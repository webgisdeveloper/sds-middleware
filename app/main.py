from fastapi import FastAPI
from app.core.config import settings
from app.core.logger import add_logging_middleware
from app.core.security import add_security_middleware
from app.admin_console import router as admin_router

app = FastAPI()

add_logging_middleware(app)
add_security_middleware(app)

# Include admin console router
app.include_router(admin_router)

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/config")
async def read_config():
    return settings.model_dump()
