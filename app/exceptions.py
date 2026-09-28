from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

class DiagnosticAppException(Exception):
    def __init__(self, message: str, status_code: int = 400, resolution: str = None):
        self.message = message
        self.status_code = status_code
        self.resolution = resolution

async def app_exception_handler(request: Request, exc: DiagnosticAppException):
    logger.warning(f"App Exception [{exc.status_code}]: {exc.message} | Path: {request.url.path}")
    content = {"error": exc.message}
    if exc.resolution:
        content["resolution"] = exc.resolution
    return JSONResponse(status_code=exc.status_code, content=content)
