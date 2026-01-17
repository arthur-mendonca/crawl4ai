from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig 

app = FastAPI(title="Crawl4AI Clean API Optimized")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador "Stealth" (SIMPLIFICADA)
    # Removemos 'args' e 'locale' para evitar erros de inicialização.
    # Confiamos nos Headers e no override_navigator para definir o idioma.
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        user_agent_mode="random",
        viewport_width=1920,
        viewport_height=1080,
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )

    # 2. Configuração de Scroll Virtual (Lazy Loading)
    scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=3,
        scroll_by="page_height",
        wait_after_scroll=1.5
    )

    # 3. Script JavaScript de Reforço
    js_handler = """
    (async () => {
        console.log("Executando script de limpeza complementar...");
        
        // Tenta remover overlays persistentes
        const overlays = document.querySelectorAll('[class*="modal"], [class*="consent"], [class*="overlay"], [class*="banner"]');
        overlays.forEach(el => {
            const style = window.getComputedStyle(el);
            if (style.position === 'fixed' || style.position === 'absolute') {
                if (parseInt(style.zIndex) > 50) {
                    el.remove();
                }
            }
        });
    })();
    """

    # 4. Gerador de Markdown
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 5. Configuração de Execução Otimizada
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        cache_mode=CacheMode.BYPASS,
        
        # Otimizações para lidar com pop-ups e detecção
        magic=True, 
        simulate_user=True,
        override_navigator=True, 
        
        js_code=js_handler,
        virtual_scroll_config=scroll_config,

        # Espera pelo artigo real (O Pulo do Gato)
        wait_for="css:article, [role='main'], .article-content, #main-content",
        
        delay_before_return_html=3.0,

        excluded_tags=["nav", "footer", "header", "script", "style", "noscript", "svg", "button", "iframe"],
        excluded_selector=".social-share, .sidebar, .ad-container, .related-content, .cookie-banner"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                print(f"Erro ao raspar: {result.error_message}")
                raise HTTPException(status_code=500, detail=result.error_message)

            content_length = len(result.markdown.raw_markdown)
            
            if content_length < 300:
                print(f"ALERTA: Conteúdo curto ({content_length} chars). URL: {request.url}")

            return {
                "success": True,
                "url": request.url,
                "content_length": content_length,
                "markdown": result.markdown.markdown_with_citations
            }
            
    except Exception as e:
        print(f"Exceção crítica: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
