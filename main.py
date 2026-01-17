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
    # 1. Filtro de conteúdo mais inteligente
    # O PruningContentFilter remove menus e rodapés baseando-se na densidade de texto
    content_filter = PruningContentFilter(
        threshold=0.45,           # Aumentamos um pouco para ser mais rigoroso com menus
        min_word_threshold=30,    # Parágrafos muito curtos (geralmente lixo) são ignorados
        threshold_type="dynamic"
    )

    md_generator = DefaultMarkdownGenerator(
        content_filter=content_filter,
        options={
            "ignore_links": False, 
            "ignore_images": True,
            "body_width": 0,
            "citations": True      # Habilita o modo de citações no gerador
        }
    )

    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        # Importante: Queremos que o crawler foque no conteúdo principal
        main_content_only=True     # Tenta identificar o <main> ou <article> automaticamente
    )

    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # O 'fit_markdown' agora conterá apenas o texto relevante 
            # E como 'citations' está True, ele virá limpo com as referências no fim.
            final_content = result.markdown.fit_markdown

            # Backup caso o filtro seja agressivo demais
            if not final_content or len(final_content) < 300:
                final_content = result.markdown.markdown_with_citations

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
