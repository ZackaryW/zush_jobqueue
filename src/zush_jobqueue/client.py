from __future__ import annotations

from typing import Any

import httpx

from zush_jobqueue.bootstrap import runtime_settings


class JobQueueClient:
    def __init__(self, base_url: str | None = None) -> None:
        if base_url is None:
            settings = runtime_settings()
            base_url = f"http://{settings.host}:{settings.port}"
        self._client = httpx.Client(base_url=base_url, timeout=10.0)

    def add(self, name: str, payload: list[dict[str, Any]]) -> dict[str, Any]:
        response = self._client.post(f"/add/{name}", json=payload)
        response.raise_for_status()
        return response.json()

    def get(self, name: str) -> list[dict[str, Any]]:
        response = self._client.get(f"/get/{name}")
        response.raise_for_status()
        return response.json()

    def queue(self, name: str) -> dict[str, Any]:
        response = self._client.put(f"/queue/{name}")
        response.raise_for_status()
        return response.json()

    def list_queue(self) -> dict[str, Any]:
        response = self._client.get("/queue")
        response.raise_for_status()
        return response.json()

    def check(self, name: str) -> dict[str, Any]:
        response = self._client.get(f"/check/{name}")
        response.raise_for_status()
        return response.json()

    def start(self, name: str) -> list[dict[str, Any]]:
        response = self._client.get(f"/start/{name}")
        response.raise_for_status()
        return response.json()

    def next(self, name: str) -> list[dict[str, Any]]:
        response = self._client.get(f"/next/{name}")
        response.raise_for_status()
        return response.json()

    def queuekill(self, name: str, max_lifetime: float, action: str) -> dict[str, Any]:
        response = self._client.post(
            f"/queuekill/{name}",
            json={"max_lifetime": max_lifetime, "action": action},
        )
        response.raise_for_status()
        return response.json()

    def complete(self, name: str) -> dict[str, Any]:
        response = self._client.post(f"/complete/{name}")
        response.raise_for_status()
        return response.json()

    def quit(self, restore: bool = False) -> dict[str, Any]:
        response = self._client.post("/quit", json={"restore": restore})
        response.raise_for_status()
        return response.json()