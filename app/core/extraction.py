import re

def extract_article_by_density(markdown: str, title: str = "") -> str:
    """Extrai artigo por densidade de texto (fallback)"""
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    blocks = [b.strip() for b in markdown.split('\n\n') if b.strip()]
    
    scored_blocks = []
    for block in blocks:
        # 1. Limpeza preliminar para pontuação precisa
        # Remove URLs e converte links markdown para texto puro para contar palavras reais
        clean_text = re.sub(r'https?://\S+', '', block)
        clean_text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', clean_text)
        clean_text = clean_text.replace('()', '').replace('[]', '').replace('[ ]', '')
        
        words = clean_text.split()
        word_count = len(words)
        
        # Ignora blocos vazios ou muito curtos após limpeza
        if word_count < 5:
            continue
            
        # 2. Pontuação Base
        score = min(word_count, 500)
        
        # 3. Análise de Links (no bloco original)
        link_count = block.count('[') + block.count('http')
        
        # Se tiver links, verifica a densidade em relação ao texto limpo
        if link_count > 0:
            # Densidade = links / palavras reais
            link_density = link_count / max(word_count, 1)
            
            # Penaliza apenas se for MUITO denso (menu/lista de links)
            # Aumentado para 0.5 (50%) para não pegar artigos com muitas citações
            if link_density > 0.5:
                score -= 500  # Penalidade forte, mas não fatal imediata
            elif link_density > 0.3:
                score -= 100
        
        block_lower = block.lower()
        
        # 4. Penalidades Estruturais
        # Penaliza linhas curtas repetitivas (menu vertical)
        lines = block.split('\n')
        short_lines = sum(1 for l in lines if len(l.strip()) < 50)
        if len(lines) > 3 and short_lines > len(lines) * 0.6:
            score -= 200
            
        # Penaliza palavras-chave de navegação
        nav_words = ['menu', 'toggle', 'submit', 'search', 'topics', 'more from',
                     'newsletter', 'podcast', 'contact us', 'sign up', 'subscribe', 
                     'related stories', 'read more', 'latest news', 'site map']
        
        if any(w in block_lower for w in nav_words):
             score -= 100
            
        # Penaliza rodapés e banners
        footer_words = ['all rights reserved', 'copyright', 'privacy policy', 'terms of use', 
                       'cookie', 'consent', 'advertising']
        if any(w in block_lower for w in footer_words):
             score -= 200
        
        # 5. Bônus
        # Pontuação de frase (indica texto corrido)
        score += min(clean_text.count('.') + clean_text.count('!') + clean_text.count('?'), 50)
        
        # Parágrafos longos (conteúdo real)
        if word_count > 40:
            score += 100 # Aumentei o bônus
            
        scored_blocks.append((score, clean_text, word_count))
    
    # Filtra blocos com score muito baixo
    scored_blocks = [b for b in scored_blocks if b[0] > 0]
    
    if scored_blocks:
        # Seleção baseada na mediana para evitar outliers
        sorted_scores = sorted([s[0] for s in scored_blocks])
        median_score = sorted_scores[len(sorted_scores)//2]
        
        # Threshold conservador: 20% da mediana
        # Isso garante que parágrafos normais passem, mas lixo puro (score negativo/zero) fique de fora
        threshold = max(median_score * 0.2, 10)
        
        final_blocks = []
        for score, text, _ in scored_blocks:
             if score >= threshold:
                 final_blocks.append(text.strip())
                 
        result = '\n\n'.join(final_blocks)
    else:
        result = ""
    
    if title and not result.startswith('#'):
        result = f"# {title}\n\n{result}"
    
    return result

def extract_paragraphs_fallback(raw_md: str, title: str = "") -> str:
    """Extração de fallback baseada em parágrafos longos"""
    paragraphs = re.findall(r'([^\n]{100,})', raw_md)
    
    good_paragraphs = [
        p for p in paragraphs 
        if not any(kw in p.lower() for kw in 
                  ['cookie', 'privacy', 'consent', 'cloudflare', 
                   'checking', 'browser', 'javascript'])
    ]
    
    if good_paragraphs:
        cleaned_md = '\n\n'.join(good_paragraphs[:10])
        
        # Aplica limpeza de links também no fallback
        cleaned_md = re.sub(r'https?://\S+', '', cleaned_md)
        cleaned_md = re.sub(r'<https?://[^>]+>', '', cleaned_md)
        cleaned_md = cleaned_md.replace('()', '')
        
        if title:
            cleaned_md = f"# {title}\n\n{cleaned_md}"
        return cleaned_md
    return ""
