from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class TeamMember(BaseModel):
    user_id: str
    username: str
    is_active: bool


class TeamRequest(BaseModel):
    team_name: str
    members: List[TeamMember]


class TeamResponse(BaseModel):
    team_name: str
    members: List[TeamMember]


class TeamCreateResponse(BaseModel):
    team: TeamResponse


class UserResponse(BaseModel):
    user_id: str
    username: str
    team_name: str
    is_active: bool


class UserUpdateResponse(BaseModel):
    user: UserResponse


class SetIsActiveRequest(BaseModel):
    user_id: str
    is_active: bool


class PullRequestShort(BaseModel):
    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: str


class PullRequestResponse(BaseModel):
    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: str
    assigned_reviewers: List[str]
    createdAt: Optional[datetime] = None
    mergedAt: Optional[datetime] = None


class PullRequestCreateRequest(BaseModel):
    pull_request_id: str
    pull_request_name: str
    author_id: str


class PullRequestCreateResponse(BaseModel):
    pr: PullRequestResponse


class PullRequestMergeRequest(BaseModel):
    pull_request_id: str


class PullRequestMergeResponse(BaseModel):
    pr: PullRequestResponse


class PullRequestReassignRequest(BaseModel):
    pull_request_id: str
    old_user_id: str


class PullRequestReassignResponse(BaseModel):
    pr: PullRequestResponse
    replaced_by: str


class GetReviewResponse(BaseModel):
    user_id: str
    pull_requests: List[PullRequestShort]


class BulkDeactivateRequest(BaseModel):
    team_name: str


class ReassignmentInfo(BaseModel):
    pr_id: str
    old_reviewer_id: str
    new_reviewer_id: Optional[str] = None


class BulkDeactivateResponse(BaseModel):
    team_name: str
    deactivated_users: List[str]
    reassignments: List[ReassignmentInfo]

