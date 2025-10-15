def select_best_assets(predictions, fundamentals=None):
    selected = []
    for p in predictions:
        g = p['predicted_growth_%']
        c = p['confidence']
        score = g * c
        if g > 1.5 and c > 0.2:
            selected.append({**p, "score": score})
    
    # сортировка по score
    selected = sorted(selected, key=lambda x: x['score'], reverse=True)
    # ограничение top-N
    return selected[:10]
