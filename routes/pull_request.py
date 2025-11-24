from fastapi import APIRouter, HTTPException, status
from schemas import (
    PullRequestCreateRequest, PullRequestCreateResponse,
    PullRequestMergeRequest, PullRequestMergeResponse,
    PullRequestReassignRequest, PullRequestReassignResponse,
    ErrorResponse
)
from services import pull_request as pr_service


router = APIRouter(prefix="/pullRequest")


@router.post("/create", status_code=status.HTTP_201_CREATED,
                summary="Создать PR и автоматически назначить до 2 ревьюверов из команды автора",
                response_model=PullRequestCreateResponse,
                responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
async def create(request: PullRequestCreateRequest):
    try:
        pr = await pr_service.create_pull_request(
            request.pull_request_id,
            request.pull_request_name,
            request.author_id
        )
        return PullRequestCreateResponse(pr=pr)
    except ValueError as e:
        error_code = str(e)
        if error_code == "PR_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "PR_EXISTS", "message": "PR id already exists"}}
            )
        elif error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {"code": "NOT_FOUND", "message": "author or team not found"}
                }
            )
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/merge", status_code=status.HTTP_200_OK,
                summary="Пометить PR как MERGED (идемпотентная операция)",
                response_model=PullRequestMergeResponse,
                responses={404: {"model": ErrorResponse}})
async def merge(request: PullRequestMergeRequest):
    try:
        pr = await pr_service.merge_pull_request(request.pull_request_id)
        if not pr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "PR not found"}}
            )
        return PullRequestMergeResponse(pr=pr)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/reassign", status_code=status.HTTP_200_OK,
                summary="Переназначить конкретного ревьювера на другого из его команды",
                response_model=PullRequestReassignResponse,
                responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
async def reassign(request: PullRequestReassignRequest):
    try:
        result = await pr_service.reassign_reviewer(
            request.pull_request_id,
            request.old_user_id
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "PR or user not found"}}
            )
        return PullRequestReassignResponse(
            pr=result["pr"],
            replaced_by=result["replaced_by"]
        )
    except ValueError as e:
        error_code = str(e)
        if error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "PR or user not found"}}
            )
        elif error_code == "PR_MERGED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {"code": "PR_MERGED", "message": "cannot reassign on merged PR"}
                }
            )
        elif error_code == "NOT_ASSIGNED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "NOT_ASSIGNED", "message": "reviewer is not assigned to this PR"}}
            )
        elif error_code == "NO_CANDIDATE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "NO_CANDIDATE", "message": "no active replacement candidate in team"}}
            )
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
