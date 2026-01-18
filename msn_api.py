import re
import httpx
from bs4 import BeautifulSoup


def extract_msn_article_id(url: str) -> str | None:
    match = re.search(r"/ar-([A-Za-z0-9]+)", url)
    if match:
        article_id = match.group(1)
        article_id = article_id.split("?")[0]
        return article_id
    return None


async def fetch_msn_api(article_id: str) -> dict | None:
    locale = "en-us"
    api_url = f"https://assets.msn.com/content/view/v2/Detail/{locale}/{article_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.msn.com/",
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
    parts = []

    if "title" in data:
        parts.append(f"# {data['title']}\n")

    if "authors" in data and data["authors"]:
        authors = ", ".join(a.get("name", "") for a in data["authors"])
        parts.append(f"**Por:** {authors}\n")

    if "abstract" in data:
        parts.append(f"*{data['abstract']}*\n")

    if "body" in data:
        soup = BeautifulSoup(data["body"], "html.parser")

        for tag in soup(["script", "style", "iframe", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)

        parts.append(text)

    if "sourceHref" in data:
        parts.append(f"\n---\n**Fonte:** [{data['sourceHref']}]({data['sourceHref']})")

    return "\n\n".join(parts)

