import os
import requests
import yfinance as yf
import pandas as pd
import ta
from datetime import datetime

TOKEN = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")
FICHIER_MEMOIRE = "alertes_envoyees.txt"

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def charger_alertes_deja_envoyees():
    if os.path.exists(FICHIER_MEMOIRE):
        with open(FICHIER_MEMOIRE, "r") as f:
            lignes = f.read().splitlines()
        aujourd_hui = datetime.now().strftime("%Y-%m-%d")
        alertes_valides = []
        for ligne in lignes:
            if "|" in ligne:
                date, ticker = ligne.split("|")
                if date == aujourd_hui:
                    alertes_valides.append(ticker)
        return alertes_valides
    return []

def enregistrer_nouvelles_alertes(tickers_alertes):
    aujourd_hui = datetime.now().strftime("%Y-%m-%d")
    deja_envoyees = charger_alertes_deja_envoyees()
    total_alertes = set(deja_envoyees + tickers_alertes)
    
    with open(FICHIER_MEMOIRE, "w") as f:
        for ticker in total_alertes:
            f.write(f"{aujourd_hui}|{ticker}\n")

def analyser_contexte_global():
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
    return [
        "intelligence artificielle", "semi-conducteurs", "cybersécurité", "défense", 
        "data centers", "cloud", "robotique", "automatisation", "électricité", "réseaux électriques", 
        "nucléaire", "santé", "medtech", "équipements médicaux", "eau", "spatial", 
        "batteries", "stockage", "logiciels saas", "saas", "industrie de précision", 
        "énergies renouvelables", "mines", "logistique", "fintech", "biotechnologies",
        "software", "semiconductors", "aerospace", "biotechnology", "pharmaceuticals"
    ]

def generer_liste_tickers_dynamique():
    tickers = set()
    try:
        url_sp500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url_sp500)
        sp500_df = tables[0]
        tickers.update(sp500_df['Symbol'].tolist())
    except Exception as e:
        print(f"Erreur récupération S&P 500 : {e}")
        
    grandes_valeurs_monde = [
        "ASML", "MC.PA", "OR.PA", "SAP", "SIE.DE", "AIR.PA", "TTE.PA", "NESN.SW", "NOVN.SW",
        "7203.T", "9984.T", "6758.T", "8035.T", "BHP.AX", "CBA.AX", "CSL.AX", "RIO"
    ]
    tickers.update(grandes_valeurs_monde)
    return [t.replace('.', '-') if not t.endswith(('.PA', '.DE', '.T', '.AX', '.CO', '.SW')) else t for t in tickers]

def evaluer_action(info, contexte_macro):
    score = 50
    try:
        growth = info.get('revenueGrowth', 0) or 0
        if growth > 0.25: score += 15
        elif growth > 0.15: score += 10
        elif growth < 0: score -= 15

        marge_brute = info.get('grossMargins', 0) or 0
        marge_op = info.get('operatingMargins', 0) or 0
        if marge_brute > 0.50: score += 10
        if marge_op > 0.20: score += 10

        roe = info.get('returnOnEquity', 0) or 0
        if roe > 0.20: score += 10

        dette_ebitda = info.get('debtToEbitda', 5) or 5
        if dette_ebitda < 2: score += 10
        elif dette_ebitda > 4: score -= 15

        fcf = info.get('freeCashflow', 0) or 0
        if fcf > 0: score += 5

        secteur = (info.get('industry', '') or '').lower()
        if any(keyword in secteur for keyword in ["software", "semiconductors", "computer"]):
            score = int(score * contexte_macro["facteur_tech"])
        elif any(keyword in secteur for keyword in ["aerospace", "defense"]):
            score = int(score * contexte_macro["facteur_defense"])
        elif "mining" in secteur:
            score = int(score * contexte_macro["facteur_mines"])
    except:
        pass
    return min(max(score, 0), 100)

def executer_scan():
    contexte_macro = analyser_contexte_global()
    secteurs_cibles = recuperer_secteurs_cibles()
    deja_alertes = charger_alertes_deja_envoyees()
    
    print("🔄 Scan en cours (Filtre RSI < 35)...")
    tickers = generer_liste_tickers_dynamique()
    opportunites = []
    
    for symbol in tickers:
        if symbol in deja_alertes:
            continue
            
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo") # Télécharge par défaut les bougies de 1 jour
            if len(hist) < 20: continue
            
            rsi_series = ta.momentum.rsi(hist['Close'], window=14)
            rsi_actuel = rsi_series.iloc[-1]
            
            # CONSIGNE : RSI strictement inférieur à 35
            if rsi_actuel < 35:
                info = ticker.info
                secteur_brut = info.get('industry', 'Autre') or 'Autre'
                appartient_aux_secteurs = any(sec in secteur_brut.lower() for sec in secteurs_cibles)
                
                if appartient_aux_secteurs:
                    score = evaluer_action(info, contexte_macro)
                    
                    # Filtrage pour ne garder que des entreprises solides
                    if score >= 55:
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
        except:
            continue

    meilleures_opportunites = sorted(opportunites, key=lambda x: x['score'], reverse=True)[:5]
    
    if meilleures_opportunites:
        maintenant = datetime.now().strftime('%Y-%m-%d %H:%M')
        message = f"<b>🚨 NOUVELLES OPPORTUNITÉS DÉTECTEES - {maintenant}</b>\n"
        message += f"<i>{contexte_macro['synthese']}</i>\n\n"
        message += f"<b>🎯 TOP {len(meilleures_opportunites)} DES OPPORTUNITÉS (RSI &lt; 35) :</b>\n\n"
        
        tickers_a_enregistrer = []
        for i, opti in enumerate(meilleures_opportunites, 1):
            message += f"<b>{i}. {opti['nom']} ({opti['symbol']})</b>\n"
            message += f"▪️ <b>Secteur :</b> {opti['secteur']}\n"
            message += f"▪️ <b>Pays d'origine :</b> {opti['pays']}\n"
            message += f"▪️ <b>Cotation :</b> {opti['bourse']}\n"
            message += f"▪️ <b>Prix actuel :</b> {opti['prix']}$\n"
            message += f"▪️ <b>RSI (14) Daily :</b> 🟢 <b>{opti['rsi']}</b>\n"
            message += f"▪️ <b>Score de Qualité :</b> <b>{opti['score']}/100</b>\n\n"
            tickers_a_enregistrer.append(opti['symbol'])
            
        envoyer_telegram(message)
        enregistrer_nouvelles_alertes(tickers_a_enregistrer)
    else:
        print("Aucune opportunité sous un RSI de 35 n'a été trouvée lors de ce scan.")

if __name__ == "__main__":
    executer_scan()
