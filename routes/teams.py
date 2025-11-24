from fastapi import APIRouter, HTTPException, status, Query
from schemas import (
    TeamRequest, TeamCreateResponse, TeamResponse,
    BulkDeactivateRequest, BulkDeactivateResponse,
    ErrorResponse
)
from services import teams as team_service


router = APIRouter(prefix="/team")


@router.post("/add", status_code=status.HTTP_201_CREATED,
                  summary="Создать команду с участниками (создаёт/обновляет пользователей)",
                  response_model=TeamCreateResponse,
                  responses={400: {"model": ErrorResponse}})
async def add(request: TeamRequest):
    try:
        team = await team_service.add_team(request.team_name, request.members)
        return TeamCreateResponse(team=team)
    except ValueError as e:
        if str(e) == "TEAM_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "TEAM_EXISTS", "message": "team_name already exists"}}
            )
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/get", status_code=status.HTTP_200_OK,
                 summary="Получить команду с участниками",
                 response_model=TeamResponse,
                 responses={404: {"model": ErrorResponse}})
async def get(team_name: str = Query(..., description="Уникальное имя команды")):
    try:
        team = await team_service.get_team(team_name)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "team not found"}}
            )
        return TeamResponse(**team)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/bulkDeactivate", status_code=status.HTTP_200_OK,
                  summary="Массовая деактивация пользователей команды с безопасным переназначением ревьюверов",
                  response_model=BulkDeactivateResponse,
                  responses={404: {"model": ErrorResponse}})
async def bulk_deactivate(request: BulkDeactivateRequest):
    try:
        result = await team_service.bulk_deactivate_team(request.team_name)
        return BulkDeactivateResponse(**result)
    except ValueError as e:
        if str(e) == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "team not found"}}
            )
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
