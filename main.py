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
    # 1. Configura o gerador para ignorar links/imagens e aplicar o filtro de limpeza
    md_generator = DefaultMarkdownGenerator(
        # O PruningContentFilter remove o "lixo" (menus, rodapés) baseado na densidade de texto
        content_filter=PruningContentFilter(threshold=0.45, min_word_threshold=50),
        options={
            "ignore_links": True,   # Remove links: transforma [texto](url) em apenas texto
            "ignore_images": True,  # Remove todas as imagens
            "body_width": 0
        }
    )

    # 2. Define a configuração de execução
    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # Agora result.markdown é um objeto MarkdownGenerationResult
            # fit_markdown contém o texto limpo pelo filtro
            return {
                "success": True,
                "url": request.url,
                "markdown": result.markdown.fit_markdown 
            }
            
    except Exception as e:
        print(f"Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
