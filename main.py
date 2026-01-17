from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import os

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador Gerenciado
    # 'use_persistent_context' cria um perfil real, dificultando o bloqueio por IP/Datacenter.
    browser_config = BrowserConfig(
        headless=True,
        enable_stealth=True,
        user_agent_mode="random",
        # Isso cria uma pasta temporária para salvar a sessão do "humano"
        use_persistent_context=True, 
        user_data_dir="/tmp/crawl4ai_profile"
    )

    # 2. Gerador de Markdown (Mantendo sua integridade de links)
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 3. Configuração de Execução com "Gatilho de Conteúdo"
    run_config = CrawlerRunConfig(
        markdown_generator=md_generator,
        magic=True,
        simulate_user=True,
        override_navigator=True,
        
        # O SEGREDO: Esperamos até que um seletor de conteúdo real apareça.
        # Quase todo site de notícia usa a tag <article>. Se ele vir o Cloudflare, 
        # ele vai esperar até o redirect acontecer e o <article> carregar.
        wait_for="css:article", 
        
        # Aumentamos o timeout global para dar tempo do desafio ser resolvido
        page_timeout=60000, 
        delay_before_return_html=5.0, # Pequeno delay extra após o <article> aparecer
        
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        excluded_selector=".social-share, .sidebar, .menu, .ads, .tp-ads"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=run_config)
            
            if not result.success:
                # Se der timeout no wait_for, significa que ele ficou preso no Cloudflare
                raise HTTPException(status_code=500, detail=f"Falha ao carregar conteúdo real: {result.error_message}")

            final_content = result.markdown.markdown_with_citations

            # Verificação final de segurança
            if "Cloudflare" in final_content and len(final_content) < 1500:
                 return {
                    "success": False,
                    "error": "Ainda preso no desafio do Cloudflare. O IP da sua VPS pode estar na blacklist.",
                    "markdown": final_content
                }

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
