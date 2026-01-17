from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

app = FastAPI(title="Crawl4AI Clean API")

class CrawlRequest(BaseModel):
    url: str

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    # 1. Configuração do Filtro de Conteúdo
    # O PruningContentFilter remove menus, rodapés e ruídos com base na densidade de texto
    content_filter = PruningContentFilter(
        threshold=0.45,           # Sensibilidade para distinguir conteúdo de menus
        min_word_threshold=30,    # Ignora blocos com poucas palavras
        threshold_type="dynamic"
    )

    # 2. Configuração do Gerador de Markdown
    md_generator = DefaultMarkdownGenerator(
        content_filter=content_filter,
        options={
            "ignore_links": False,  # IMPORTANTE: Mantém o texto dos links íntegro
            "ignore_images": True,
            "body_width": 0,
            "citations": True       # Move as URLs para o fim (Referências numeradas)
        }
    )

    # 3. Configuração de Execução
    # Removido o argumento 'main_content_only' que causou o erro
    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # ESTRATÉGIA DE RETORNO:
            # O 'fit_markdown' contém apenas o texto principal (limpo pelo PruningFilter)
            # Como 'citations' está True, ele virá no formato "texto [1]" com referências no fim.
            final_content = result.markdown.fit_markdown

            # Se o filtro for agressivo demais e o resultado for muito curto,
            # retornamos a página inteira limpa (markdown_with_citations).
            if not final_content or len(final_content) < 300:
                final_content = result.markdown.markdown_with_citations

            return {
                "success": True,
                "url": request.url,
                "markdown": final_content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
