from fastapi import FastAPI
from app.core.config import settings

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/config")
async def read_config():
    return settings.dict()
