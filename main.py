from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import re
from collections import Counter

app = FastAPI(title="Crawl4AI v3 - Text Density Extraction")

class CrawlRequest(BaseModel):
    url: str
    min_words: int = 100  # Mínimo de palavras para considerar válido

def extract_article_by_density(markdown: str, title: str = "") -> str:
    """
    Extrai o artigo procurando pelos blocos com maior densidade de texto
    """
    # Remove múltiplas quebras de linha
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    # Divide em blocos por dupla quebra de linha
    blocks = [b.strip() for b in markdown.split('\n\n') if b.strip()]
    
    # Analisa cada bloco
    scored_blocks = []
    for block in blocks:
        words = block.split()
        word_count = len(words)
        
        # Skip blocos muito pequenos
        if word_count < 10:
            continue
        
        # Calcula score baseado em características de artigo
        score = 0
        
        # +1 por palavra (até 500 palavras)
        score += min(word_count, 500)
        
        # -50 se tiver muito link (navegação)
        if block.count('[') > 5 or block.count('http') > 3:
            score -= 50
        
        # -30 se for lista de links curtos
        lines = block.split('\n')
        if len(lines) > 5 and sum(len(l) < 50 for l in lines) > len(lines) * 0.7:
            score -= 30
        
        # -100 se tiver palavras-chave de banner
        banner_words = ['privacy', 'cookie', 'consent', 'partners', 'vendors', 
                       'preferences', 'advertising', 'manage', 'accept', 'reject']
        if sum(1 for w in banner_words if w in block.lower()) >= 3:
            score -= 100
        
        # +20 se tiver pontuação de artigo (. ! ?)
        score += min(block.count('.') + block.count('!') + block.count('?'), 20)
        
        # +30 se tiver parágrafos completos (termina com ponto)
        if block.strip().endswith('.'):
            score += 30
        
        scored_blocks.append((score, block, word_count))
    
    # Ordena por score
    scored_blocks.sort(reverse=True, key=lambda x: x[0])
    
    # Pega os top blocos até atingir bom tamanho
    result_blocks = []
    total_words = 0
    
    for score, block, word_count in scored_blocks:
        if score > 0 and total_words < 2000:  # Até 2000 palavras
            result_blocks.append(block)
            total_words += word_count
    
    # Monta resultado
    result = '\n\n'.join(result_blocks)
    
    # Adiciona título no topo se não tiver
    if title and not result.startswith('#'):
        result = f"# {title}\n\n{result}"
    
    return result

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    
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

    # JS MINIMALISTA - só remove overlays e clica em consentimento
    js_handler = """
    (async () => {
        const sleep = ms => new Promise(r => setTimeout(r, ms));
        await sleep(2000);
        
        // Remove overlays
        ['.modal', '.overlay', '[aria-modal="true"]', '[class*="consent"]', 
         '[class*="cookie"]', '[class*="privacy"]'].forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });
        
        // Clica em aceitar se existir
        const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
        const acceptBtn = btns.find(b => 
            /accept|agree|ok|continue/i.test(b.innerText) && b.innerText.length < 50
        );
        if (acceptBtn) {
            acceptBtn.click();
            await sleep(2000);
        }
        
        // Scroll para carregar lazy content
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(1000);
        window.scrollTo(0, 0);
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
        wait_after_scroll=1.0
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
        page_timeout=45000,  # 45s (reduzido para evitar timeout)
        delay_before_return_html=3.0,
        excluded_tags=['script', 'style', 'iframe', 'noscript'],
        excluded_selector="#cookie-banner, .ms-consent-banner, .privacy-modal"
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
            
            # Extrai título da página
            title = ""
            if result.metadata and 'title' in result.metadata:
                title = result.metadata['title']
            
            print(f"\n{'='*60}")
            print(f"URL: {request.url}")
            print(f"Markdown bruto: {len(raw_md)} chars")
            print(f"HTML: {len(result.html) if result.html else 0} chars")
            print(f"Título: {title}")
            
            # ===== EXTRAÇÃO POR DENSIDADE DE TEXTO =====
            cleaned_md = extract_article_by_density(raw_md, title)
            
            # Validação de qualidade
            word_count = len(cleaned_md.split())
            
            # Se ainda muito pequeno, tenta fallback: pega parágrafos >100 chars
            if word_count < request.min_words:
                print("⚠️ Tentando fallback: extração de parágrafos longos...")
                paragraphs = re.findall(r'([^\n]{100,})', raw_md)
                
                # Filtra parágrafos de banner
                good_paragraphs = [
                    p for p in paragraphs 
                    if not any(kw in p.lower() for kw in 
                              ['cookie', 'privacy', 'consent', 'vendor', 'preference'])
                ]
                
                if good_paragraphs:
                    cleaned_md = '\n\n'.join(good_paragraphs[:10])  # Top 10
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
                "url": request.url,
                "title": title,
                "content_length": len(cleaned_md),
                "word_count": word_count,
                "quality_check": quality_check,
                "markdown": cleaned_md,
                "raw_markdown_length": len(raw_md),
                "raw_html_length": len(result.html) if result.html else 0
            }
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "crawl4ai-v3"}

@app.post("/crawl/debug")
async def crawl_debug(request: CrawlRequest):
    """
    Endpoint de debug que retorna o markdown bruto SEM processamento
    """
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        user_agent_mode="random",
        viewport_width=1920,
        viewport_height=1080
    )

    config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(),
        cache_mode=CacheMode.BYPASS,
        wait_for="js:() => document.readyState === 'complete'",
        page_timeout=30000,
        delay_before_return_html=2.0
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            return {
                "success": result.success,
                "url": request.url,
                "raw_markdown": result.markdown.raw_markdown[:5000],  # Primeiros 5000 chars
                "full_length": len(result.markdown.raw_markdown)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
