from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Gerador de Markdown
    # REMOVEMOS o PruningContentFilter porque ele buga e remove o texto dos links.
    # Mantemos ignore_links como False para as palavras não sumirem.
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,    # OBRIGATÓRIO para manter o texto âncora
            "ignore_images": True,   # Remove imagens para economizar tokens
            "body_width": 0,
            "citations": True        # Transforma links em [1], [2] e joga URLs pro fim
        }
    )

    # 2. Configuração de Execução
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        excluded_tags=[
            "nav", "footer", "header", "aside", 
            "script", "style", "form", "noscript", 
            "svg", "canvas"
        ],
        # Remove seletores comuns de redes sociais e menus laterais para qualquer site
        excluded_selector=".social-share, .sidebar, .menu, .nav-menu, .ads-container"
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
