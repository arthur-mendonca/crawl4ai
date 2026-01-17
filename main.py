from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador "Stealth"
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        user_agent_mode="random",
        # Viewport maior ajuda a carregar versão desktop completa
        viewport_width=1920,
        viewport_height=1080,
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )

    # 2. Script JavaScript Refinado para o MSN
    # Tenta clicar em "Aceitar", mas se falhar, REMOVE o modal à força.
    js_handler = """
    (async () => {
        console.log("Iniciando script de limpeza...");
        
        // Função auxiliar para esperar
        const sleep = (ms) => new Promise(r => setTimeout(r, ms));

        // 1. Tentar clicar em botões de consentimento (GDPR/Cookies)
        const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
        const acceptBtn = buttons.find(btn => 
            btn.innerText && (
                btn.innerText.match(/aceit(o|ar)/i) || 
                btn.innerText.match(/concordo/i) || 
                btn.innerText.match(/consent/i) ||
                btn.innerText.match(/continuar/i)
            )
        );
        
        if (acceptBtn) {
            console.log("Botão de aceitar encontrado. Clicando...");
            acceptBtn.click();
            await sleep(2000);
        }

        // 2. Tática de "Força Bruta": Remover modais que cobrem a tela
        // O MSN costuma ter classes como 'peregrine-auth-modal' ou similar
        const overlays = document.querySelectorAll('[class*="modal"], [class*="consent"], [class*="overlay"], [class*="banner"]');
        overlays.forEach(el => {
            // Só remove se estiver cobrindo a tela e tiver z-index alto
            const style = window.getComputedStyle(el);
            if (style.position === 'fixed' || style.position === 'absolute') {
                if (parseInt(style.zIndex) > 100) {
                    console.log("Removendo overlay bloqueador:", el);
                    el.remove();
                }
            }
        });

        // 3. Rolar a página para forçar o Lazy Loading do texto
        window.scrollTo(0, document.body.scrollHeight / 2);
        await sleep(1000);
        window.scrollTo(0, 0);
    })();
    """

    # 3. Gerador de Markdown
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": True
        }
    )

    # 4. Configuração de Execução
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        cache_mode=CacheMode.BYPASS,
        js_code=js_handler,
        
        # O PULO DO GATO: Esperar até que exista bastante texto na página
        # Isso impede que o crawler retorne antes da notícia carregar.
        wait_for="js:() => document.body.innerText.length > 500",
        
        # Se o wait_for acima falhar (timeout), tenta pelo menos esperar o article
        # wait_for="article", 
        
        # Dá um tempo extra após o processamento JS para o DOM estabilizar
        delay_before_return_html=3.0,

        excluded_tags=["nav", "footer", "header", "script", "style", "noscript", "svg", "button"],
        excluded_selector=".social-share, .sidebar, .ad-container, .related-content"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # Validação final: Se o texto for muito curto, provavelmente falhou
            content_length = len(result.markdown.raw_markdown)
            if content_length < 300:
                print(f"ALERTA: Conteúdo muito curto ({content_length} chars). HTML dump: {result.html[:500]}")
                # Aqui você poderia tentar uma estratégia de fallback se quisesse

            return {
                "success": True,
                "url": request.url,
                "content_length": content_length,
                "markdown": result.markdown.markdown_with_citations
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
