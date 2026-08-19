from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.auth import router as auth_router
from backend.routers.domains import router as domains_router
from backend.routers.interviews import router as interviews_router
from backend.routers.monitoring import router as monitoring_router
from backend.routers.questions import router as questions_router
from backend.routers.resumes import router as resumes_router
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
app.include_router(resumes_router)
app.include_router(domains_router)
app.include_router(questions_router)
app.include_router(interviews_router)
app.include_router(monitoring_router)


@app.get("/", tags=["health"])
def root():
    return {"app": "IntelliVue", "version": "2.0.0", "status": "ok"}


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}