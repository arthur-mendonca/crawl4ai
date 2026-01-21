
JS_HANDLER = """
(async () => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    
    // Espera inicial mais longa para Cloudflare
    await sleep(5000);
    
    // Procura por challenge do Cloudflare
    const cfChallenge = document.querySelector('#challenge-running');
    if (cfChallenge) {
        console.log('⏳ Cloudflare challenge detectado, aguardando...');
        await sleep(8000); // Espera o challenge resolver
    }
    
    // Remove overlays
    ['.modal', '.overlay', '[aria-modal="true"]', '[class*="consent"]', 
     '[class*="cookie"]', '[class*="privacy"]'].forEach(sel => {
        document.querySelectorAll(sel).forEach(el => el.remove());
    });
    
    // Clica em aceitar
    const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
    const acceptBtn = btns.find(b => 
        /accept|agree|ok|continue|aceitar|permitir/i.test(b.innerText) && 
        b.innerText.length < 60
    );
    if (acceptBtn) {
        console.log('✅ Clicando em aceitar');
        acceptBtn.click();
        await sleep(3000);
    }
    
    // Scroll completo
    for (let i = 0; i < 3; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(1500);
    }
    window.scrollTo(0, 0);
    
    console.log('🏁 JS concluído');
})();
"""
