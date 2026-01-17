from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler

# Inicializa a API
app = FastAPI(title="Crawl4AI API Service")

# Define o formato dos dados que a API espera receber
class CrawlRequest(BaseModel):
    url: str
    # Você pode adicionar mais opções aqui se quiser (ex: javascript_enabled: bool)

@app.post("/crawl")
async def crawl_url(request: CrawlRequest):
    """
    Recebe uma URL e retorna o conteúdo em Markdown.
    """
    print(f"Recebendo pedido para: {request.url}")
    
    try:
        # Inicializa o Crawler
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(url=request.url)
            
            # Retorna o resultado
            return {
                "success": True,
                "url": request.url,
                "markdown": result.markdown,
                "html": result.html # Opcional, se quiser o HTML puro
            }
            
    except Exception as e:
        print(f"Erro ao processar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"message": "Crawl4AI API is running! Use POST /crawl endpoint."}
