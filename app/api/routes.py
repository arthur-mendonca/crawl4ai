from fastapi import APIRouter, HTTPException
from app.api.models import CrawlRequest
from app.core.crawler import get_page_content
from app.core.extraction import extract_article_by_density, extract_paragraphs_fallback
from app.services.msn import extract_msn_article_id, fetch_msn_api, msn_json_to_markdown
import re

router = APIRouter()

@router.post("/crawl")
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
    try:
        result = await get_page_content(url)
        
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
            fallback_md = extract_paragraphs_fallback(raw_md, title)
            if fallback_md:
                cleaned_md = fallback_md
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

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "crawl4ai-v4"}
