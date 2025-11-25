import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_team_lifecycle(client: AsyncClient):
    """E2E тест: создание команды, добавление пользователей, получение команды"""

    team_data = {
        "team_name": "backend",
        "members": [
            {"user_id": "u1", "username": "Alice", "is_active": True},
            {"user_id": "u2", "username": "Bob", "is_active": True},
            {"user_id": "u3", "username": "Charlie", "is_active": True}
        ]
    }
    
    response = await client.post("/team/add", json=team_data)
    assert response.status_code == 201
    assert response.json()["team"]["team_name"] == "backend"
    assert len(response.json()["team"]["members"]) == 3
    

    response = await client.get("/team/get?team_name=backend")
    assert response.status_code == 200
    assert response.json()["team_name"] == "backend"
    assert len(response.json()["members"]) == 3


@pytest.mark.asyncio
async def test_pr_creation_and_reviewers(client: AsyncClient):
    """E2E тест: создание PR с автоматическим назначением ревьюверов"""

    team_data = {
        "team_name": "frontend",
        "members": [
            {"user_id": "u4", "username": "David", "is_active": True},
            {"user_id": "u5", "username": "Eve", "is_active": True},
            {"user_id": "u6", "username": "Frank", "is_active": True}
        ]
    }
    await client.post("/team/add", json=team_data)
    

    pr_data = {
        "pull_request_id": "pr-1001",
        "pull_request_name": "Add feature",
        "author_id": "u4"
    }
    
    response = await client.post("/pullRequest/create", json=pr_data)
    assert response.status_code == 201
    pr = response.json()["pr"]
    assert pr["pull_request_id"] == "pr-1001"
    assert pr["status"] == "OPEN"
    assert len(pr["assigned_reviewers"]) <= 2
    assert "u4" not in pr["assigned_reviewers"]  # Автор не должен быть ревьювером


@pytest.mark.asyncio
async def test_pr_merge(client: AsyncClient):
    """E2E тест: создание и merge PR"""

    team_data = {
        "team_name": "devops",
        "members": [
            {"user_id": "u7", "username": "Grace", "is_active": True},
            {"user_id": "u8", "username": "Henry", "is_active": True}
        ]
    }
    await client.post("/team/add", json=team_data)
    

    pr_data = {
        "pull_request_id": "pr-1002",
        "pull_request_name": "Fix bug",
        "author_id": "u7"
    }
    await client.post("/pullRequest/create", json=pr_data)
    

    merge_data = {"pull_request_id": "pr-1002"}
    response = await client.post("/pullRequest/merge", json=merge_data)
    assert response.status_code == 200
    assert response.json()["pr"]["status"] == "MERGED"
    
    response = await client.post("/pullRequest/merge", json=merge_data)
    assert response.status_code == 200
    assert response.json()["pr"]["status"] == "MERGED"


@pytest.mark.asyncio
async def test_reviewer_reassignment(client: AsyncClient):
    """E2E тест: переназначение ревьювера"""

    team_data = {
        "team_name": "qa",
        "members": [
            {"user_id": "u9", "username": "Ivan", "is_active": True},
            {"user_id": "u10", "username": "Julia", "is_active": True},
            {"user_id": "u11", "username": "Kate", "is_active": True}
        ]
    }
    await client.post("/team/add", json=team_data)
    
    pr_data = {
        "pull_request_id": "pr-1003",
        "pull_request_name": "Test feature",
        "author_id": "u9"
    }
    create_response = await client.post("/pullRequest/create", json=pr_data)
    old_reviewers = create_response.json()["pr"]["assigned_reviewers"]
    
    if old_reviewers:
        reassign_data = {
            "pull_request_id": "pr-1003",
            "old_user_id": old_reviewers[0]
        }
        response = await client.post("/pullRequest/reassign", json=reassign_data)
        assert response.status_code == 200
        assert response.json()["replaced_by"] != old_reviewers[0]
        assert response.json()["replaced_by"] in response.json()["pr"]["assigned_reviewers"]


@pytest.mark.asyncio
async def test_user_deactivation(client: AsyncClient):
    """E2E тест: деактивация пользователя"""

    team_data = {
        "team_name": "support",
        "members": [
            {"user_id": "u12", "username": "Liam", "is_active": True},
            {"user_id": "u13", "username": "Mia", "is_active": True}
        ]
    }
    await client.post("/team/add", json=team_data)
    
    deactivate_data = {"user_id": "u12", "is_active": False}
    response = await client.post("/users/setIsActive", json=deactivate_data)
    assert response.status_code == 200
    assert response.json()["user"]["is_active"] == False


@pytest.mark.asyncio
async def test_get_user_reviews(client: AsyncClient):
    """E2E тест: получение PR'ов пользователя"""

    team_data = {
        "team_name": "design",
        "members": [
            {"user_id": "u14", "username": "Noah", "is_active": True},
            {"user_id": "u15", "username": "Olivia", "is_active": True}
        ]
    }
    await client.post("/team/add", json=team_data)
    
    pr_data = {
        "pull_request_id": "pr-1004",
        "pull_request_name": "Design update",
        "author_id": "u14"
    }
    await client.post("/pullRequest/create", json=pr_data)
    
    response = await client.get("/users/getReview?user_id=u15")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_bulk_deactivate(client: AsyncClient):
    """E2E тест: массовая деактивация команды"""

    team_data = {
        "team_name": "marketing",
        "members": [
            {"user_id": "u16", "username": "Paul", "is_active": True},
            {"user_id": "u17", "username": "Quinn", "is_active": True},
            {"user_id": "u18", "username": "Rachel", "is_active": True}
        ]
    }
    await client.post("/team/add", json=team_data)

    pr_data = {
        "pull_request_id": "pr-1005",
        "pull_request_name": "Campaign",
        "author_id": "u16"
    }
    await client.post("/pullRequest/create", json=pr_data)
    
    deactivate_data = {"team_name": "marketing"}
    response = await client.post("/team/bulkDeactivate", json=deactivate_data)
    assert response.status_code == 200
    assert len(response.json()["deactivated_users"]) == 3


@pytest.mark.asyncio
async def test_error_cases(client: AsyncClient):
    """E2E тест: обработка ошибок"""

    response = await client.get("/team/get?team_name=nonexistent")
    assert response.status_code == 404
    
    response = await client.post("/pullRequest/merge", json={"pull_request_id": "pr-9999"})
    assert response.status_code == 404
    
    team_data = {
        "team_name": "duplicate",
        "members": [{"user_id": "u19", "username": "Sam", "is_active": True}]
    }
    await client.post("/team/add", json=team_data)
    response = await client.post("/team/add", json=team_data)
    assert response.status_code == 400
    
    pr_data = {
        "pull_request_id": "pr-duplicate",
        "pull_request_name": "Test",
        "author_id": "u19"
    }
    await client.post("/pullRequest/create", json=pr_data)
    response = await client.post("/pullRequest/create", json=pr_data)
    assert response.status_code == 409

