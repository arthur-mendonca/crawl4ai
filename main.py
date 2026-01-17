from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
# Importação necessária para o scroll inteligente [cite: 30]
from crawl4ai.async_configs import VirtualScrollConfig 

app = FastAPI(title="Crawl4AI Clean API Optimized")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador "Stealth" Refinada
    browser_config = BrowserConfig(
        headless=True, # Mude para False se precisar ver o navegador abrindo para debug [cite: 35]
        verbose=True,
        user_agent_mode="random",
        viewport_width=1920,
        viewport_height=1080,
        # Define o locale no navegador para garantir conteúdo em PT-BR [cite: 34]
        locale="pt-BR", 
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )

    # 2. Configuração de Scroll Virtual (Lazy Loading)
    # Substitui o scroll manual do seu script JS antigo por uma solução nativa mais robusta [cite: 28, 31]
    scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=3,           # Faz 3 scrolls para garantir carregamento
        scroll_by="page_height",
        wait_after_scroll=1.5     # Espera 1.5s entre scrolls para o conteúdo renderizar
    )

    # 3. Script JavaScript de Reforço
    # Mantemos sua lógica para casos onde o 'magic' do Crawl4AI possa falhar
    js_handler = """
    (async () => {
        console.log("Executando script de limpeza complementar...");
        const sleep = (ms) => new Promise(r => setTimeout(r, ms));

        // Tenta remover overlays persistentes que o magic mode possa ter perdido
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
        
        # --- OTIMIZAÇÕES DO PDF ---
        
        # Ativa o tratamento automático de banners/pop-ups 
        magic=True, 
        
        # Simula comportamento humano (mouse, navegador real) para evitar bloqueios [cite: 6, 10]
        simulate_user=True,
        override_navigator=True, # [cite: 11]
        
        # Injeta o handler JS auxiliar e o config de scroll
        js_code=js_handler,
        virtual_scroll_config=scroll_config, # [cite: 31]

        # MUDANÇA CRÍTICA: Esperar pelo seletor CSS do artigo, não por contagem de texto.
        # Isso garante que a notícia carregou, não apenas o banner de cookies.
        # Usamos uma lista de seletores comuns em sites de notícias (article, main, div de conteudo)
        wait_for="css:article, [role='main'], .article-content, #main-content", # 
        
        delay_before_return_html=3.0, # Tempo para estabilização após JS [cite: 13]

        excluded_tags=["nav", "footer", "header", "script", "style", "noscript", "svg", "button", "iframe"],
        excluded_selector=".social-share, .sidebar, .ad-container, .related-content, .cookie-banner"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                # Log de erro detalhado
                print(f"Erro ao raspar: {result.error_message}")
                raise HTTPException(status_code=500, detail=result.error_message)

            # Validação do conteúdo
            content_length = len(result.markdown.raw_markdown)
            
            # Se ainda vier curto, logamos o aviso.
            if content_length < 300:
                print(f"ALERTA: Conteúdo curto ({content_length} chars). URL: {request.url}")
                # Dica do PDF: Em casos reais, aqui você poderia tentar um retry com js_only=True [cite: 38]

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
