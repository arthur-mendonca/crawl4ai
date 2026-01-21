# Implementação de Evasão de Bots (Undetected Browser)

Baseado na sua solicitação e na documentação do Crawl4AI, o problema ocorre porque o Cloudflare está detectando o navegador automatizado. A solução recomendada é utilizar o **Undetected Browser Mode**.

## Plano de Implementação

1.  **Modificar `app/core/crawler.py`**:
    *   Importar `UndetectedAdapter` e `AsyncPlaywrightCrawlerStrategy`.
    *   Atualizar `get_page_content` para usar o `UndetectedAdapter`.
    *   Configurar `BrowserConfig` com `headless=False` (essencial para evitar detecção simples) e `enable_stealth=True` (camada extra de proteção).
    *   Instanciar `AsyncWebCrawler` passando a nova `crawler_strategy`.

2.  **Ajustes na Configuração**:
    *   Manter as configurações de scroll e espera que você já definiu, pois são úteis para carregar o conteúdo dinâmico após passar pelo desafio.

## Por que mudar `headless` para `False`?
A documentação e os testes indicam que o modo `headless=True` (sem interface gráfica) é um dos sinais mais fortes para detecção de bots. Para passar pelo Cloudflare, é altamente recomendado que o navegador abra visivelmente (mesmo que em um servidor, usando Xvfb, mas localmente abrirá a janela).

Não são necessárias alterações em `app/core/extraction.py` neste momento, pois o problema é o bloqueio de acesso (Crawler), não a extração do conteúdo (que está falhando porque o conteúdo recebido é a página de bloqueio).
