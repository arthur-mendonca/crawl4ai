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
    # 1. Configuração balanceada do gerador
    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(
            threshold=0.3,           # Reduzido de 0.45 para 0.3 para manter mais texto
            min_word_threshold=20,    # Reduzido de 50 para 20 para não descartar parágrafos curtos
            threshold_type="dynamic"  # Ajusta o limite automaticamente com base nos dados da página
        ),
        options={
            "ignore_links": True,   # Isso garante que mesmo no 'raw_markdown' não haverá links
            "ignore_images": True,
            "body_width": 0
        }
    )

    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # ESTRATÉGIA DE RETORNO:
            # Se o fit_markdown (filtrado) parecer muito curto (ex: < 500 caracteres),
            # retornamos o raw_markdown (todo o texto da página, mas sem os links).
            final_content = result.markdown.fit_markdown
            if len(final_content) < 500:
                final_content = result.markdown.raw_markdown

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
