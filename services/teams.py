from models.models import *
from models.database import async_session_maker
from sqlalchemy import select, update, and_
from typing import List, Optional, Dict
from schemas import TeamMember as TeamMemberSchema


async def get_team_by_name(team_name: str) -> Optional[Team]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Team).where(Team.team_name == team_name)
        )
        return result.scalar_one_or_none()


async def get_or_create_user(user_id: str, username: str, is_active: bool, session) -> User:
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.name = username
        user.isActive = is_active
    else:
        user = User(user_id=user_id, name=username, isActive=is_active)
        session.add(user)
    
    await session.flush()
    return user


async def add_team(team_name: str, members: List[TeamMemberSchema]) -> Dict:
    async with async_session_maker() as session:
        existing_team = await get_team_by_name(team_name)
        if existing_team:
            raise ValueError("TEAM_EXISTS")
        
        new_team = Team(team_name=team_name)
        session.add(new_team)
        await session.flush()
        
        team_members_list = []
        for member in members:
            user = await get_or_create_user(member.user_id, member.username, member.is_active, session)
            team_member = TeamMember(team_id=new_team.id, member_id=user.id)
            session.add(team_member)
            team_members_list.append({
                "user_id": member.user_id,
                "username": member.username,
                "is_active": member.is_active
            })
        
        await session.commit()
        
        return {
            "team_name": team_name,
            "members": team_members_list
        }


async def get_team(team_name: str) -> Optional[Dict]:
    async with async_session_maker() as session:
        team = await get_team_by_name(team_name)
        if not team:
            return None
        
        result = await session.execute(
            select(User, TeamMember)
            .join(TeamMember, User.id == TeamMember.member_id)
            .where(TeamMember.team_id == team.id)
        )
        
        members = []
        for user, _ in result.all():
            members.append({
                "user_id": user.user_id,
                "username": user.name,
                "is_active": user.isActive
            })
        
        return {
            "team_name": team_name,
            "members": members
        }


async def bulk_deactivate_team(team_name: str) -> Dict:
    """
    Массовая деактивация пользователей команды с безопасным переназначением ревьюверов
    """
    async with async_session_maker() as session:
        team = await get_team_by_name(team_name)
        if not team:
            raise ValueError("NOT_FOUND")
        
        # Получаем ID деактивируемых пользователей
        team_users_result = await session.execute(
            select(User.id, User.user_id)
            .join(TeamMember, User.id == TeamMember.member_id)
            .where(
                and_(
                    TeamMember.team_id == team.id,
                    User.isActive == True
                )
            )
        )
        active_users = {row[0]: row[1] for row in team_users_result.all()}
        active_user_ids = list(active_users.keys())
        
        if not active_user_ids:
            return {
                "team_name": team_name,
                "deactivated_users": [],
                "reassignments": []
            }
        
        # Запрос 1: Деактивируем всех пользователей команды
        await session.execute(
            update(User)
            .where(User.id.in_(active_user_ids))
            .values(isActive=False)
        )
        
        # Запрос 2: Переназначаем ревьюверов на открытых PR
        # Находим активных кандидатов из той же команды (исключая деактивируемых)
        candidates_result = await session.execute(
            select(User.id)
            .join(TeamMember, User.id == TeamMember.member_id)
            .where(
                and_(
                    User.isActive == True,
                    TeamMember.team_id == team.id,
                    User.id.notin_(active_user_ids)
                )
            )
        )
        candidate_ids = [row[0] for row in candidates_result.all()]
        
        if candidate_ids:
            # Получаем открытые PR с деактивируемыми ревьюверами
            prs_to_reassign = await session.execute(
                select(
                    Reviewers.pr_id,
                    Reviewers.reviewer_id,
                    PullRequest.author_id,
                    PullRequest.pull_request_id
                )
                .join(PullRequest, Reviewers.pr_id == PullRequest.id)
                .where(
                    and_(
                        Reviewers.reviewer_id.in_(active_user_ids),
                        PullRequest.isMerged == False
                    )
                )
            )
            
            # Группируем по PR и находим замену
            pr_updates = {}  # {pr_id: (old_reviewer_id, new_reviewer_id, pr_string_id)}
            used_candidates = set()
            
            for pr_id, old_reviewer_id, author_id, pr_string_id in prs_to_reassign.all():
                # Ищем кандидата (не автора, не использованного)
                new_reviewer_id = None
                for candidate_id in candidate_ids:
                    if candidate_id != author_id and candidate_id not in used_candidates:
                        new_reviewer_id = candidate_id
                        used_candidates.add(candidate_id)
                        break
                
                if new_reviewer_id:
                    pr_updates[pr_id] = (old_reviewer_id, new_reviewer_id, pr_string_id)
            
            # Batch update всех переназначений
            for pr_id, (old_reviewer_id, new_reviewer_id, _) in pr_updates.items():
                await session.execute(
                    update(Reviewers)
                    .where(
                        and_(
                            Reviewers.pr_id == pr_id,
                            Reviewers.reviewer_id == old_reviewer_id
                        )
                    )
                    .values(reviewer_id=new_reviewer_id)
                )
            
            # Формируем ответ
            reassignments = []
            for pr_id, (old_reviewer_id, new_reviewer_id, pr_string_id) in pr_updates.items():
                old_reviewer_string_id = active_users.get(old_reviewer_id, "")
                new_reviewer_string_id_result = await session.execute(
                    select(User.user_id).where(User.id == new_reviewer_id)
                )
                new_reviewer_string_id = new_reviewer_string_id_result.scalar_one_or_none()
                reassignments.append({
                    "pr_id": pr_string_id,
                    "old_reviewer_id": old_reviewer_string_id,
                    "new_reviewer_id": new_reviewer_string_id
                })
        else:
            reassignments = []
        
        await session.commit()
        
        return {
            "team_name": team_name,
            "deactivated_users": list(active_users.values()),
            "reassignments": reassignments
        }
