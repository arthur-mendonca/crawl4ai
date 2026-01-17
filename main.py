from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig 

app = FastAPI(title="Crawl4AI Optimized - DOM Isolation")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Navegador
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

    # 2. Scroll Virtual
    scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=4,
        scroll_by="page_height",
        wait_after_scroll=2.0 
    )

    # 3. JS: "Protocolo de Isolamento"
    # Este script tenta clicar no consentimento. Se falhar, procura o artigo
    # e DELETA todo o resto do site para sobrar apenas a notícia.
    js_handler = """
    (async () => {
        console.log(">>> INICIANDO PROTOCOLO DE ISOLAMENTO <<<");
        const sleep = (ms) => new Promise(r => setTimeout(r, ms));

        // --- FASE 1: Tenta Clicar no Consentimento (Bilíngue) ---
        const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
        const keywords = ['aceit', 'agree', 'consent', 'yes', 'allow', 'manage'];
        
        for (const btn of buttons) {
            const text = (btn.innerText || "").toLowerCase();
            // Clica apenas se for um botão de consentimento óbvio
            if (keywords.some(k => text.includes(k)) && text.length < 50) {
                console.log("Tentando clicar em:", text);
                try {
                    btn.click();
                    await sleep(2000); // Espera reação da página
                } catch(e) {}
            }
        }

        // --- FASE 2: Cirurgia de DOM (O Pulo do Gato) ---
        // Procura pelo conteúdo real da notícia
        const article = document.querySelector('article') || 
                        document.querySelector('[role="main"]') || 
                        document.querySelector('.article-content') ||
                        document.querySelector('#main');

        if (article) {
            console.log("Artigo encontrado! Isolando conteúdo...");
            // Clona o artigo
            const content = article.cloneNode(true);
            // Limpa o corpo do site (remove banners, menus, footers, scripts)
            document.body.innerHTML = '';
            // Insere apenas o artigo limpo
            document.body.appendChild(content);
        } else {
            console.log("Artigo não encontrado. Tentando remover overlays na força bruta...");
            // Se não achou o artigo, remove modais conhecidos
            document.querySelectorAll('.modal, .banner, .overlay, [id*="cookie"]').forEach(el => el.remove());
        }
    })();
    """

    # 4. Gerador de Markdown
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": True,
            "ignore_images": True, 
            "body_width": 0,
            "citations": False
        }
    )

    # 5. Run Config
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        cache_mode=CacheMode.BYPASS,
        magic=True,
        simulate_user=True,
        override_navigator=True,
        js_code=js_handler,
        virtual_scroll_config=scroll_config,
        
        # Aguarda até que exista um article OU que o body tenha mudado
        wait_for="css:body", 
        delay_before_return_html=3.0,
        
        # Exclusão redundante para garantir
        excluded_selector="#cookie-banner, .ms-consent-banner, .privacy-modal"
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            raw_md = result.markdown.raw_markdown

            # --- FASE 3: Limpeza Python Pós-Processamento ---
            # Se o JS falhar e o banner vier, cortamos ele aqui.
            # Adicionei os termos em Inglês que apareceram no seu log.
            block_phrases = [
                "Microsoft Cares About Your Privacy", 
                "A Microsoft Preocupa-se Com a Sua Privacidade",
                "We and our partners process data"
            ]
            
            # Se encontrar frases do banner, tenta limpar
            if any(phrase in raw_md for phrase in block_phrases):
                print("Banner detectado no Python. Aplicando split...")
                # Tenta separar pelo termo "Privacy Statement" ou "Declaração de Privacidade"
                # O texto real da notícia costuma vir DEPOIS disso.
                separators = ["Privacy Statement", "Declaração de Privacidade", "Manage Preferences", "Gerenciar preferências"]
                
                for sep in separators:
                    if sep in raw_md:
                        parts = raw_md.split(sep)
                        # Pega a última parte (assumindo que o banner está no topo)
                        if len(parts) > 1:
                            candidate_text = parts[-1]
                            # Se o corte resultou em algo útil, atualizamos
                            if len(candidate_text) > 200:
                                raw_md = candidate_text
                                break
            
            return {
                "success": True,
                "url": request.url,
                "content_length": len(raw_md),
                "markdown": raw_md.strip()
            }
            
    except Exception as e:
        print(f"Erro Crítico: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
