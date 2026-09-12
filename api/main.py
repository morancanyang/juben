import asyncio
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from api.agents import recover_interrupted, tasks
from api.errors import GameError
from api.settings import ROOT, settings
from api.identity_api import router as identity_router
from api.game_api import router as game_router
from api.scripts_api import router as scripts_router


@asynccontextmanager
async def lifespan(_app):
    settings.validate_deployment()
    recover_interrupted()
    yield
    running = list(tasks.values())
    for task in running:
        task.cancel()
    if running:
        await asyncio.gather(*running, return_exceptions=True)


app = FastAPI(
    title="夜半卷宗 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-CSRF-Token", "Last-Event-ID"],
)
rate_windows = {}


@app.middleware("http")
async def request_boundary(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    if request.method not in ["GET", "HEAD", "OPTIONS"]:
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins.split(","):
            return JSONResponse(
                {
                    "error": {
                        "code": "ORIGIN_DENIED",
                        "message": "请求来源不受信任。",
                        "requestId": request_id,
                    }
                },
                403,
            )
        try:
            if int(request.headers.get("content-length", "0")) > 1_000_000:
                raise ValueError()
        except ValueError:
            return JSONResponse(
                {
                    "error": {
                        "code": "TOO_LARGE",
                        "message": "请求内容过大。",
                        "requestId": request_id,
                    }
                },
                413,
            )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1_000_000:
                return JSONResponse(
                    {
                        "error": {
                            "code": "TOO_LARGE",
                            "message": "请求内容过大。",
                            "requestId": request_id,
                        }
                    },
                    413,
                )
        request._body = bytes(body)
        if "/auth/" in request.url.path:
            key = (request.client.host if request.client else "local", request.url.path)
            t = time.monotonic()
            start, count = rate_windows.get(key, (t, 0))
            if t - start > 60:
                start, count = t, 0
            if count >= 30:
                return JSONResponse(
                    {
                        "error": {
                            "code": "RATE_LIMIT",
                            "message": "操作太频繁，请稍后重试。",
                        }
                    },
                    429,
                )
            rate_windows[key] = (start, count + 1)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api/") else "no-cache"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response


@app.exception_handler(GameError)
async def game_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "retryable": exc.status in [409, 429, 502, 503, 504],
                "requestId": getattr(request.state, "request_id", ""),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请检查输入格式和必填项。",
                "details": {
                    "fields": [".".join(map(str, e["loc"])) for e in exc.errors()]
                },
            }
        },
        422,
    )


@app.exception_handler(IntegrityError)
async def integrity_handler(request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "CONFLICT",
                "message": "这次操作与已有记录冲突，请刷新后重试。",
                "retryable": True,
            }
        },
        409,
    )



app.include_router(identity_router)
app.include_router(game_router)
app.include_router(scripts_router)

dist = ROOT / "web" / "dist"
if (dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if (
        path in ["icon.svg", "manifest.webmanifest", "sw.js"]
        and (dist / path).is_file()
    ):
        return FileResponse(dist / path)
    if path == "" or path in ["library", "play", "editor", "docs", "settings"]:
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        return JSONResponse(
            {
                "message": "Frontend not built. Run npm run build in web/ or open Vite at port 5173."
            },
            503,
        )
    return JSONResponse(
        {"error": {"code": "NOT_FOUND", "message": "页面不存在。"}}, 404
    )
