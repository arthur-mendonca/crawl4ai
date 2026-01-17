from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração Global do Navegador
    # Definimos como o navegador será lançado.
    browser_config = BrowserConfig(
        headless=True,
        user_agent_mode="random"  # Identidades randômicas para cada site
    )

    # 2. Gerador de Markdown (Mantendo a limpeza de hyperlinks e citações)
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 3. Configuração da Corrida (Onde o "Magic" acontece)
    run_config = CrawlerRunConfig(
        markdown_generator=md_generator,
        magic=True,               # BYPASS: Ativa comportamento humano (Anti-bot)
        # Espera o Cloudflare redirecionar após o sucesso
        wait_until="networkidle",
        delay_before_return_html=5.0,
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        excluded_selector=".social-share, .sidebar, .menu, .ads"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=run_config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            final_content = result.markdown.markdown_with_citations

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        # Se der erro de tipo ou qualquer outro, pegamos aqui
        raise HTTPException(status_code=500, detail=str(e))
