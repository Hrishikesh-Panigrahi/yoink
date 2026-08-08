"""Evaluate JavaScript in the running Yoink UI over the DevTools protocol.

Launch the app with QTWEBENGINE_REMOTE_DEBUGGING=9222 first, then:

    python cdp.py expressions.json [--port 9222]

where expressions.json is a JSON list of JavaScript strings. Each result is
printed next to the expression that produced it.

Every expression is raced against a timeout: `Runtime.evaluate` with
`awaitPromise` waits forever on a promise that never settles, which otherwise
hangs the whole run with no output.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import aiohttp

TIMEOUT_MS = 3000


def with_timeout(expression: str, timeout_ms: int = TIMEOUT_MS) -> str:
    return (
        "Promise.race(["
        f"Promise.resolve().then(() => ({expression})),"
        f'new Promise(r => setTimeout(() => r("TIMEOUT"), {timeout_ms}))'
        "])"
    )


async def evaluate(expressions, port: int, timeout_ms: int):
    async with aiohttp.ClientSession() as http:
        async with http.get(f"http://localhost:{port}/json/list") as resp:
            targets = await resp.json()
        pages = [t for t in targets if t.get("type") == "page"]
        if not pages:
            raise SystemExit(f"no page target on port {port} - is the app running?")

        results = []
        async with http.ws_connect(pages[0]["webSocketDebuggerUrl"]) as ws:
            for index, expression in enumerate(expressions, start=1):
                await ws.send_json(
                    {
                        "id": index,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": with_timeout(expression, timeout_ms),
                            "returnByValue": True,
                            "awaitPromise": True,
                        },
                    }
                )
                while True:
                    message = json.loads(await ws.receive_str())
                    if message.get("id") == index:
                        break
                payload = message.get("result", {})
                if "exceptionDetails" in payload:
                    results.append(("ERROR", payload["exceptionDetails"].get("text")))
                else:
                    results.append(("ok", payload.get("result", {}).get("value")))
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expressions", help="JSON file holding a list of JS strings")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--timeout-ms", type=int, default=TIMEOUT_MS)
    args = parser.parse_args()

    with open(args.expressions, encoding="utf-8") as handle:
        expressions = json.load(handle)
    if not isinstance(expressions, list):
        raise SystemExit("expected a JSON list of JavaScript strings")

    results = asyncio.run(evaluate(expressions, args.port, args.timeout_ms))
    failed = 0
    for expression, (status, value) in zip(expressions, results, strict=True):
        label = expression if len(expression) <= 70 else expression[:67] + "..."
        print(f"[{status}] {label}\n      -> {value}")
        if status == "ERROR" or value == "TIMEOUT":
            failed += 1
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
