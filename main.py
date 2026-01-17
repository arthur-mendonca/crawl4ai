from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração Global do Navegador (O SEGREDO DO BYPASS)
    browser_config = BrowserConfig(
        headless=True,            # Pode ser True no VPS
        magic=True,               # Ativa o Magic Mode (Anti-bot robusto)
        user_agent_mode="random", # Gera identidades diferentes para cada site
        # Em alguns sites muito agressivos, 'headless=False' pode ser necessário,
        # mas com 'magic=True', o headless costuma passar bem.
    )

    # 2. Gerador de Markdown (Mantendo a limpeza que já ajustamos)
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 3. Configuração da Corrida (Wait and Delay)
    run_config = CrawlerRunConfig(
        markdown_generator=md_generator,
        # Espera a rede ficar ociosa (garante que o redirecionamento terminou)
        wait_until="networkidle", 
        # DÁ TEMPO para o Cloudflare te mandar para a página real (5 segundos)
        delay_before_return_html=5.0, 
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        excluded_selector=".social-share, .sidebar, .menu, .ads"
    )

    try:
        # Importante: Passamos o browser_config na inicialização do crawler
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
        raise HTTPException(status_code=500, detail=str(e))
