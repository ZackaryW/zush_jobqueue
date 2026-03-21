from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from zush_jobqueue.manager import JobQueueManager

if TYPE_CHECKING:
    from zush.paths import ZushStorage


class QueueKillRequest(BaseModel):
    max_lifetime: float
    action: str


class QuitRequest(BaseModel):
    restore: bool = False


def create_app(
    storage: ZushStorage | None = None,
    shutdown_callback=None,
) -> FastAPI:
    app = FastAPI()
    manager = JobQueueManager(storage=storage, shutdown_callback=shutdown_callback)
    app.state.manager = manager

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/add/{name}")
    def add(name: str, payload: list[dict[str, Any]]) -> dict[str, Any]:
        return manager.add_payload(name, payload)

    @app.get("/get/{name}")
    def get_payload(name: str) -> list[dict[str, Any]]:
        try:
            return manager.get_payload(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.put("/queue/{name}")
    def queue(name: str) -> dict[str, Any]:
        try:
            return manager.queue_payload(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/queue")
    def queue_state() -> dict[str, Any]:
        return manager.snapshot()

    @app.get("/check/{name}")
    def check(name: str) -> dict[str, Any]:
        return manager.check(name)

    @app.get("/start/{name}")
    def start(name: str) -> list[dict[str, Any]]:
        try:
            return manager.start(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/next/{name}")
    def next_entry(name: str) -> list[dict[str, Any]]:
        try:
            return manager.next(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/queuekill/{name}")
    def queuekill(name: str, request: QueueKillRequest) -> dict[str, Any]:
        return manager.configure_queuekill(name, request.max_lifetime, request.action)

    @app.post("/complete/{name}")
    def complete(name: str) -> dict[str, Any]:
        return manager.complete(name)

    @app.post("/quit")
    def quit_server(request: QuitRequest) -> dict[str, Any]:
        return manager.quit(restore=request.restore)

    return app