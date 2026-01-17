from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Gerador focado em integridade de texto
    # Mantemos ignore_links=False para as palavras não sumirem
    # Ativamos citations=True para que a URL não "suje" o meio da frase
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 2. Configuração de Execução de Uso Geral
    # Usamos excluded_tags para remover o "lixo" estrutural (menus/rodapés)
    # sem o risco de o filtro de densidade (Pruning) apagar partes do texto real.
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        excluded_tags=[
            "nav", "footer", "header", "aside", 
            "script", "style", "form", "noscript", 
            "svg", "canvas"
        ],
        # Seletores CSS comuns que costumam conter ruído em diversos sites
        excluded_selector=".social-share, .sidebar, .menu, .nav-menu, .ads, #comments"
    )

    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # O markdown_with_citations é o campo ideal para inputs de LLMs
            # pois preserva o texto original e isola as referências.
            final_content = result.markdown.markdown_with_citations

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
