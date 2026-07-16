import os
import requests
import yfinance as yf
import pandas as pd
import ta
from datetime import datetime

TOKEN = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def analyser_contexte_global():
    """
    Scanne les actualités macroéconomiques et géopolitiques mondiales
    pour ajuster les scores des secteurs sensibles.
    """
    contexte = {
        "facteur_defense": 1.0,
        "facteur_tech": 1.0,
        "facteur_mines": 1.0,
        "synthese": "Climat macroéconomique mondial stable."
    }
    try:
        rss_url = "https://finance.yahoo.com/news/rssindex"
        response = requests.get(rss_url, timeout=10)
        text = response.text.lower()
        
        tensions = ["war", "conflict", "geopolitical", "military", "escalation", "strike", "missile", "guerre"]
        inflation = ["inflation", "rates", "fed", "ecb", "central bank", "recession", "taux"]
        
        score_tension = sum(1 for mot in tensions if mot in text)
        score_macro = sum(1 for mot in inflation if mot in text)
        
        if score_tension > 2:
            contexte["facteur_defense"] = 1.3
            contexte["facteur_tech"] = 0.90
            contexte["synthese"] = "⚠️ Risques géopolitiques / Conflits détectés dans l'actualité mondiale."
        elif score_macro > 3:
            contexte["facteur_mines"] = 1.2
            contexte["synthese"] = "📈 Focus sur l'inflation et les politiques monétaires des banques centrales."
    except Exception as e:
        print(f"Erreur scan actualités : {e}")
    return contexte

def recuperer_secteurs_cibles():
    """
    Liste textuelle de tes 20 secteurs cibles pour filtrer les découvertes du bot.
    """
    return [
        "intelligence artificielle", "semi-conducteurs", "cybersécurité", "défense", 
        "data centers", "cloud", "robotique", "automatisation", "électricité", "réseaux électriques", 
        "nucléaire", "santé", "medtech", "équipements médicaux", "eau", "spatial", 
        "batteries", "stockage", "logiciels saas", "saas", "industrie de précision", 
        "énergies renouvelables", "mines", "logistique", "fintech", "biotechnologies"
    ]

def generer_liste_tickers_dynamique():
    """
    Génère dynamiquement une large liste de tickers à surveiller en téléchargeant 
    les composants majeurs des indices mondiaux (S&P 500, STOXX 600, ASX, etc.).
    """
    tickers = set()
    
    # 1. Récupération dynamique du S&P 500 (USA) via Wikipédia
    try:
        url_sp500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url_sp500)
        sp500_df = tables[0]
        tickers.update(sp500_df['Symbol'].tolist())
    except Exception as e:
        print(f"Erreur récupération S&P 500 : {e}")
        
    # 2. Ajout de grandes valeurs européennes et asiatiques de référence pour assurer la couverture mondiale
    grandes_valeurs_monde = [
        "ASML", "MC.PA", "OR.PA", "SAP", "SIE.DE", "AIR.PA", "TTE.PA", "NESN.SW", "NOVN.SW", # Europe
        "7203.T", "9984.T", "6758.T", "8035.T", # Japon
        "BHP.AX", "CBA.AX", "CSL.AX", "RIO" # Australie & Mines
    ]
    tickers.update(grandes_valeurs_monde)
    
    # Nettoyage des tickers (remplacement des points par des tirets pour yfinance si nécessaire)
    tickers_propres = [t.replace('.', '-') if not t.endswith(('.PA', '.DE', '.T', '.AX', '.CO', '.SW')) else t for t in tickers]
    return list(tickers_propres)

def evaluer_action(info, contexte_macro):
    """
    Analyse les ratios financiers universels et sectoriels à la volée.
    Retourne un score sur 100.
    """
    score = 50
    try:
        # --- CRITÈRES FINANCIERS UNIVERSELS ---
        # 1. Croissance CA
        growth = info.get('revenueGrowth', 0) or 0
        if growth > 0.25: score += 15
        elif growth > 0.15: score += 10
        elif growth < 0: score -= 15

        # 2. Marges
        marge_brute = info.get('grossMargins', 0) or 0
        marge_op = info.get('operatingMargins', 0) or 0
        if marge_brute > 0.50: score += 10
        if marge_op > 0.20: score += 10

        # 3. Retours sur capitaux (ROE)
        roe = info.get('returnOnEquity', 0) or 0
        if roe > 0.20: score += 10

        # 4. Endettement (Dette / EBITDA)
        dette_ebitda = info.get('debtToEbitda', 5) or 5
        if dette_ebitda < 2: score += 10
        elif dette_ebitda > 4: score -= 15

        # 5. Flux de trésorerie (FCF)
        fcf = info.get('freeCashflow', 0) or 0
        if fcf > 0: score += 5

        # --- AJUSTEMENTS MACRO SECTORIELS ---
        secteur = (info.get('industry', '') or '').lower()
        if any(keyword in secteur for keyword in ["software", "semiconductors", "computer"]):
            score = int(score * contexte_macro["facteur_tech"])
        elif any(keyword in secteur for keyword in ["aerospace", "defense"]):
            score = int(score * contexte_macro["facteur_defense"])
        elif "mining" in secteur:
            score = int(score * contexte_macro["facteur_mines"])

    except Exception as e:
        print(f"Erreur calcul ratios : {e}")
        
    return min(max(score, 0), 100)

def executer_scan():
    contexte_macro = analyser_contexte_global()
    secteurs_cibles = recuperer_secteurs_cibles()
    
    print("🔄 Génération de la liste d'actions mondiales...")
    tickers = generer_liste_tickers_dynamique()
    print(f"🎯 {len(tickers)} actions identifiées pour le scan global.")
    
    opportunites = []
    
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo")
            if len(hist) < 20: continue
            
            # Calcul du RSI (14)
            rsi_series = ta.momentum.rsi(hist['Close'], window=14)
            rsi_actuel = rsi_series.iloc[-1]
            
            # FILTRE STRICT : RSI < 30 (Survente)
            if rsi_actuel < 30:
                info = ticker.info
                secteur_brut = info.get('industry', 'Autre') or 'Autre'
                
                # Vérification : Est-ce que l'action appartient à l'un de nos 20 secteurs ?
                appartient_aux_secteurs = any(sec in secteur_brut.lower() for sec in secteurs_cibles)
                
                if appartient_aux_secteurs:
                    score = evaluer_action(info, contexte_macro)
                    
                    opportunites.append({
                        "symbol": symbol,
                        "nom": info.get('longName', symbol),
                        "secteur": secteur_brut,
                        "bourse": info.get('exchange', 'Inconnue'),
                        "pays": info.get('country', 'Inconnu'),
                        "rsi": round(rsi_actuel, 2),
                        "score": score,
                        "prix": round(hist['Close'].iloc[-1], 2)
                    })
        except Exception as e:
            # On ignore silencieusement les erreurs d'API sur les tickers invalides
            continue

    # Filtrer et trier pour ne garder que les 5 MEILLEURES opportunités
    meilleures_opportunites = sorted(opportunites, key=lambda x: x['score'], reverse=True)[:5]
    
    if meilleures_opportunites:
        maintenant = datetime.now().strftime('%Y-%m-%d %H:%M')
        message = f"<b>🔔 RADAR MARCHÉ DYNAMIQUE - {maintenant}</b>\n"
        message += f"<i>{contexte_macro['synthese']}</i>\n\n"
        message += f"<b>🎯 TOP 5 DES OPPORTUNITÉS DÉCOUVERTES (RSI < 30) :</b>\n\n"
        
        for i, opti in enumerate(meilleures_opportunites, 1):
            message += f"<b>{i}. {opti['nom']} ({opti['symbol']})</b>\n"
            message += f"▪️ <b>Secteur :</b> {opti['secteur']}\n"
            message += f"▪️ <b>Pays d'origine :</b> {opti['pays']}\n"
            message += f"▪️ <b>Cotation :</b> {opti['bourse']}\n"
            message += f"▪️ <b>Prix actuel :</b> {opti['prix']}$\n"
            message += f"▪️ <b>RSI (14) :</b> 🟢 <b>{opti['rsi']}</b>\n"
            message += f"▪️ <b>Score de Qualité :</b> <b>{opti['score']}/100</b>\n\n"
            
        envoyer_telegram(message)
    else:
        print("Aucun signal qualifié (RSI < 30) sur les secteurs cibles lors de ce scan.")

if __name__ == "__main__":
    executer_scan()
