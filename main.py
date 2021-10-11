import uvicorn
from fastapi import FastAPI, Path, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
import workflow_runner
from models import MyException, Configuration, Index
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from typing import List
import json
from datetime import datetime


app = FastAPI(title='SMART Data Science Application',
              description='A Smart Data Science Application running on FastAPI + uvicorn',
              version='0.0.1')

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

security = HTTPBasic()

@app.get("/users/me")
def read_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    return {"username": credentials.username, "password": credentials.password}

@app.get("/{index}")
async def get_result(request: Request, index: Index = Path(..., title="The name of the Index")):
    config = Configuration(
        index=index
    )
    try:
        result = await workflow_runner.run(config)
        return templates.TemplateResponse("item.html", {"request": request, "result": result})


    except Exception:
        raise MyException(Exception)


@app.exception_handler(MyException)
async def unicorn_exception_handler(request: Request, exc: MyException):
    return JSONResponse(
        status_code=418,
        content={"message": f"Error occurred! Please contact the system admin."},
    )


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("real_chat.html", {"request": request})


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Вы: {data}", websocket)
            await manager.broadcast(f"Пользователь #{client_id} пишет: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f" #{client_id} покинул чат!")

