from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do gerador para preservar texto e limpar URLs
    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(
            threshold=0.3,            
            min_word_threshold=20,    
            threshold_type="dynamic"  
        ),
        options={
            "ignore_links": False,  # OBRIGATÓRIO: Se for True, o texto do link desaparece!
            "ignore_images": True,
            "body_width": 0
        }
    )

    # O segredo está em 'citations=True' no CrawlerRunConfig (ou no generator)
    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)
                
            final_content = result.markdown.markdown_with_citations
            
            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
