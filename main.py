from contextlib import asynccontextmanager
from models.database import *
from fastapi import FastAPI
import uvicorn
from routes import users, teams, pull_request


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    yield
    
    pass


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(teams.router)
app.include_router(pull_request.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)