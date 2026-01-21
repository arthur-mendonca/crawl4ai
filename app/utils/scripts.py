
JS_HANDLER = """
(async () => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    
    console.log('🚀 Iniciando JS Handler customizado...');
    
    // Loop de espera para Cloudflare (max 60s)
    const maxWait = 60000;
    const start = Date.now();
    
    while (Date.now() - start < maxWait) {
        const title = document.title;
        
        // Se título vazio, espera carregar
        if (!title || title.trim() === '') {
            console.log('⏳ Título vazio, aguardando...');
            await sleep(1000);
            continue;
        }

        const isCloudflare = title.includes('Um momento') || 
                             title.includes('Just a moment') || 
                             title.includes('Attention Required') ||
                             title.includes('Security Check');
                             
        if (!isCloudflare) {
            console.log('✅ Página real carregada: ' + title);
            break;
        }
        
        console.log('⏳ Cloudflare detectado (' + title + '), tentando passar...');
        
        // Tenta encontrar e clicar no checkbox (Turnstile/Challenge)
        // Estratégia: Encontrar Shadow Hosts e clicar dentro
        
        function clickShadow(root) {
             // Tenta clicar em inputs/buttons dentro do shadow root
             const clickables = root.querySelectorAll('input[type="checkbox"], div.cb-i, a.cb-i, #challenge-stage, .ctp-checkbox-label');
             clickables.forEach(el => {
                 console.log('👆 Tentando clicar em elemento Shadow DOM:', el);
                 el.click();
             });
        }

        // Procura em todos os elementos da página
        const allNodes = document.querySelectorAll('*');
        for (const node of allNodes) {
            if (node.shadowRoot) {
                clickShadow(node.shadowRoot);
            }
        }
        
        // Tenta clicar em iframes
        const iframes = document.querySelectorAll('iframe');
        iframes.forEach(iframe => {
            try {
                // Tenta focar no iframe (simula atenção do usuário)
                iframe.focus();
                
                // Em alguns casos, o desafio é apenas um clique no iframe
                // Mas não podemos acessar o conteúdo do iframe se for cross-origin
                // Podemos tentar "clicar" no elemento iframe em si
                iframe.click();
            } catch (e) {}
        });
        
        // Tenta clicar no wrapper se existir
        const wrapper = document.querySelector('#turnstile-wrapper') || 
                        document.querySelector('#challenge-stage') ||
                        document.querySelector('.h-captcha');
        if (wrapper) {
            try { wrapper.click(); } catch(e) {}
        }

        // Espera 3s antes de checar novamente (dá tempo para o clique processar)
        await sleep(3000);
    }
    
    // Remove overlays
    ['.modal', '.overlay', '[aria-modal="true"]', '[class*="consent"]', 
     '[class*="cookie"]', '[class*="privacy"]'].forEach(sel => {
        document.querySelectorAll(sel).forEach(el => el.remove());
    });
    
    // Clica em aceitar cookies/termos
    const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
    const acceptBtn = btns.find(b => 
        /accept|agree|ok|continue|aceitar|permitir/i.test(b.innerText) && 
        b.innerText.length < 60
    );
    if (acceptBtn) {
        console.log('✅ Clicando em aceitar');
        try { acceptBtn.click(); } catch(e) {}
        await sleep(3000);
    }
    
    // Scroll completo para carregar lazy loading
    console.log('📜 Iniciando scroll...');
    for (let i = 0; i < 3; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(1500);
    }
    window.scrollTo(0, 0);
    
    console.log('🏁 JS concluído');
})();
"""
