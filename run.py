import sys
import asyncio
import uvicorn

# Configuração crítica para Windows + Playwright
# O loop padrão (SelectorEventLoop) não suporta subprocessos no Windows, o que quebra o Playwright.
# Precisamos forçar o ProactorEventLoop antes de qualquer operação assíncrona.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    print("🚀 Iniciando servidor com suporte a Playwright no Windows...")
    # NOTA: reload=True foi removido pois causa conflito com o ProactorEventLoop no Windows
    # ao criar subprocessos que perdem a configuração da política de loop.
    # Para desenvolvimento com reload, seria necessário configurar o uvicorn de outra forma,
    # mas para garantir funcionamento estável do Playwright, rodamos sem reload.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
