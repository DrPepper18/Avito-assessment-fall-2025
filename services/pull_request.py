from models.models import *
from models.database import async_session_maker
from sqlalchemy import select, update, and_
from typing import Optional, Dict
from datetime import datetime


async def get_pr_by_string_id(pull_request_id: str) -> Optional[PullRequest]:
    """Get PR by string ID"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(PullRequest).where(PullRequest.pull_request_id == pull_request_id)
        )
        return result.scalar_one_or_none()


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


async def create_pull_request(pull_request_id: str, pull_request_name: str, author_id: str) -> Dict:
    """
    POST /pullRequest/create
    Create a PR and automatically assign up to 2 reviewers from the author's team
    Returns PR object
    """
    async with async_session_maker() as session:
        # Check if PR already exists
        existing_pr = await get_pr_by_string_id(pull_request_id)
        if existing_pr:
            raise ValueError("PR_EXISTS")
        
        # Get author
        author = await get_user_by_string_id(author_id)
        if not author:
            raise ValueError("NOT_FOUND")
        
        # Get author's team
        author_team = await session.execute(
            select(Team, TeamMember)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.member_id == author.id)
            .limit(1)
        )
        team_row = author_team.first()
        
        if not team_row:
            raise ValueError("NOT_FOUND")
        
        team, _ = team_row
        
        # Create new PR
        new_pr = PullRequest(
            pull_request_id=pull_request_id,
            name=pull_request_name,
            author_id=author.id,
            isMerged=False,
            createdAt=datetime.utcnow()
        )
        session.add(new_pr)
        await session.flush()
        
        # Find available reviewers (active, not the author, in the same team, limit 2)
        reviewers_query = (
            select(User.id)
            .join(TeamMember, User.id == TeamMember.member_id)
            .where(
                and_(
                    User.isActive == True,
                    User.id != author.id,
                    TeamMember.team_id == team.id
                )
            )
            .limit(2)
        )
        
        reviewers_result = await session.execute(reviewers_query)
        reviewer_ids = [row[0] for row in reviewers_result.all()]
        
        # Add reviewers
        assigned_reviewer_string_ids = []
        if reviewer_ids:
            reviewers = [
                Reviewers(pr_id=new_pr.id, reviewer_id=reviewer_id)
                for reviewer_id in reviewer_ids
            ]
            session.add_all(reviewers)
            
            # Get string IDs for reviewers
            for reviewer_id in reviewer_ids:
                string_id = await _get_user_string_id(session, reviewer_id)
                if string_id:
                    assigned_reviewer_string_ids.append(string_id)
        
        await session.commit()
        
        return {
            "pull_request_id": pull_request_id,
            "pull_request_name": pull_request_name,
            "author_id": author_id,
            "status": "OPEN",
            "assigned_reviewers": assigned_reviewer_string_ids,
            "createdAt": new_pr.createdAt,
            "mergedAt": None
        }


async def merge_pull_request(pull_request_id: str) -> Optional[Dict]:
    """
    POST /pullRequest/merge
    Mark a PR as merged (idempotent operation)
    Returns PR object or None if not found
    """
    async with async_session_maker() as session:
        pr = await get_pr_by_string_id(pull_request_id)
        if not pr:
            return None
        
        # Update PR
        merged_at = datetime.utcnow() if not pr.isMerged else pr.mergedAt
        await session.execute(
            update(PullRequest)
            .where(PullRequest.id == pr.id)
            .values(isMerged=True, mergedAt=merged_at)
        )
        await session.commit()
        
        # Get reviewers
        reviewers_result = await session.execute(
            select(Reviewers.reviewer_id)
            .where(Reviewers.pr_id == pr.id)
        )
        reviewer_ids = [row[0] for row in reviewers_result.all()]
        assigned_reviewers = []
        for reviewer_id in reviewer_ids:
            string_id = await _get_user_string_id(session, reviewer_id)
            if string_id:
                assigned_reviewers.append(string_id)
        
        author_string_id = await _get_user_string_id(session, pr.author_id)
        
        return {
            "pull_request_id": pr.pull_request_id,
            "pull_request_name": pr.name,
            "author_id": author_string_id,
            "status": "MERGED",
            "assigned_reviewers": assigned_reviewers,
            "createdAt": pr.createdAt,
            "mergedAt": merged_at
        }


async def reassign_reviewer(pull_request_id: str, old_user_id: str) -> Optional[Dict]:
    """
    POST /pullRequest/reassign
    Reassign a reviewer to another person from their team
    Returns dict with pr and replaced_by, or None if error
    """
    async with async_session_maker() as session:
        # Get PR
        pr = await get_pr_by_string_id(pull_request_id)
        if not pr:
            raise ValueError("NOT_FOUND")
        
        # Check if PR is merged
        if pr.isMerged:
            raise ValueError("PR_MERGED")
        
        # Get old reviewer
        old_reviewer = await get_user_by_string_id(old_user_id)
        if not old_reviewer:
            raise ValueError("NOT_FOUND")
        
        # Check if old reviewer is assigned to this PR
        reviewer_check = await session.execute(
            select(Reviewers)
            .where(
                and_(
                    Reviewers.pr_id == pr.id,
                    Reviewers.reviewer_id == old_reviewer.id
                )
            )
        )
        if not reviewer_check.first():
            raise ValueError("NOT_ASSIGNED")
        
        # Get old reviewer's team
        old_reviewer_team = await session.execute(
            select(TeamMember.team_id)
            .where(TeamMember.member_id == old_reviewer.id)
            .limit(1)
        )
        team_row = old_reviewer_team.first()
        
        if not team_row:
            raise ValueError("NOT_FOUND")
        
        team_id = team_row[0]
        
        # Get existing reviewers for this PR
        existing_reviewers = await session.execute(
            select(Reviewers.reviewer_id)
            .where(Reviewers.pr_id == pr.id)
        )
        existing_reviewer_ids = {row[0] for row in existing_reviewers.all()}
        
        # Find a candidate (active, not the old reviewer, not already a reviewer, in the same team)
        candidate_query = (
            select(User.id)
            .join(TeamMember, User.id == TeamMember.member_id)
            .where(
                and_(
                    User.isActive == True,
                    User.id != old_reviewer.id,
                    User.id.notin_(existing_reviewer_ids),
                    TeamMember.team_id == team_id
                )
            )
            .limit(1)
        )
        
        candidate_result = await session.execute(candidate_query)
        candidate_row = candidate_result.first()
        
        if not candidate_row:
            raise ValueError("NO_CANDIDATE")
        
        new_reviewer_id = candidate_row[0]
        new_reviewer_string_id = await _get_user_string_id(session, new_reviewer_id)
        
        # Update the reviewer
        await session.execute(
            update(Reviewers)
            .where(
                and_(
                    Reviewers.pr_id == pr.id,
                    Reviewers.reviewer_id == old_reviewer.id
                )
            )
            .values(reviewer_id=new_reviewer_id)
        )
        await session.commit()
        
        # Get updated PR with reviewers
        reviewers_result = await session.execute(
            select(Reviewers.reviewer_id)
            .where(Reviewers.pr_id == pr.id)
        )
        reviewer_ids = [row[0] for row in reviewers_result.all()]
        assigned_reviewers = []
        for reviewer_id in reviewer_ids:
            string_id = await _get_user_string_id(session, reviewer_id)
            if string_id:
                assigned_reviewers.append(string_id)
        
        author_string_id = await _get_user_string_id(session, pr.author_id)
        
        return {
            "pr": {
                "pull_request_id": pr.pull_request_id,
                "pull_request_name": pr.name,
                "author_id": author_string_id,
                "status": "OPEN",
                "assigned_reviewers": assigned_reviewers,
                "createdAt": pr.createdAt,
                "mergedAt": None
            },
            "replaced_by": new_reviewer_string_id
        }
