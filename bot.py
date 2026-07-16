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
    Analyse les gros titres économiques et géopolitiques récents.
    Détermine si le climat mondial est tendu (guerres, inflation, hausse des taux)
    et ajuste les scores sectoriels en conséquence.
    """
    contexte = {
        "facteur_defense": 1.0,
        "facteur_tech": 1.0,
        "facteur_banques": 1.0,
        "synthese": "Climat macroéconomique global stable."
    }
    
    try:
        # Scan rapide des news via un flux RSS ou une API publique d'actualités financières
        url = "https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey=YOUR_NEWS_API_KEY" # Optionnel
        # Pour rester 100% gratuit et sans clé, on utilise un flux RSS de Yahoo Finance ou Reuters
        rss_url = "https://finance.yahoo.com/news/rssindex"
        response = requests.get(rss_url, timeout=10)
        text = response.text.lower()
        
        tensions = ["war", "conflict", "geopolitical", "military", "escalation", "strike"]
        inflation_rates = ["inflation", "rates hike", "fed", "central bank"]
        
        score_tension = sum(1 for mot in tensions if mot in text)
        score_inflation = sum(1 for mot in inflation_rates if mot in text)
        
        if score_tension > 2:
            contexte["facteur_defense"] = 1.3  # Favorise grandement le secteur Défense
            contexte["facteur_tech"] = 0.85     # Pénalise légèrement la Tech de croissance
            contexte["synthese"] = "⚠️ Risques géopolitiques / conflits détectés dans l'actualité mondiale."
        elif score_inflation > 3:
            contexte["facteur_banques"] = 1.2  # Les banques profitent généralement des taux élevés
            contexte["synthese"] = "📈 Focus macroéconomique sur l'inflation et les décisions des banques centrales."
            
    except Exception as e:
        print(f"Impossible d'analyser les news : {e}. Utilisation du profil neutre.")
        
    return contexte

def recuperer_tickers_dynamiques():
    """
    Génère dynamiquement une liste d'actions majeures à scanner 
    en fonction de l'indice de référence de la session mondiale.
    """
    # Pour le test et l'efficacité sur GitHub Actions, on prend un échantillon large et représentatif des grosses capitalisations mondiales
    # incluant US, Europe, Japon et Australie (les 4 sessions).
    tickers_mondiaux = [
        # USA (S&P 500 principaux par secteurs)
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "LLY", "AVGO", "TSLA", "JPM", "UNH", "V", "XOM", "LMT", "RTX", "PLTR",
        # EUROPE (Stoxx 600 principaux)
        "ASML", "MC.PA", "OR.PA", "NESN.SW", "NOVN.SW", "SAP", "SIE.DE", "AIR.PA", "TTE.PA", "HSBA.L", "BP.L",
        # ASIE (Nikkei principaux)
        "7203.T", "9984.T", "6758.T", "8035.T", "6861.T",
        # SYDNEY (ASX principaux)
        "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX"
    ]
    return tickers_mondiaux

def evaluer_action(ticker_symbol, contexte_macro):
    """
    Analyse en profondeur les fondamentaux universels et sectoriels d'une entreprise.
    Attribue un score final sur 100.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        secteur = info.get('industry', 'Autre')
        score = 50 # Base
        
        # --- CRITÈRES FINANCIERS UNIVERSELS ---
        # Croissance CA
        rev_growth = info.get('revenueGrowth', 0)
        if rev_growth > 0.15: score += 10
        elif rev_growth > 0.25: score += 15
        elif rev_growth < 0: score -= 15
        
        # Marges (Marge brute & Marge opérationnelle)
        marge_brute = info.get('grossMargins', 0)
        marge_op = info.get('operatingMargins', 0)
        if marge_brute > 0.40: score += 5
        if marge_op > 0.20: score += 10
        
        # Endettement (Dette/EBITDA)
        dette_ebitda = info.get('debtToEbitda', 5)
        if dette_ebitda < 2: score += 10
        elif dette_ebitda > 4: score -= 15
        
        # Rentabilité (ROE & ROIC)
        roe = info.get('returnOnEquity', 0)
        if roe > 0.20: score += 10
        
        # Flux de trésorerie (FCF positif)
        fcf = info.get('freeCashflow', 0)
        if fcf > 0: score += 5

        # --- CRITÈRES SECTORIELS AVANCÉS ---
        # 1. IA & Semi-conducteurs
        if "semiconductors" in secteur.lower() or "software" in secteur.lower():
            score = int(score * contexte_macro["facteur_tech"])
            if marge_brute > 0.50: score += 10
            
        # 2. Défense
        elif "aerospace & defense" in secteur.lower():
            score = int(score * contexte_macro["facteur_defense"])
            # Importance du carnet de commandes / marge stable
            if marge_op > 0.12: score += 10
            
        # 3. Banques
        elif "banks" in secteur.lower():
            score = int(score * contexte_macro["facteur_banques"])
            if roe > 0.12: score += 10

        return min(max(score, 0), 100), secteur, info.get('longName', ticker_symbol)
    except:
        return 0, "Inconnu", ticker_symbol

def executer_scan():
    contexte_macro = analyser_contexte_global()
    tickers = recuperer_tickers_dynamiques()
    
    opportunites = []
    
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo")
            if len(hist) < 20: continue
            
            # Calcul strict du RSI (14)
            rsi_series = ta.momentum.rsi(hist['Close'], window=14)
            rsi_actuel = rsi_series.iloc[-1]
            
            # FILTRE STRICT : RSI < 30
            if rsi_actuel < 30:
                score, secteur, nom_complet = evaluer_action(symbol, contexte_macro)
                
                # Récupération du prix actuel
                prix_actuel = hist['Close'].iloc[-1]
                
                opportunites.append({
                    "symbol": symbol,
                    "nom": nom_complet,
                    "secteur": secteur,
                    "rsi": round(rsi_actuel, 2),
                    "score": score,
                    "prix": round(prix_actuel, 2)
                })
        except Exception as e:
            print(f"Erreur d'analyse sur {symbol} : {e}")

    # Classement par score fondamental & conservation des 3 MEILLEURES opportunités
    meilleures_opportunites = sorted(opportunites, key=lambda x: x['score'], reverse=True)[:3]
    
    if meilleures_opportunites:
        maintenant = datetime.now().strftime('%Y-%m-%d %H:%M')
        message = f"<b>🔔 RADAR MARCHÉ - {maintenant} (Heure Locale)</b>\n"
        message += f"<i>{contexte_macro['synthese']}</i>\n\n"
        message += "<b>🎯 LES 3 MEILLEURES ACTIONS À SURVEILLER (RSI < 30) :</b>\n\n"
        
        for i, opti in enumerate(meilleures_opportunites, 1):
            message += f"<b>{i}. {opti['nom']} ({opti['symbol']})</b>\n"
            message += f"▪️ Secteur : {opti['secteur']}\n"
            message += f"▪️ Prix : {opti['prix']}$\n"
            message += f"▪️ RSI (14) : 🟢 <b>{opti['rsi']}</b>\n"
            message += f"▪️ Score Fondamental & Macro : <b>{opti['score']}/100</b>\n\n"
            
        envoyer_telegram(message)
    else:
        print("Aucun signal qualifié (RSI < 30) trouvé pour cette session.")

if __name__ == "__main__":
    executer_scan()
