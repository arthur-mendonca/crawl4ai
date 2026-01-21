import sys
import asyncio
from fastapi import FastAPI
from app.api.routes import router

# Fix para Windows + Playwright: Força o uso do ProactorEventLoop
# O SelectorEventLoop (padrão antigo ou em algumas configs) não suporta subprocessos,
# causando NotImplementedError ao tentar abrir o browser.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="Crawl4AI v4 - MSN API + Anti-Bot")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
