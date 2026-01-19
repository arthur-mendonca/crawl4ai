from pydantic import BaseModel

class CrawlRequest(BaseModel):
    url: str
    min_words: int = 100
