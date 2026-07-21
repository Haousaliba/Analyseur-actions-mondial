import pandas as pd
import requests
import yfinance as yf
import datetime
import os
import argparse

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
VOTRE_CHAT_ID = os.getenv("CHAT_ID")

def extraire_wiki(url, possible_cols):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    tickers = []
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(resp.text)
        for df in tables:
            for col in df.columns:
                if any(c.lower() in str(col).lower() for c in possible_cols):
                    found = df[col].dropna().astype(str).tolist()
                    if len(found) > 10:
                        tickers.extend(found)
                        break
    except Exception as e:
        print(f"⚠️ Scan Wiki indisponible pour {url}: {e}")
    return tickers

def recuperer_tickers(region):
    tickers = []
    
    if region in ["US", "ALL"]:
        t_sp = extraire_wiki("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", ["Symbol", "Ticker"])
        t_dj = extraire_wiki("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average", ["Symbol", "Ticker"])
        t_nasdaq = extraire_wiki("https://en.wikipedia.org/wiki/Nasdaq-100", ["Ticker", "Symbol"])
        tickers += t_sp + t_dj + t_nasdaq
        if not tickers: # Liste de secours US
            tickers += ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AMD", "PLTR", "AVGO", "LMT", "PANW", "EQIX"]

    if region in ["EU", "ALL"]:
        t_cac = [f"{t}.PA" for t in extraire_wiki("https://en.wikipedia.org/wiki/CAC_40", ["Ticker", "Symbol"])]
        t_dax = [f"{t}.DE" for t in extraire_wiki("https://en.wikipedia.org/wiki/DAX", ["Ticker", "Symbol"])]
        t_ftse = [f"{t}.L" for t in extraire_wiki("https://en.wikipedia.org/wiki/FTSE_100_Index", ["Ticker", "Header"])]
        t_stoxx = [f"{t}" for t in extraire_wiki("https://en.wikipedia.org/wiki/Euro_Stoxx_50", ["Ticker", "Symbol"])]
        tickers += t_cac + t_dax + t_ftse + t_stoxx
        if len(t_cac) == 0: # Liste de secours EU
            tickers += ["MC.PA", "OR.PA", "RMS.PA", "TTE.PA", "SU.PA", "AIR.PA", "HO.PA", "VIE.PA", "SAP.DE", "RHM.DE", "ASML.AS", "ADYEN.AS"]

    if region in ["AU", "ALL"]:
        t_asx = [f"{t}.AX" for t in extraire_wiki("https://en.wikipedia.org/wiki/List_of_S%26P/ASX_200_companies", ["Ticker", "Code"])]
        tickers += t_asx
        if not t_asx:
            tickers += ["BHP.AX", "CBA.AX", "CSL.AX", "WDS.AX", "RIO.AX"]

    if region in ["ASIA", "ALL"]:
        # Nikkei, Hang Seng, Sensex & Nifty composants majeurs
        tickers += [
            "6758.T", "8035.T", "9984.T", "7203.T", "6857.T", # Japon
            "0992.HK", "0700.HK", "3690.HK", "9988.HK", "1810.HK", # Hong Kong
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", # Inde
            "2330.TW" # TSMC
        ]

    # Nettoyage des formats de tickers pour Yahoo Finance
    cleaned = []
    for t in set(tickers):
        t_clean = str(t).strip().replace('.', '-') if not any(ext in str(t) for ext in ['.AX', '.PA', '.AS', '.DE', '.T', '.L', '.NS', '.HK', '.TW']) else str(t).strip()
        cleaned.append(t_clean)
        
    return list(set(cleaned))

def classifier_secteur(info, ticker):
    sector = info.get('sector', '').lower()
    industry = info.get('industry', '').lower()
    
    # 22 Secteurs Stratégiques
    if "semiconductor" in industry or "semiconductor" in sector:
        return "🔌 Semi-conducteurs", f"PER: {info.get('trailingPE', 'N/A')} | Marge Brute: {info.get('grossMargins', 0)*100:.1f}%"
    elif "cybersecurity" in industry or ("software" in industry and "security" in industry):
        return "🛡️ Cybersécurité", f"CA Growth: {info.get('revenueGrowth', 0)*100:.1f}% | Marge Brute: {info.get('grossMargins', 0)*100:.1f}%"
    elif "aerospace" in industry or "defense" in industry:
        return "🦅 Défense & Spatial", f"Marge Op: {info.get('operatingMargins', 0)*100:.1f}% | ROIC: {info.get('returnOnAssets', 0)*100:.1f}%"
    elif "data center" in industry or ("computer" in industry and "infrastructure" in industry):
        return "💻 Data Centers & Cloud", f"Dette/Eq: {info.get('debtToEquity', 'N/A')}% | FCF: {info.get('freeCashflow', 'N/A')}"
    elif "robotics" in industry or "automation" in industry:
        return "🤖 Robotique & Automatisation", f"Marge Op: {info.get('operatingMargins', 0)*100:.1f}% | R&D: Métrique Clé"
    elif "biotechnology" in industry:
        return "🧬 Biotechnologies", f"Cash: {info.get('totalCash', 'N/A')} | EBITDA: {info.get('ebitda', 'N/A')}"
    elif "medical" in industry or "healthcare" in sector:
        return "🩺 Santé / MedTech", f"ROE: {info.get('returnOnEquity', 0)*100:.1f}% | Marge Brute: {info.get('grossMargins', 0)*100:.1f}%"
    elif "renewable" in industry or "solar" in industry:
        return "🌱 Énergies Renouvelables", f"Dette/Eq: {info.get('debtToEquity', 'N/A')}%"
    elif "uranium" in industry or "nuclear" in industry or ticker in ["CCJ", "URA"]:
        return "⚛️ Nucléaire", f"Marge Op: {info.get('operatingMargins', 0)*100:.1f}%"
    elif "utilities" in sector or "water" in industry:
        return "💧 Eau & Réseaux Électriques", f"Dette/EBITDA: N/A | ROIC: {info.get('returnOnAssets', 0)*100:.1f}%"
    elif "mining" in industry or "copper" in industry or "metals" in industry:
        return "⛏️ Mines Stratégiques", f"FCF Yield: N/A | Marge Op: {info.get('operatingMargins', 0)*100:.1f}%"
    elif "software" in sector or "software" in industry:
        return "💻 Logiciels SaaS", f"Marge Brute: {info.get('grossMargins', 0)*100:.1f}% | EV/Sales: {info.get('enterprisetoRevenue', 'N/A')}"
    elif "bank" in sector or "bank" in industry:
        return "🏦 Banques & Fintech", f"P/B: {info.get('priceToBook', 'N/A')} | ROE: {info.get('returnOnEquity', 0)*100:.1f}%"
    elif "insurance" in industry:
        return "🛡️ Assurance", f"P/B: {info.get('priceToBook', 'N/A')} | ROE: {info.get('returnOnEquity', 0)*100:.1f}%"
    elif "luxury" in industry or "apparel" in industry or ticker in ["MC.PA", "RMS.PA", "KER.PA"]:
        return "💎 Luxe", f"Marge Op: {info.get('operatingMargins', 0)*100:.1f}% | ROIC: {info.get('returnOnAssets', 0)*100:.1f}%"
    elif "auto" in industry:
        return "🚗 Automobile & Batteries", f"Marge Brute: {info.get('grossMargins', 0)*100:.1f}%"
    elif "telecom" in sector or "communication" in sector:
        return "📞 Télécoms", f"Div Yield: {info.get('dividendYield', 0)*100:.1f}%"
    elif "real estate" in sector:
        return "🏢 Immobilier (REIT)", f"P/B: {info.get('priceToBook', 'N/A')}"
    else:
        return "📦 Industrie / Secteur Général", f"PER: {info.get('trailingPE', 'N/A')} | ROE: {info.get('returnOnEquity', 0)*100:.1f}%"

def envoyer_telegram(texte):
    if not TOKEN_TELEGRAM or not VOTRE_CHAT_ID:
        print("❌ Identifiants Telegram manquants.")
        return
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": VOTRE_CHAT_ID, "text": texte, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Échec envoi Telegram: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="ALL", choices=["US", "EU", "ASIA", "AU", "ALL"])
    args = parser.parse_args()
    
    print(f"🚀 Lancement du scan mondial sur la zone : {args.region}")
    radar = recuperer_tickers(args.region)
    print(f"🎯 Total de {len(radar)} actions prêtes à l'analyse.")
    
    candidats = []
    
    # Traitement par paquets
    for i in range(0, len(radar), 30):
        paquet = radar[i:i+30]
        try:
            donnees = yf.download(paquet, period="3mo", group_by='ticker', progress=False)
            for ticker in paquet:
                try:
                    df = donnees[ticker].dropna() if ticker in donnees.columns.levels[0] else None
                    if df is None or len(df) < 20: 
                        continue
                    
                    delta = df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
                    
                    prix_actuel = df['Close'].iloc[-1]
                    volume_moyen = df['Volume'].mean()
                    
                    # Filtre de pré-sélection (Survente technique + Liquidité suffisante)
                    if rsi < 40 and volume_moyen > 30000:
                        action_info = yf.Ticker(ticker)
                        info = action_info.info
                        secteur, metriques = classifier_secteur(info, ticker)
                        
                        candidats.append({
                            'ticker': ticker,
                            'rsi': rsi,
                            'info': info,
                            'prix': prix_actuel,
                            'volume': volume_moyen,
                            'secteur': secteur,
                            'metriques': metriques
                        })
                except Exception:
                    continue
        except Exception:
            continue

    # TRI ET SÉLECTION DES 5 MEILLEURES OPPORTUNITÉS (Par RSI le plus bas)
    candidats.sort(key=lambda x: x['rsi'])
    top_5 = candidats[:5]

    print(f"🏆 {len(top_5)} opportunités majeures sélectionnées sur {len(candidats)} détectées.")

    if not top_5:
        print("ℹ️ Aucune action ne valide les critères stricts de survente aujourd'hui.")

    for rang, c in enumerate(top_5, 1):
        nom = c['info'].get('longName', c['ticker'])[:25]
        devise = c['info'].get('currency', '$')
        pays = c['info'].get('country', 'International')
        
        message = (
            f"🏆 *TOP {rang}/5 OPPORTUNITÉ DU RADAR*\n"
            f"📌 *{nom.upper()} ({c['ticker']})*\n"
            f"🌍 *Pays :* {pays} | *Secteur :* _{c['secteur']}_\n"
            f"🕒 *Date du scan :* {datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}\n\n"
            f"```\n"
            f"+--------------------+-------------------------------------+\n"
            f"| DONNÉE TECHNIQUE   | VALEUR MESURÉE                      |\n"
            f"+--------------------+-------------------------------------+\n"
            f"| Prix Actuel        | {c['prix']:.2f} {devise}                         |\n"
            f"| Score RSI (14j)    | {c['rsi']:.1f} (Niveau de survente)        |\n"
            f"| Ratios Financiers  | {c['metriques'][:35]} |\n"
            f"| Entrée Optimale    | {c['prix'] * 1.01:.2f} {devise}                         |\n"
            f"| Objectif Vente     | {c['prix'] * 1.12:.2f} {devise}                         |\n"
            f"+--------------------+-------------------------------------+\n"
            f"```\n"
            f"💡 *Verdict :* Sélectionné dans les 5 meilleures configurations globales."
        )
        envoyer_telegram(message)
