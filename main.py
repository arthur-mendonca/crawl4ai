from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Anti-Bot API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador
    # enable_stealth aplica patches de furtividade para burlar detecções básicas
    browser_config = BrowserConfig(
        headless=True,
        user_agent_mode="random",
        enable_stealth=True  # Essencial para passar pelo Cloudflare
    )

    # 2. Gerador de Markdown
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 3. Configuração da Execução (Onde o Bypass acontece)
    run_config = CrawlerRunConfig(
        markdown_generator=md_generator,
        magic=True,               # Tenta lidar automaticamente com desafios e popups
        simulate_user=True,       # Simula movimentos de mouse e interações humanas
        override_navigator=True,  # Mascara propriedades do navegador
        
        # MUDANÇA CRUCIAL: Voltamos para 'domcontentloaded' para evitar o Timeout de 60s
        # e usamos um delay maior para dar tempo do Cloudflare redirecionar.
        wait_until="domcontentloaded", 
        delay_before_return_html=10.0, # 10 segundos é o tempo ideal para o bypass do Turnstile
        
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
        raise HTTPException(status_code=500, detail=str(e))
