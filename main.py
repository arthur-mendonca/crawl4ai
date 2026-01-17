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
    # 1. Configura o gerador para ignorar links e imagens
    md_generator = DefaultMarkdownGenerator(
        # O PruningContentFilter remove menus, footers e sidebar baseado na densidade de texto
        content_filter=PruningContentFilter(threshold=0.45, min_word_threshold=50),
        options={
            "ignore_links": True,   # Remove todos os links [texto](url)
            "ignore_images": True,  # Remove todas as imagens ![alt](url)
            "body_width": 0         # Não quebra linhas por largura fixa
        }
    )

    # 2. Define a configuração de execução do crawler
    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            return {
                "success": True,
                "url": request.url,
                # 'fit_markdown' contém a versão processada pelo filtro (sem lixo)
                "markdown": result.markdown_v2.fit_markdown if result.markdown_v2 else result.markdown
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
