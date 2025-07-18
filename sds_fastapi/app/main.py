from fastapi import FastAPI
from app.core.config import settings
from app.core.logger import add_logging_middleware
from app.core.security import add_security_middleware

app = FastAPI()

add_logging_middleware(app)
add_security_middleware(app)

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/config")
async def read_config():
    return settings.model_dump()
