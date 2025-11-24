from models.models import *
from models.database import async_session_maker
from sqlalchemy import select, update
from typing import List, Optional
from datetime import datetime


async def get_user_by_string_id(user_id: str) -> Optional[User]:
    """Get user by string ID"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def _get_user_string_id(session, user_id: int) -> str:
    """Helper to get user string ID from internal ID"""
    result = await session.execute(
        select(User.user_id).where(User.id == user_id)
    )
    row = result.first()
    return row[0] if row else ""


async def get_review(user_id: str) -> List[dict]:
    """
    GET /users/getReview
    Get PRs where the user is a reviewer
    Returns list of PR short objects
    """
    async with async_session_maker() as session:
        # Get user by string ID
        user = await get_user_by_string_id(user_id)
        if not user:
            return []
        
        # Get PRs where user is reviewer
        result = await session.execute(
            select(PullRequest, Reviewers)
            .join(Reviewers, PullRequest.id == Reviewers.pr_id)
            .where(Reviewers.reviewer_id == user.id)
        )
        
        prs = []
        for pr, _ in result.all():
            prs.append({
                "pull_request_id": pr.pull_request_id,
                "pull_request_name": pr.name,
                "author_id": await _get_user_string_id(session, pr.author_id),
                "status": "MERGED" if pr.isMerged else "OPEN"
            })
        
        return prs


async def set_is_active(user_id: str, is_active: bool) -> Optional[dict]:
    """
    POST /users/setIsActive
    Update user's isActive status
    Returns user object with team_name
    """
    async with async_session_maker() as session:
        user = await get_user_by_string_id(user_id)
        if not user:
            return None
        
        await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(isActive=is_active)
        )
        await session.commit()
        
        # Get team name
        team_result = await session.execute(
            select(Team.team_name)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.member_id == user.id)
            .limit(1)
        )
        team_row = team_result.first()
        team_name = team_row[0] if team_row else ""
        
        return {
            "user_id": user.user_id,
            "username": user.name,
            "team_name": team_name,
            "is_active": is_active
        }
