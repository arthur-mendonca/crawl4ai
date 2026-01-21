from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_configs import VirtualScrollConfig
from app.utils.scripts import JS_HANDLER

async def get_page_content(url: str):
    """
    Executes the crawler for a given URL with anti-bot configuration.
    Returns the CrawlResult object.
    """
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
        js_code=JS_HANDLER,
        virtual_scroll_config=scroll_config,
        wait_for="js:() => document.readyState === 'complete'",
        page_timeout=60000,  # 60s para dar tempo ao Cloudflare
        delay_before_return_html=8.0,  # Delay longo para challenges
        excluded_tags=['script', 'style', 'iframe', 'noscript']
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=config)
        return result
