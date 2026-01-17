from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador (BrowserConfig)
    # Isso é crucial para sites protegidos. O 'user_agent_mode="random"' e 
    # headers específicos ajudam a evitar que o MSN detecte que é um bot.
    browser_config = BrowserConfig(
        headless=True,  # Use False se quiser ver o navegador abrindo para debug
        verbose=True,
        user_agent_mode="random", # Alterna entre user agents reais
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
    )

    # 2. Script para lidar com Cookies/Popups
    # Este script roda no navegador antes da raspagem. Ele tenta clicar 
    # em botões comuns de "Aceitar Cookies".
    js_click_consent = """
    (async () => {
        const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
        const acceptBtn = buttons.find(btn => 
            btn.innerText.toLowerCase().includes('aceito') || 
            btn.innerText.toLowerCase().includes('concordo') || 
            btn.innerText.toLowerCase().includes('accept') ||
            btn.innerText.toLowerCase().includes('continuar')
        );
        if (acceptBtn) {
            console.log("Botão de consentimento encontrado. Clicando...");
            acceptBtn.click();
            // Espera um pouco para o modal sumir e o conteúdo carregar
            await new Promise(r => setTimeout(r, 2000));
        }
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

    # 4. Configuração da Execução (CrawlerRunConfig)
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        # Força o crawler a baixar a página de novo, ignorando cache anterior com erro
        cache_mode=CacheMode.BYPASS, 
        
        # Executa nosso script de fechar popups
        js_code=js_click_consent,
        
        # O PULO DO GATO: O crawler só vai considerar a página "pronta" 
        # quando encontrar a tag <article> ou um <h1>. 
        # Isso evita raspar antes do redirect ou carregamento do JS.
        wait_for="article, h1, .article-content",
        
        excluded_tags=[
            "nav", "footer", "header", "aside", 
            "script", "style", "form", "noscript", 
            "svg", "canvas", "button", "input"
        ],
        excluded_selector=".social-share, .sidebar, .menu, .nav-menu, .ads, #comments, .cookie-banner, .gdpr-banner"
    )

    try:
        # Passamos o browser_config aqui na inicialização
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # Verifica se o conteúdo é muito curto (sinal de bloqueio persistente)
            if len(result.markdown.raw_markdown) < 200:
                 # Opcional: Tentar logar ou retornar aviso específico
                 pass

            final_content = result.markdown.markdown_with_citations

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content,
                # Útil para debug: retorna o título da página para ver se pegou a notícia
                "metadata": result.metadata 
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
