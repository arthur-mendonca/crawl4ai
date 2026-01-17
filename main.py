from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador (Nível Hard)
    browser_config = BrowserConfig(
        headless=True,
        enable_stealth=True,        # Ativa o modo furtivo contra Cloudflare
        user_agent_mode="random",
        # Use um contexto persistente para 'guardar' o sucesso do bypass
        use_persistent_context=True,
        user_data_dir="/tmp/crawl4ai_profile",
        # --- SE O CÓDIGO FALHAR, DESCOMENTE A LINHA ABAIXO E USE UM PROXY ---
        # proxy="http://usuario:senha@ip_do_proxy:porta" 
    )

    # 2. Gerador de Markdown (Mantendo sua limpeza)
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 3. Configuração da Execução
    run_config = CrawlerRunConfig(
        markdown_generator=md_generator,
        magic=True,                 # Resolve desafios e remove overlays
        simulate_user=True,         # Move o mouse e simula cliques
        override_navigator=True,    # Mascara que é um navegador automatizado
        
        # Em vez de esperar pelo 'article' (que pode nunca vir se o IP estiver bloqueado),
        # usamos um delay longo e tentamos capturar o que houver.
        wait_until="networkidle",
        delay_before_return_html=15.0, 
        
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        excluded_selector=".social-share, .sidebar, .menu, .ads"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=run_config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            final_content = result.markdown.markdown_with_citations

            # Se o conteúdo for muito curto e falar de Cloudflare, o IP da VPS caiu no filtro
            if "Cloudflare" in final_content and len(final_content) < 1500:
                return {
                    "success": False,
                    "error": "IP da VPS Bloqueado pelo Cloudflare (Datacenter Block). Use um Proxy Residencial.",
                    "markdown": final_content
                }

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
