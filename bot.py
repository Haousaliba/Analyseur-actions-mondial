import pandas as pd
import requests
import yfinance as yf
import datetime
import os
import sys
import argparse

# Configuration des variables d'environnement
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
VOTRE_CHAT_ID = os.getenv("CHAT_ID")

def recuperer_tickers(region):
    headers = {"User-Agent": "Mozilla/5.0"}
    tickers = []
    
    try:
        if region == "US":
            # S&P 500
            tickers += pd.read_html(requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=headers).text)[0]['Symbol'].tolist()
            # Dow Jones
            tickers += pd.read_html(requests.get("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average", headers=headers).text)[1]['Symbol'].tolist()
            # Nasdaq 100
            tickers += pd.read_html(requests.get("https://en.wikipedia.org/wiki/Nasdaq-100", headers=headers).text)[4]['Ticker'].tolist()
            
        elif region == "EU":
            # CAC 40
            tickers += [f"{t}.PA" for t in pd.read_html(requests.get("https://en.wikipedia.org/wiki/CAC_40", headers=headers).text)[4]['Ticker'].tolist()]
            # DAX
            tickers += [f"{t}.DE" for t in pd.read_html(requests.get("https://en.wikipedia.org/wiki/DAX", headers=headers).text)[4]['Ticker'].tolist()]
            # FTSE 100
            tickers += [f"{t}.L" for t in pd.read_html(requests.get("https://en.wikipedia.org/wiki/FTSE_100_Index", headers=headers).text)[4]['Ticker'].tolist()]
            # Euro Stoxx 50
            tickers += [f"{t}" for t in pd.read_html(requests.get("https://en.wikipedia.org/wiki/Euro_Stoxx_50", headers=headers).text)[4]['Ticker'].tolist()]
            
        elif region == "AU":
            # ASX 200
            asx = pd.read_html(requests.get("https://en.wikipedia.org/wiki/List_of_S%26P/ASX_200_companies", headers=headers).text)[0]['Ticker'].tolist()
            tickers += [f"{t}.AX" for t in asx]
            
        elif region == "ASIA":
            # Sélection qualitative des plus grandes valeurs asiatiques (Nikkei, Hang Seng, Nifty)
            tickers += ["6758.T", "8035.T", "9984.T", "7203.T", "0992.HK", "0700.HK", "3690.HK", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération des indices pour la région {region}: {e}")
        
    # Nettoyage basique des formats de tickers pour Yahoo Finance
    cleaned_tickers = []
    for t in tickers:
        t_str = str(t).strip().replace('.', '-') if not any(ext in str(t) for ext in ['.AX', '.PA', '.AS', '.DE', '.T', '.L', '.NS', '.HK']) else str(t).strip()
        cleaned_tickers.append(t_str)
        
    return list(set(cleaned_tickers))

def classifier_secteur(info, ticker):
    sector = info.get('sector', '').lower()
    industry = info.get('industry', '').lower()
    long_name = info.get('longName', ticker)
    
    # Cartographie de tes secteurs stratégiques cibles
    if "semiconductor" in industry or "semiconductor" in sector:
        return "🔌 Semi-conducteurs", f"PER: {info.get('trailingPE', 'N/A')} | Marge Brute: {info.get('grossMargins', 0)*100:.1f}%"
    elif "software" in industry and "security" in industry:
        return "🛡️ Cybersécurité", f"ARR/Growth: {info.get('revenueGrowth', 0)*100:.1f}%"
    elif "aerospace" in industry or "defense" in industry:
        return "🦅 Défense & Spatial", f"Marge Op: {info.get('operatingMargins', 0)*100:.1f}%"
    elif "computer" in industry and "infrastructure" in industry:
        return "💻 Data Centers & Cloud", f"CAPEX: {info.get('capitalExpenditure', 'N/A')}"
    elif "biotechnology" in industry:
        return "🧬 Biotechnologies", f"EBITDA: {info.get('ebitda', 'N/A')}"
    elif "medical" in industry or "healthcare" in sector:
        return "🩺 Santé / MedTech", f"ROE: {info.get('returnOnEquity', 0)*100:.1f}%"
    elif "renewable" in industry or "solar" in industry:
        return "🌱 Énergies Renouvelables", f"Dette/Eq: {info.get('debtToEquity', 'N/A')}%"
    elif "uranium" in industry or "nuclear" in industry or ticker in ["CCJ", "URA"]:
        return "⚛️ Nucléaire", f"Marge Op: {info.get('operatingMargins', 0)*100:.1f}%"
    elif "bank" in sector or "financial" in sector:
        return "🏦 Secteur Bancaire", f"P/B: {info.get('priceToBook', 'N/A')} | ROE: {info.get('returnOnEquity', 0)*100:.1f}%"
    elif "luxury" in industry or "apparel" in industry or ticker in ["MC.PA", "RMS.PA"]:
        return "💎 Industrie du Luxe", f"Marge Brute: {info.get('grossMargins', 0)*100:.1f}%"
    else:
        return "📦 Secteur Général / Autre", f"PER: {info.get('trailingPE', 'N/A')}"

def generer_message(ticker, info, prix_actuel, rsi_val, secteur_label, donnees_cles):
    nom = info.get('longName', ticker)[:25]
    devise = info.get('currency', '$')
    pays = info.get('country', 'Inconnu')
    
    tableau = (
        f"🚨 *ALERTE RADAR MONDIAL : {nom.upper()} ({ticker})*\n"
        f"🌍 *Pays :* {pays} | *Secteur :* _{secteur_label}_\n"
        f"🕒 *Analyse automatisée du :* {datetime.datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"```\n"
        f"+--------------------+-------------------------------------+\n"
        f"| PARAMÈTRE CRITIQUE | DONNÉE EN TEMPS RÉEL                |\n"
        f"+--------------------+-------------------------------------+\n"
        f"| Prix Actuel        | {prix_actuel:.2f} {devise}                         |\n"
        f"| Indicateur RSI     | {rsi_val:.1f} (Signal technique bas)       |\n"
        f"| Métriques Secteur  | {donnees_cles[:35]} |\n"
        f"| Zone d'Achat Max   | {prix_actuel * 1.01:.2f} {devise}                         |\n"
        f"| Objectif Probable  | {prix_actuel * 1.12:.2f} {devise}                         |\n"
        f"+--------------------+-------------------------------------+\n"
        f"```\n"
        f"⚠️ *Note macroéconomique :* Profil à analyser au regard du contexte géopolitique et des rapports sectoriels récents."
    )
    return tableau

def envoyer_telegram(texte):
    if not TOKEN_TELEGRAM or not VOTRE_CHAT_ID:
        print("❌ Identifiants Telegram manquants.")
        return
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": VOTRE_CHAT_ID, "text": texte, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Échec de la notification Telegram: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True, choices=["US", "EU", "ASIA", "AU"], help="Région des indices boursiers à scanner")
    args = parser.parse_args()
    
    print(f"🚀 Initialisation du scan pour la région : {args.region}")
    radar = recuperer_tickers(args.region)
    print(f"🎯 Fichier d'analyse chargé avec {len(radar)} actions cibles.")
    
    # Traitement par paquets pour éviter les blocages API
    for i in range(0, len(radar), 30):
        paquet = radar[i:i+30]
        try:
            donnees = yf.download(paquet, period="3mo", group_by='ticker', progress=False)
            for ticker in paquet:
                try:
                    if ticker in donnees.columns.levels[0]:
                        df = donnees[ticker].dropna()
                    else:
                        continue
                    if len(df) < 20: 
                        continue
                    
                    # Calcul rapide du RSI
                    delta = df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
                    
                    prix_actuel = df['Close'].iloc[-1]
                    volume_moyen = df['Volume'].mean()
                    
                    # Filtrage sur niveau de survente modérée (RSI inférieur à 38)
                    if rsi < 38 and volume_moyen > 30000:
                        action_info = yf.Ticker(ticker)
                        secteur, metriques = classifier_secteur(action_info.info, ticker)
                        
                        message = generer_message(ticker, action_info.info, prix_actuel, rsi, secteur, metriques)
                        envoyer_telegram(message)
                        print(f"📢 Alerte transmise avec succès pour {ticker}")
                except Exception as e:
                    continue
        except Exception as e:
            continue
