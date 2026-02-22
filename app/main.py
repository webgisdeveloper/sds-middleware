from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.logger import add_logging_middleware
from app.core.security import add_security_middleware
from app.admin_console import router as admin_router
from app.ops_console import router as ops_router
from app.worker import router as worker_router
from app.hipaa_api import router as hipaa_router
import os

app = FastAPI()

add_logging_middleware(app)
add_security_middleware(app)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(admin_router)
app.include_router(ops_router)
app.include_router(worker_router)
app.include_router(hipaa_router)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join("app", "static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return {"message": "Favicon not found"}

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/config")
async def read_config():
    return settings.model_dump()
