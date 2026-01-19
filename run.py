import sys
import asyncio
import uvicorn

if __name__ == "__main__":
    # Windows specific event loop policy to support subprocesses (Playwright)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # reload=True is incompatible with WindowsProactorEventLoopPolicy on Windows
    # because the spawned process defaults to SelectorEventLoop before app code runs.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
