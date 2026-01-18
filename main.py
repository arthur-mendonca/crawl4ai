from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig
from msn_api import extract_msn_article_id, fetch_msn_api, msn_json_to_markdown
import re

app = FastAPI(title="Crawl4AI v4 - MSN API + Anti-Bot")

class CrawlRequest(BaseModel):
    url: str
    min_words: int = 100

def extract_article_by_density(markdown: str, title: str = "") -> str:
    """Extrai artigo por densidade de texto (fallback)"""
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    blocks = [b.strip() for b in markdown.split('\n\n') if b.strip()]
    
    scored_blocks = []
    for block in blocks:
        # 1. Limpeza preliminar para pontuação precisa
        # Remove URLs e converte links markdown para texto puro para contar palavras reais
        clean_text = re.sub(r'https?://\S+', '', block)
        clean_text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', clean_text)
        clean_text = clean_text.replace('()', '').replace('[]', '').replace('[ ]', '')
        
        words = clean_text.split()
        word_count = len(words)
        
        # Ignora blocos vazios ou muito curtos após limpeza
        if word_count < 5:
            continue
            
        # 2. Pontuação Base
        score = min(word_count, 500)
        
        # 3. Análise de Links (no bloco original)
        link_count = block.count('[') + block.count('http')
        
        # Se tiver links, verifica a densidade em relação ao texto limpo
        if link_count > 0:
            # Densidade = links / palavras reais
            link_density = link_count / max(word_count, 1)
            
            # Penaliza apenas se for MUITO denso (menu/lista de links)
            # Aumentado para 0.5 (50%) para não pegar artigos com muitas citações
            if link_density > 0.5:
                score -= 500  # Penalidade forte, mas não fatal imediata
            elif link_density > 0.3:
                score -= 100
        
        block_lower = block.lower()
        
        # 4. Penalidades Estruturais
        # Penaliza linhas curtas repetitivas (menu vertical)
        lines = block.split('\n')
        short_lines = sum(1 for l in lines if len(l.strip()) < 50)
        if len(lines) > 3 and short_lines > len(lines) * 0.6:
            score -= 200
            
        # Penaliza palavras-chave de navegação
        nav_words = ['menu', 'toggle', 'submit', 'search', 'topics', 'more from',
                     'newsletter', 'podcast', 'contact us', 'sign up', 'subscribe', 
                     'related stories', 'read more', 'latest news', 'site map']
        
        if any(w in block_lower for w in nav_words):
             score -= 100
            
        # Penaliza rodapés e banners
        footer_words = ['all rights reserved', 'copyright', 'privacy policy', 'terms of use', 
                       'cookie', 'consent', 'advertising']
        if any(w in block_lower for w in footer_words):
             score -= 200
        
        # 5. Bônus
        # Pontuação de frase (indica texto corrido)
        score += min(clean_text.count('.') + clean_text.count('!') + clean_text.count('?'), 50)
        
        # Parágrafos longos (conteúdo real)
        if word_count > 40:
            score += 100 # Aumentei o bônus
            
        scored_blocks.append((score, clean_text, word_count))
    
    # Filtra blocos com score muito baixo
    scored_blocks = [b for b in scored_blocks if b[0] > 0]
    
    if scored_blocks:
        # Seleção baseada na mediana para evitar outliers
        sorted_scores = sorted([s[0] for s in scored_blocks])
        median_score = sorted_scores[len(sorted_scores)//2]
        
        # Threshold conservador: 20% da mediana
        # Isso garante que parágrafos normais passem, mas lixo puro (score negativo/zero) fique de fora
        threshold = max(median_score * 0.2, 10)
        
        final_blocks = []
        for score, text, _ in scored_blocks:
             if score >= threshold:
                 final_blocks.append(text.strip())
                 
        result = '\n\n'.join(final_blocks)
    else:
        result = ""
    
    if title and not result.startswith('#'):
        result = f"# {title}\n\n{result}"
    
    return result

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    url = request.url
    
    # ===== ESTRATÉGIA 1: MSN API DIRETA =====
    if 'msn.com' in url:
        article_id = extract_msn_article_id(url)
        
        if article_id:
            print(f"🎯 MSN detectado! ID do artigo: {article_id}")
            print(f"📡 Buscando via API...")
            
            msn_data = await fetch_msn_api(article_id)
            
            if msn_data:
                markdown = msn_json_to_markdown(msn_data)
                word_count = len(markdown.split())
                
                print(f"✅ Extraído da API do MSN: {word_count} palavras")
                
                return {
                    "success": True,
                    "url": url,
                    "title": msn_data.get('title', ''),
                    "content_length": len(markdown),
                    "word_count": word_count,
                    "quality_check": {
                        "has_content": word_count > 50,
                        "word_count": word_count,
                        "likely_article": word_count >= request.min_words,
                        "extraction_method": "msn_api"
                    },
                    "markdown": markdown,
                    "source": msn_data.get('sourceHref', url)
                }
            else:
                print("⚠️ API do MSN falhou, tentando crawl normal...")
    
    # ===== ESTRATÉGIA 2: CRAWL NORMAL COM ANTI-BOT MÁXIMO =====
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        user_agent_mode="random",
        viewport_width=1920,
        viewport_height=1080,
        headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    )

    # JS para bypass de Cloudflare e outros bots
    js_handler = """
    (async () => {
        const sleep = ms => new Promise(r => setTimeout(r, ms));
        
        // Espera inicial mais longa para Cloudflare
        await sleep(5000);
        
        // Procura por challenge do Cloudflare
        const cfChallenge = document.querySelector('#challenge-running');
        if (cfChallenge) {
            console.log('⏳ Cloudflare challenge detectado, aguardando...');
            await sleep(8000); // Espera o challenge resolver
        }
        
        // Remove overlays
        ['.modal', '.overlay', '[aria-modal="true"]', '[class*="consent"]', 
         '[class*="cookie"]', '[class*="privacy"]'].forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });
        
        // Clica em aceitar
        const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
        const acceptBtn = btns.find(b => 
            /accept|agree|ok|continue|aceitar|permitir/i.test(b.innerText) && 
            b.innerText.length < 60
        );
        if (acceptBtn) {
            console.log('✅ Clicando em aceitar');
            acceptBtn.click();
            await sleep(3000);
        }
        
        // Scroll completo
        for (let i = 0; i < 3; i++) {
            window.scrollTo(0, document.body.scrollHeight);
            await sleep(1500);
        }
        window.scrollTo(0, 0);
        
        console.log('🏁 JS concluído');
    })();
    """

    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": False,
            "ignore_images": True,
            "body_width": 0,
            "citations": False
        }
    )

    scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=3,
        scroll_by="page_height",
        wait_after_scroll=1.5
    )

    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        cache_mode=CacheMode.BYPASS,
        magic=True,
        simulate_user=True,
        override_navigator=True,
        js_code=js_handler,
        virtual_scroll_config=scroll_config,
        wait_for="js:() => document.readyState === 'complete'",
        page_timeout=60000,  # 60s para dar tempo ao Cloudflare
        delay_before_return_html=8.0,  # Delay longo para challenges
        excluded_tags=['script', 'style', 'iframe', 'noscript']
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=config)
            
            if not result.success:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Crawl falhou: {result.error_message}"
                )

            raw_md = result.markdown.raw_markdown
            
            title = ""
            if result.metadata and 'title' in result.metadata:
                title = result.metadata['title']
            
            print(f"\n{'='*60}")
            print(f"URL: {url}")
            print(f"Markdown bruto: {len(raw_md)} chars")
            print(f"Título: {title}")
            
            # Detecta página de challenge
            if any(kw in raw_md.lower() for kw in 
                  ['cloudflare', 'checking your browser', 'enable javascript', 'um momento']):
                print("⚠️ Página de challenge/verificação detectada")
            
            # Extração por densidade
            cleaned_md = extract_article_by_density(raw_md, title)
            word_count = len(cleaned_md.split())
            
            # Fallback para parágrafos longos
            if word_count < request.min_words:
                print("⚠️ Fallback: extração de parágrafos...")
                paragraphs = re.findall(r'([^\n]{100,})', raw_md)
                
                good_paragraphs = [
                    p for p in paragraphs 
                    if not any(kw in p.lower() for kw in 
                              ['cookie', 'privacy', 'consent', 'cloudflare', 
                               'checking', 'browser', 'javascript'])
                ]
                
                if good_paragraphs:
                    cleaned_md = '\n\n'.join(good_paragraphs[:10])
                    
                    # Aplica limpeza de links também no fallback
                    cleaned_md = re.sub(r'https?://\S+', '', cleaned_md)
                    cleaned_md = re.sub(r'<https?://[^>]+>', '', cleaned_md)
                    cleaned_md = cleaned_md.replace('()', '')
                    
                    if title:
                        cleaned_md = f"# {title}\n\n{cleaned_md}"
                    word_count = len(cleaned_md.split())
            
            print(f"Markdown limpo: {len(cleaned_md)} chars, {word_count} palavras")
            print(f"{'='*60}\n")
            
            quality_check = {
                "has_content": len(cleaned_md) > 200,
                "word_count": word_count,
                "likely_article": word_count >= request.min_words,
                "extraction_method": "density" if word_count >= request.min_words else "fallback"
            }
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "content_length": len(cleaned_md),
                "word_count": word_count,
                "quality_check": quality_check,
                "markdown": cleaned_md,
                "raw_markdown_length": len(raw_md)
            }
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "crawl4ai-v4"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
