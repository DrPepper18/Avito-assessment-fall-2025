from fastapi import APIRouter, HTTPException, status, Query
from schemas import (
    SetIsActiveRequest, UserUpdateResponse, GetReviewResponse,
    ErrorResponse
)
from services import users as user_service


router = APIRouter(prefix="/users")


@router.post("/setIsActive", status_code=status.HTTP_200_OK,
                   summary="Установить флаг активности пользователя",
                   response_model=UserUpdateResponse,
                   responses={404: {"model": ErrorResponse}})
async def setIsActive(request: SetIsActiveRequest):
    try:
        user = await user_service.set_is_active(request.user_id, request.is_active)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "user not found"}}
            )
        return UserUpdateResponse(user=user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/getReview", status_code=status.HTTP_200_OK,
                  summary="Получить PR'ы, где пользователь назначен ревьювером",
                  response_model=GetReviewResponse)
async def getReview(user_id: str = Query(..., description="Идентификатор пользователя")):
    try:
        pull_requests = await user_service.get_review(user_id)
        return GetReviewResponse(
            user_id=user_id,
            pull_requests=pull_requests
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
