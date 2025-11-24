from locust import HttpUser, task, between
import random
import string


class PRReviewerUser(HttpUser):
    wait_time = between(0.5, 2.0)
    
    def on_start(self):
        """Выполняется один раз при старте каждого пользователя"""
        # Создаем уникальную команду для каждого пользователя
        self.team_name = f"team_{self._generate_id()}"
        self.user_ids = [f"u_{self._generate_id()}" for _ in range(5)]
        
        # Создаем команду
        team_data = {
            "team_name": self.team_name,
            "members": [
                {"user_id": uid, "username": f"User_{uid}", "is_active": True}
                for uid in self.user_ids
            ]
        }
        self.client.post("/team/add", json=team_data)
        
        # Создаем несколько PR
        self.pr_ids = []
        for i in range(3):
            pr_id = f"pr_{self._generate_id()}"
            pr_data = {
                "pull_request_id": pr_id,
                "pull_request_name": f"PR {i}",
                "author_id": random.choice(self.user_ids)
            }
            response = self.client.post("/pullRequest/create", json=pr_data)
            if response.status_code == 201:
                self.pr_ids.append(pr_id)
    
    def _generate_id(self):
        """Генерирует случайный ID"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    @task(3)
    def get_team(self):
        """Получение команды"""
        self.client.get(f"/team/get?team_name={self.team_name}")
    
    @task(2)
    def get_user_reviews(self):
        """Получение PR'ов пользователя"""
        user_id = random.choice(self.user_ids)
        self.client.get(f"/users/getReview?user_id={user_id}")
    
    @task(2)
    def create_pr(self):
        """Создание PR"""
        pr_id = f"pr_{self._generate_id()}"
        pr_data = {
            "pull_request_id": pr_id,
            "pull_request_name": "New PR",
            "author_id": random.choice(self.user_ids)
        }
        self.client.post("/pullRequest/create", json=pr_data)
    
    @task(1)
    def merge_pr(self):
        """Merge PR"""
        if self.pr_ids:
            pr_id = random.choice(self.pr_ids)
            self.client.post("/pullRequest/merge", json={"pull_request_id": pr_id})
    
    @task(1)
    def set_user_active(self):
        """Изменение активности пользователя"""
        user_id = random.choice(self.user_ids)
        self.client.post("/users/setIsActive", json={
            "user_id": user_id,
            "is_active": random.choice([True, False])
        })
    
    @task(1)
    def reassign_reviewer(self):
        """Переназначение ревьювера"""
        if self.pr_ids:
            pr_id = random.choice(self.pr_ids)
            # Получаем информацию о PR (через getReview для одного из пользователей)
            user_id = random.choice(self.user_ids)
            response = self.client.get(f"/users/getReview?user_id={user_id}")
            if response.status_code == 200:
                prs = response.json().get("pull_requests", [])
                for pr in prs:
                    if pr["pull_request_id"] == pr_id and pr["status"] == "OPEN":
                        # Пытаемся переназначить (нужен старый ревьювер, упрощаем)
                        break

