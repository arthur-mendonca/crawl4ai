from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig
import re
import json
import httpx
from urllib.parse import urlparse
from bs4 import BeautifulSoup

app = FastAPI(title="Crawl4AI v4 - MSN API + Anti-Bot")

class CrawlRequest(BaseModel):
    url: str
    min_words: int = 100

def extract_msn_article_id(url: str) -> str | None:
    """Extrai o ID do artigo de URLs do MSN (ex: AA1UiYJv)"""
    # Padrão: /ar-AA1UiYJv ou /ar-AA1UiYJv?parametros
    match = re.search(r'/ar-([A-Za-z0-9]+)', url)
    if match:
        article_id = match.group(1)
        # Remove query params se estiverem grudados
        article_id = article_id.split('?')[0]
        return article_id
    return None

async def fetch_msn_api(article_id: str) -> dict | None:
    """Busca conteúdo direto da API do MSN"""
    # Detecta idioma da URL (padrão en-us)
    locale = "en-us"  # Pode ser extraído da URL original se necessário
    
    api_url = f"https://assets.msn.com/content/view/v2/Detail/{locale}/{article_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.msn.com/"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ MSN API retornou {response.status_code}")
                return None
    except Exception as e:
        print(f"❌ Erro ao buscar MSN API: {e}")
        return None

def msn_json_to_markdown(data: dict) -> str:
    """Converte JSON da API do MSN para markdown"""
    parts = []
    
    # Título
    if 'title' in data:
        parts.append(f"# {data['title']}\n")
    
    # Autores
    if 'authors' in data and data['authors']:
        authors = ', '.join(a.get('name', '') for a in data['authors'])
        parts.append(f"**Por:** {authors}\n")
    
    # Abstract/resumo
    if 'abstract' in data:
        parts.append(f"*{data['abstract']}*\n")
    
    # Corpo do artigo (HTML)
    if 'body' in data:
        # Remove tags HTML e converte para texto limpo
        soup = BeautifulSoup(data['body'], 'html.parser')
        
        # Remove scripts, styles, etc
        for tag in soup(['script', 'style', 'iframe', 'noscript']):
            tag.decompose()
        
        # Extrai texto
        text = soup.get_text(separator='\n', strip=True)
        
        # Limpa linhas vazias excessivas
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        parts.append(text)
    
    # Fonte original
    if 'sourceHref' in data:
        parts.append(f"\n---\n**Fonte:** [{data['sourceHref']}]({data['sourceHref']})")
    
    return '\n\n'.join(parts)

def extract_article_by_density(markdown: str, title: str = "") -> str:
    """Extrai artigo por densidade de texto (fallback)"""
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    blocks = [b.strip() for b in markdown.split('\n\n') if b.strip()]
    
    scored_blocks = []
    for block in blocks:
        words = block.split()
        word_count = len(words)
        
        if word_count < 10:
            continue
        
        score = min(word_count, 500)
        
        if block.count('[') > 5 or block.count('http') > 3:
            score -= 50
        
        lines = block.split('\n')
        if len(lines) > 5 and sum(len(l) < 50 for l in lines) > len(lines) * 0.7:
            score -= 30
        
        banner_words = ['privacy', 'cookie', 'consent', 'partners', 'vendors', 
                       'preferences', 'advertising', 'manage', 'accept', 'reject',
                       'cloudflare', 'checking your browser', 'enable javascript']
        if sum(1 for w in banner_words if w in block.lower()) >= 3:
            score -= 100
        
        score += min(block.count('.') + block.count('!') + block.count('?'), 20)
        
        if block.strip().endswith('.'):
            score += 30
        
        scored_blocks.append((score, block, word_count))
    
    scored_blocks.sort(reverse=True, key=lambda x: x[0])
    
    result_blocks = []
    total_words = 0
    
    for score, block, word_count in scored_blocks:
        if score > 0 and total_words < 2000:
            result_blocks.append(block)
            total_words += word_count
    
    result = '\n\n'.join(result_blocks)
    
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
