from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador com Stealth Mode ATIVADO
    # 'enable_stealth' é o que realmente mascara o Playwright contra o Cloudflare
    browser_config = BrowserConfig(
        headless=True,
        user_agent_mode="random",
        enable_stealth=True,  # CRUCIAL para passar pelo desafio Turnstile
    )

    # 2. Gerador de Markdown (Mantendo a limpeza de links)
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 3. Configuração de Execução com Delay de Redirecionamento
    run_config = CrawlerRunConfig(
        markdown_generator=md_generator,
        magic=True,              # Lida com popups e frames de desafio
        simulate_user=True,      # Simula movimentos humanos para não ser banido
        override_navigator=True, # Força o navegador a parecer um Chrome comum
        
        # 'domcontentloaded' evita o timeout de 60s do 'networkidle'
        wait_until="domcontentloaded", 
        
        # Aumentamos para 15 segundos. O Cloudflare leva tempo para redirecionar 
        # após o "Vérification réussie". Se capturar antes, a página vem vazia.
        delay_before_return_html=15.0, 
        
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        excluded_selector=".social-share, .sidebar, .menu, .ads, .tp-ads"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=run_config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            final_content = result.markdown.markdown_with_citations

            # Se o conteúdo ainda vier com sinais de Cloudflare, avisamos
            if "Cloudflare" in final_content and len(final_content) < 1000:
                return {
                    "success": False,
                    "error": "Bloqueio do Cloudflare detectado. Tente novamente em alguns instantes.",
                    "markdown": final_content
                }

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
