import os
import sys
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig
from crawl4ai import UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.async_logger import AsyncLogger, LogLevel
from app.utils.scripts import JS_HANDLER

async def get_page_content(url: str):
    """
    Executes the crawler for a given URL with anti-bot configuration.
    Returns the CrawlResult object.
    """
    # Remove espaços e quebras de linha que podem causar erro de DNS
    url = url.strip()
    print(f"DEBUG: Crawling URL: '{url}'")

    # Define headless based on env var, defaulting to False (dev) or True (prod/linux)
    # In production (Linux), set default to true to avoid "no display" errors.
    default_headless = "true" if sys.platform == "linux" else "false"
    is_headless = os.getenv("HEADLESS", default_headless).lower() == "true"

    browser_config = BrowserConfig(
        headless=is_headless, 
        verbose=True,
        user_agent_mode="random",
        # enable_stealth=True, # Desativado pois estava causando ERR_BLOCKED_BY_CLIENT
        viewport_width=1920,
        viewport_height=1080,
        # headers={ # Comentado para evitar conflito com stealth
        #    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        #    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        #    "Cache-Control": "no-cache",
        #    "Pragma": "no-cache"
        # }
    )

    # Configuração do Adapter para evitar detecção (Cloudflare, etc)
    # undetected_adapter = UndetectedAdapter()
    
    # Logger explícito para evitar crash em AsyncPlaywrightCrawlerStrategy
    # logger = AsyncLogger(log_level=LogLevel.DEBUG, verbose=True)

    # Estratégia do Crawler usando o adapter padrão com Stealth ativado
    # Voltar ao padrão pode resolver problemas com outros sites e ainda passar pelo Cloudflare com stealth
    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        # browser_adapter=undetected_adapter,
        # logger=logger
    )

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
        # Ativa captura de logs para debug
        # capture_console_messages=True, # Seems to be in BrowserConfig or not fully exposed in RunConfig type hint but works in kwargs?
        
        cache_mode=CacheMode.BYPASS,
        magic=True, # Reativado pois parece estável com logger e sem virtual_scroll
        simulate_user=True, # Reativado para ajudar no bypass
        override_navigator=False, # Desativado para evitar conflitos se stealth estivesse on, mas ok deixar false com adapter
        js_code=JS_HANDLER,
        # virtual_scroll_config removido pois causa crash com UndetectedAdapter
        # O JS_HANDLER já faz o scroll necessário
        
        # Aguarda carregamento inicial simples, o resto é tratado no JS_HANDLER
        wait_for="js:() => document.readyState === 'complete'",
        page_timeout=60000,  # 60s para dar tempo ao Cloudflare
        delay_before_return_html=2.0,  # Tempo extra após JS_HANDLER terminar
        excluded_tags=['script', 'style', 'iframe', 'noscript']
    )

    async with AsyncWebCrawler(config=browser_config, crawler_strategy=crawler_strategy) as crawler:
        result = await crawler.arun(url=url, config=config)
        return result
