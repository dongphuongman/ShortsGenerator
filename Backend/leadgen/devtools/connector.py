import json
import asyncio
import httpx
from typing import Any, Optional

from termcolor import colored


class ChromeConnector:
    def __init__(self, host: str = "127.0.0.1", port: int = 9222):
        self.host = host
        self.port = port
        self._ws = None
        self._target_id = None
        self._msg_id = 0
        self._pending = {}
        self._session_id = None

    @property
    def _base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/json/version")
                if resp.status_code != 200:
                    return False
                data = resp.json()
                ws_url = data.get("webSocketDebuggerUrl")
                if not ws_url:
                    return False
            import websockets
            self._ws = await websockets.connect(ws_url, max_size=2**30)
            print(colored(f"[+] Connected to Chrome DevTools at {self._base_url}", "green"))
            return True
        except Exception as e:
            print(colored(f"[-] Chrome DevTools connection failed: {e}", "red"))
            return False

    async def disconnect(self):
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _send(self, method: str, params: dict = None) -> dict:
        if not self._ws:
            raise RuntimeError("Not connected to Chrome")
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params
        if self._session_id:
            msg["sessionId"] = self._session_id
        await self._ws.send(json.dumps(msg))
        async for raw in self._ws:
            response = json.loads(raw)
            if response.get("id") == self._msg_id:
                if "error" in response:
                    raise RuntimeError(f"CDP error: {response['error']}")
                return response.get("result", {})
            if "method" in response:
                await self._handle_event(response)
        return {}

    async def _handle_event(self, event: dict):
        method = event.get("method", "")
        event_params = event.get("params", {})
        for msg_id, future in list(self._pending.items()):
            if method == "Page.loadEventFired":
                if not future.done():
                    future.set_result(event_params)
                    del self._pending[msg_id]

    async def _wait_for_event(self, event_name: str, timeout: float = 15.0) -> dict:
        future = asyncio.get_event_loop().create_future()
        self._pending[self._msg_id] = future
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            del self._pending[self._msg_id]
            raise TimeoutError(f"Timeout waiting for {event_name}")

    async def create_session(self, target_id: Optional[str] = None) -> str:
        if target_id:
            self._target_id = target_id
        else:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.put(f"{self._base_url}/json/new?about:blank")
                if resp.status_code != 200:
                    raise RuntimeError("Failed to create new tab")
                data = resp.json()
                self._target_id = data["id"]
        result = await self._send("Target.attachToTarget", {
            "targetId": self._target_id,
            "flatten": True
        })
        self._session_id = result["sessionId"]
        return self._session_id

    async def close_session(self):
        if self._target_id and self._session_id:
            await self._send("Target.closeTarget", {"targetId": self._target_id})
            self._session_id = None
            self._target_id = None

    async def navigate(self, url: str, wait_until: str = "load") -> dict:
        result = await self._send("Page.enable")
        result = await self._send("Page.navigate", {"url": url})
        if wait_until == "load":
            await self._wait_for_event("Page.loadEventFired")
        elif wait_until == "network_idle":
            await self._send("Page.navigate", {"url": url})
            await asyncio.sleep(3)
        return result

    async def evaluate(self, js: str) -> Any:
        result = await self._send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": True,
        })
        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            raise RuntimeError(f"JS error: {exc.get('text', '')} - {exc.get('exception', {}).get('description', '')}")
        return result.get("result", {}).get("value")

    async def get_page_text(self) -> str:
        return await self.evaluate("document.body.innerText")

    async def get_page_html(self) -> str:
        return await self.evaluate("document.documentElement.outerHTML")

    async def scroll_down(self, times: int = 3, delay: float = 1.5):
        for i in range(times):
            await self.evaluate(f"window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay)

    async def wait_for_selector(self, selector: str, timeout: float = 10.0) -> bool:
        safe_sel = selector.replace("'", "\\'")
        js = f"""
        (() => {{
            return new Promise((resolve) => {{
                const el = document.querySelector('{safe_sel}');
                if (el) {{ resolve(true); return; }}
                const observer = new MutationObserver(() => {{
                    if (document.querySelector('{safe_sel}')) {{
                        observer.disconnect();
                        resolve(true);
                    }}
                }});
                observer.observe(document.body, {{ childList: true, subtree: true }});
                setTimeout(() => {{ observer.disconnect(); resolve(false); }}, {int(timeout * 1000)});
            }});
        }})()
        """
        return await self.evaluate(js)

    async def screenshot(self) -> bytes:
        result = await self._send("Page.captureScreenshot", {"format": "png"})
        import base64
        return base64.b64decode(result["data"])

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed
