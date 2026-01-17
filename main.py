from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig
import re

app = FastAPI(title="Crawl4AI Optimized - Anti-Banner v2")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    
    # 1. Browser Config com stealth máximo
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        user_agent_mode="random",
        viewport_width=1920,
        viewport_height=1080,
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    # 2. Scroll Config mais agressivo
    scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=5,  # Mais scrolls para lazy load
        scroll_by="page_height",
        wait_after_scroll=1.5
    )

    # 3. JavaScript Handler APRIMORADO
    js_handler = """
    (async () => {
        console.log("🚀 INICIANDO PROTOCOLO ANTI-BANNER v2");
        const sleep = ms => new Promise(r => setTimeout(r, ms));
        
        // ===== FASE 1: Espera Adicional para Conteúdo Dinâmico =====
        await sleep(3000); // Espera 3s para conteúdo carregar
        
        // ===== FASE 2: Remoção Agressiva de Overlays =====
        const overlaySelectors = [
            '.modal', '.popup', '.overlay', '.consent', '.cookie',
            '[class*="cookie"]', '[id*="cookie"]', '[class*="consent"]',
            '[id*="consent"]', '[class*="privacy"]', '[id*="privacy"]',
            '.ms-consent-banner', '#ms-consent-banner', 
            '[class*="gdpr"]', '[aria-modal="true"]',
            '.privacy-modal', '.cookie-banner', '.consent-banner',
            // MSN específico
            '#consent-prompt-overlay', '.consent-prompt'
        ];
        
        overlaySelectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                console.log(`🗑️ Removendo overlay: ${sel}`);
                el.remove();
            });
        });
        
        // Remove elementos com position:fixed que bloqueiam tela
        document.querySelectorAll('*').forEach(el => {
            const style = window.getComputedStyle(el);
            if (style.position === 'fixed' && parseInt(style.zIndex) > 1000) {
                console.log('🗑️ Removendo elemento fixed de alto z-index');
                el.remove();
            }
        });
        
        // ===== FASE 3: Clique em Botões de Consentimento =====
        const btnKeywords = [
            'accept', 'agree', 'consent', 'allow', 'continue',
            'aceitar', 'concordo', 'permitir', 'continuar',
            'ok', 'yes', 'sim', 'entendi', 'i accept'
        ];
        
        const buttons = Array.from(document.querySelectorAll(
            'button, a[role="button"], div[role="button"], [class*="button"]'
        ));
        
        for (const btn of buttons) {
            const text = (btn.innerText || btn.textContent || '').toLowerCase().trim();
            const hasKeyword = btnKeywords.some(kw => text.includes(kw));
            
            if (hasKeyword && text.length < 60) {
                console.log(`✅ Clicando botão: "${text}"`);
                try {
                    btn.click();
                    await sleep(2500);
                    break; // Clica apenas no primeiro encontrado
                } catch(e) {
                    console.log('❌ Erro ao clicar:', e);
                }
            }
        }
        
        // ===== FASE 4: Isolamento Cirúrgico do Artigo =====
        await sleep(1500);
        
        // Primeiro tenta encontrar o conteúdo por texto longo
        let article = null;
        
        // Estratégia 1: Seletores específicos
        const articleSelectors = [
            'article',
            '[role="main"]',
            'main',
            '.article-content',
            '.story-body',
            '.post-content',
            '#article',
            '#main-content',
            '[itemtype*="Article"]',
            '.news-article',
            // MSN específico
            '.article-body',
            '[data-t="article"]',
            '.content',
            '#content'
        ];
        
        for (const sel of articleSelectors) {
            article = document.querySelector(sel);
            if (article && article.innerText.length > 300) {
                console.log(`📰 Artigo encontrado com seletor: ${sel} (${article.innerText.length} chars)`);
                break;
            }
            article = null; // Reset se não tiver conteúdo suficiente
        }
        
        // Estratégia 2: Se não encontrou, procura pela div com mais texto
        if (!article) {
            console.log('📰 Buscando elemento com mais texto...');
            const allDivs = Array.from(document.querySelectorAll('div, section'));
            
            let maxLength = 0;
            let bestDiv = null;
            
            allDivs.forEach(div => {
                const textLength = div.innerText.length;
                // Ignora elementos muito pequenos ou que são containers do body inteiro
                if (textLength > maxLength && textLength < document.body.innerText.length * 0.9) {
                    maxLength = textLength;
                    bestDiv = div;
                }
            });
            
            if (bestDiv && maxLength > 500) {
                article = bestDiv;
                console.log(`📰 Melhor elemento encontrado com ${maxLength} caracteres`);
            }
        }
        
        if (article) {
            // Clone o artigo
            const content = article.cloneNode(true);
            
            // Remove elementos indesejados DENTRO do artigo
            const unwantedInside = content.querySelectorAll(
                'script, style, iframe, [class*="ad"], [id*="ad"], ' +
                '[class*="promo"], [class*="related"], [class*="comment"], ' +
                'nav, aside, header, footer'
            );
            unwantedInside.forEach(el => el.remove());
            
            // Pega o título da página
            const title = document.title;
            
            // Limpa TUDO do body
            document.body.innerHTML = '';
            
            // Adiciona título se disponível
            if (title && !content.querySelector('h1')) {
                const h1 = document.createElement('h1');
                h1.textContent = title;
                document.body.appendChild(h1);
            }
            
            // Insere o artigo limpo
            document.body.appendChild(content);
            
            console.log(`✅ DOM isolado com sucesso! Conteúdo final: ${document.body.innerText.length} chars`);
        } else {
            console.log('⚠️ Artigo não encontrado. Tentando limpeza genérica...');
            
            // Se não encontrou artigo, remove elementos comuns de navegação
            const genericUnwanted = [
                'header', 'footer', 'nav', 'aside', 
                '[role="navigation"]', '[role="banner"]',
                '[role="complementary"]', '.sidebar', '.menu',
                '[class*="ad"]', '[id*="ad"]'
            ];
            
            genericUnwanted.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
        }
        
        // ===== FASE 5: Scroll Completo para Lazy Load =====
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(1500);
        window.scrollTo(0, 0);
        await sleep(500);
        
        console.log(`🏁 PROTOCOLO CONCLUÍDO - Texto final: ${document.body.innerText.length} chars`);
    })();
    """

    # 4. Markdown Generator otimizado
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,  # Mantém links para referência
            "ignore_images": True,
            "body_width": 0,
            "citations": False,
            "escape_html": True
        }
    )

    # 5. Run Config OTIMIZADO
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        cache_mode=CacheMode.BYPASS,
        
        # Stealth mode COMPLETO
        magic=True,
        simulate_user=True,
        override_navigator=True,
        
        js_code=js_handler,
        virtual_scroll_config=scroll_config,
        
        # Espera genérica - só garante que a página carregou
        wait_for="js:() => document.readyState === 'complete'",
        page_timeout=60000,  # 60s timeout
        delay_before_return_html=5.0,  # Mais tempo para JS rodar completamente
        
        # Exclusões extras
        excluded_tags=['script', 'style', 'iframe', 'noscript'],
        excluded_selector=", ".join([
            "#cookie-banner",
            ".ms-consent-banner", 
            ".privacy-modal",
            "[id*='consent']",
            "[class*='gdpr']"
        ])
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Crawl falhou: {result.error_message}"
                )

            raw_md = result.markdown.raw_markdown

            # ===== FASE 5: Pós-Processamento Python =====
            
            # Lista de frases-chave de banners (expandida)
            banner_phrases = [
                "Microsoft Cares About Your Privacy",
                "A Microsoft Preocupa-se Com a Sua Privacidade",
                "We and our partners process data",
                "Number of Partners (vendors)",
                "I Accept Reject All Manage Preferences",
                "About Your Privacy",
                "Personalised advertising and content",
                "Use precise geolocation data",
                "Store and/or access information on a device",
                "List of Partners",
                "Privacy Statement",
                "Declaração de Privacidade",
                "Manage Preferences",
                "Gerenciar preferências"
            ]
            
            # Detecta se é principalmente banner
            banner_ratio = sum(1 for phrase in banner_phrases if phrase in raw_md)
            is_mostly_banner = banner_ratio >= 3  # Se encontrou 3+ frases
            
            if is_mostly_banner:
                print(f"⚠️ BANNER DETECTADO ({banner_ratio} frases encontradas)")
                
                # Tenta encontrar separador
                for separator in banner_phrases[-4:]:  # Usa últimos 4 como separadores
                    if separator in raw_md:
                        parts = raw_md.split(separator, 1)
                        if len(parts) > 1 and len(parts[-1]) > 300:
                            raw_md = parts[-1]
                            print(f"✂️ Cortado após '{separator}'")
                            break
                
                # Se ainda pequeno, tenta regex para pegar parágrafos longos
                if len(raw_md) < 500:
                    paragraphs = re.findall(r'\n\n(.{200,}?)\n\n', raw_md)
                    if paragraphs:
                        raw_md = '\n\n'.join(paragraphs)
                        print("✂️ Extraído via regex de parágrafos")
            
            # Remove linhas muito curtas (provavelmente menu/navegação)
            lines = raw_md.split('\n')
            cleaned_lines = [
                line for line in lines 
                if len(line.strip()) > 15 or line.strip().startswith('#')
            ]
            raw_md = '\n'.join(cleaned_lines)
            
            # Limpa espaços excessivos
            raw_md = re.sub(r'\n{3,}', '\n\n', raw_md).strip()
            
            # ===== FASE 6: Validação de Qualidade =====
            word_count = len(raw_md.split())
            
            quality_check = {
                "has_content": len(raw_md) > 200,
                "word_count": word_count,
                "likely_article": word_count > 100,
                "banner_detected": is_mostly_banner
            }
            
            return {
                "success": True,
                "url": request.url,
                "content_length": len(raw_md),
                "word_count": word_count,
                "quality_check": quality_check,
                "markdown": raw_md,
                "raw_html_length": len(result.html) if result.html else 0
            }
            
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "crawl4ai-optimized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
