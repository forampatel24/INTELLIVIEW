from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.auth import router as auth_router
from database.migrate import migrate


@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate()
    yield


app = FastAPI(
    title="IntelliVue API",
    description="AI-powered interview intelligence platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/", tags=["health"])
def root():
    return {"app": "IntelliVue", "version": "2.0.0", "status": "ok"}


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}