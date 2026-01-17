from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler

app = FastAPI()

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url)
            return {"markdown": result.markdown}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "Crawl4AI Service is running"}
