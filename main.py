from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig 

app = FastAPI(title="Crawl4AI Clean API - MSN Killer")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador
    # Mantemos simples para evitar erros de inicialização, mas reforçamos o User Agent
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        user_agent_mode="random", # Rotaciona para evitar fingerprinting fácil
        viewport_width=1920,
        viewport_height=1080,
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )

    # 2. Scroll Lento e Gradual
    # O MSN carrega imagens e parágrafos conforme o scroll.
    scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=5,           # Aumentei para 5 para garantir leitura profunda
        scroll_by="page_height",
        wait_after_scroll=2.0     # Mais tempo para renderizar imagens
    )

    # 3. JS "Caçador de Cookies" (Bilíngue e Agressivo)
    js_handler = """
    (async () => {
        console.log(">>> INICIANDO PROTOCOLO ANTI-COOKIE <<<");
        const sleep = (ms) => new Promise(r => setTimeout(r, ms));

        // 1. Procura Botões de Aceite (PT e EN)
        // O MSN usa botões, links ou divs com role button
        const keywords = ['aceit', 'concord', 'consent', 'agree', 'allow', 'yes', 'continue', 'manage'];
        
        // Seleciona tudo que é clicável
        const clickables = Array.from(document.querySelectorAll('button, a, div[role="button"], span[role="button"]'));
        
        let clicked = false;
        for (const el of clickables) {
            const text = (el.innerText || "").toLowerCase();
            // Verifica se tem texto relevante e se está visível
            if (keywords.some(k => text.includes(k)) && el.offsetParent !== null) {
                console.log("Botão encontrado: ", text);
                
                // Prioridade: Botões de "Aceitar" direto
                if (text.includes('aceit') || text.includes('agree') || text.includes('yes')) {
                    try {
                        el.click();
                        console.log("CLICADO!");
                        clicked = true;
                        await sleep(3000); // Espera o reload da página
                        break; // Se clicou em Aceitar, paramos
                    } catch (e) { console.error(e); }
                }
            }
        }

        // 2. Remoção Forçada de Modais (CSS Kill Switch)
        // Remove divs que cobrem a tela inteira, focando em palavras chave de privacidade
        const blockers = document.querySelectorAll('div[class*="modal"], div[class*="banner"], div[id*="consent"], div[class*="overlay"]');
        blockers.forEach(el => {
            const text = el.innerText.toLowerCase();
            if (text.includes('cookie') || text.includes('privacy') || text.includes('privacidade')) {
                console.log("Removendo overlay de privacidade na força bruta.");
                el.remove();
            }
        });

        // 3. Força o corpo da página a ficar visível (caso o modal tenha deixado hidden)
        document.body.style.overflow = 'auto';
        document.body.style.position = 'static';
    })();
    """

    # 4. Gerador de Markdown
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": True,  # Ignora links para limpar o texto
            "ignore_images": True,
            "body_width": 0,
            "citations": False     # Desliga citações para limpar poluição visual
        }
    )

    # 5. Configuração de Execução
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        cache_mode=CacheMode.BYPASS,
        
        magic=True,
        simulate_user=True,
        override_navigator=True,
        
        js_code=js_handler,
        virtual_scroll_config=scroll_config,

        # O PULO DO GATO REAL:
        # Não espere só pelo "article". Espere que o "article" tenha TEXTO dentro.
        # Isso evita pegar um <article> vazio enquanto o loader gira.
        wait_for="js:() => { return document.querySelector('article') && document.querySelector('article').innerText.length > 200; }",
        
        # Aumentamos o delay final para garantir que, se houve reload, pegamos a pág nova
        delay_before_return_html=4.0,

        # LISTA NEGRA: Removemos explicitamente as divs de consentimento do MSN
        excluded_selector=".ms-consent-banner, #cookie-banner, .privacy-modal, div[aria-label='Privacy'], .peregrine-auth-modal, nav, footer, .sidebar"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            content_length = len(result.markdown.raw_markdown)
            
            # Filtro Pós-Processamento
            # Se o texto ainda começar com o aviso da Microsoft, cortamos ele manualmente
            markdown_clean = result.markdown.raw_markdown
            if "Microsoft Cares About Your Privacy" in markdown_clean or "A Microsoft Preocupa-se" in markdown_clean:
                print("ALERTA: Banner detectado no output. Tentando limpar via string split...")
                # Tenta pegar tudo DEPOIS do banner (assumindo que o banner vem no topo)
                parts = markdown_clean.split("Declaração de Privacidade")
                if len(parts) > 1:
                    markdown_clean = parts[-1]
            
            return {
                "success": True,
                "url": request.url,
                "content_length": len(markdown_clean),
                "markdown": markdown_clean # Retorna o texto limpo
            }
            
    except Exception as e:
        print(f"Exceção: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
