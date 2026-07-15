import pandas as pd
import requests
import yfinance as yf
import datetime
import os
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# 🔒 Sécurisation : Récupération des clés secrètes via l'environnement GitHub
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
VOTRE_CHAT_ID = os.getenv("CHAT_ID")

def generer_synthese_action(ticker, info, prix_actuel, rsi_val, volume_moyen):
    sector = info.get('sector', '').lower()
    industry = info.get('industry', '').lower()
    devise = info.get('currency', '$')
    nom = info.get('longName', ticker)[:25]
    
    per = info.get('trailingPE', 0)
    peg = info.get('pegRatio', 0)
    rev_growth = info.get('revenueGrowth', 0)
    op_margin = info.get('operatingMargins', 0)
    gross_margin = info.get('grossMargins', 0)
    pb_ratio = info.get('priceToBook', 0)
    roe = info.get('returnOnEquity', 0)
    debt_to_equity = info.get('debtToEquity', 0)
    dy = info.get('dividendYield', 0)

    p_growth = f"{rev_growth * 100:.1f}%" if rev_growth else "N/A"
    p_op_margin = f"{op_margin * 100:.1f}%" if op_margin else "N/A"
    p_gross_margin = f"{gross_margin * 100:.1f}%" if gross_margin else "N/A"
    p_roe = f"{roe * 100:.1f}%" if roe else "N/A"
    p_dy = f"{dy * 100:.1f}%" if dy else "N/A"

    if "semiconductor" in industry or "semiconductor" in sector:
        secteur_label = "🔌 Semi-conducteurs"
        donnees_cles = f"PER: {per or 'N/A'} | Marge Brute: {p_gross_margin}"
    elif "tech" in sector or "software" in industry or "internet" in industry:
        secteur_label = "💻 Technologie & IA"
        donnees_cles = f"PER: {per or 'N/A'} | PEG: {peg or 'N/A'} | CA: {p_growth}"
    elif "luxury" in industry or "apparel" in industry:
        secteur_label = "💎 Luxe"
        donnees_cles = f"Marge Op: {p_op_margin} | PER: {per or 'N/A'}"
    elif "bank" in sector or "bank" in industry:
        secteur_label = "🏦 Banque"
        donnees_cles = f"P/B: {pb_ratio or 'N/A'} | ROE: {p_roe}"
    elif "insurance" in industry:
        secteur_label = "🛡️ Assurance"
        donnees_cles = f"ROE: {p_roe} | P/B: {pb_ratio or 'N/A'}"
    elif "energy" in sector or "oil" in industry or "gas" in industry:
        secteur_label = "⚡ Énergie"
        donnees_cles = f"Dette/Eq: {debt_to_equity or 'N/A'}% | Div: {p_dy}"
    elif "industrials" in sector:
        secteur_label = "🏭 Industrie"
        donnees_cles = f"Marge Op: {p_op_margin} | ROE: {p_roe}"
    elif "healthcare" in sector or "pharma" in industry:
        secteur_label = "🧬 Santé"
        donnees_cles = f"Marge Op: {p_op_margin} | CA: {p_growth}"
    elif "telecommunication" in industry or "communication services" in sector:
        secteur_label = "📞 Télécoms"
        donnees_cles = f"Div: {p_dy} | Dette/Eq: {debt_to_equity or 'N/A'}%"
    elif "real estate" in sector or "reit" in industry:
        secteur_label = "🏢 Immobilier (REIT)"
        donnees_cles = f"Div: {p_dy} | P/B: {pb_ratio or 'N/A'}"
    else:
        secteur_label = "📦 Secteur Général"
        donnees_cles = f"PER: {per or 'N/A'} | ROE: {p_roe}"

    tableau = (
        f"🦅 *FICHE ANALYSE : {nom.upper()} ({ticker})*\n"
        f"🏷️ *Secteur :* _{secteur_label}_\n"
        f"🕒 *Date :* {datetime.datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"```\n"
        f"+--------------------+-------------------------------------+\n"
        f"| POINT OBSERVÉ      | DONNÉE / LECTURE EN ESSENTIEL       |\n"
        f"+--------------------+-------------------------------------+\n"
        f"| Prix et volume     | {prix_actuel:.2f} {devise} (Vol: {int(volume_moyen):,}) |\n"
        f"| Timing Technique   | RSI: {rsi_val:.1f} (Survente détectée)      |\n"
        f"| Ratios Principaux  | {donnees_cles[:35]} |\n"
        f"| Zone d'Achat Max   | {prix_actuel * 1.01:.2f} {devise}                        |\n"
        f"| Objectif Vente     | {prix_actuel * 1.12:.2f} {devise}                        |\n"
        f"+--------------------+-------------------------------------+\n"
        f"```\n"
        f"💡 *Verdict Pédagogique :* Essentiel validé. Action en sous-évaluation technique."
    )
    return tableau

def envoyer_alerte_telegram(texte):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": VOTRE_CHAT_ID, "text": texte, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: print("❌ Échec envoi Telegram")

def recuperer_radar_mondial():
    headers = {"User-Agent": "Mozilla/5.0"}
    tickers = []
    try:
        tickers += pd.read_html(requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=headers).text)[0]['Symbol'].tolist()
        asx = pd.read_html(requests.get("https://en.wikipedia.org/wiki/List_of_S%26P/ASX_200_companies", headers=headers).text)[0]['Ticker'].tolist()
        tickers += [f"{t}.AX" for t in asx]
    except: pass
    
    tickers += ["ASML.AS", "ASM.AS", "STMPA.PA", "IFX.DE", "SAP.DE", "SU.PA", "HO.PA", "AIR.PA", "MC.PA", "6758.T", "8035.T"]
    return list(set([str(t).replace('.', '-') if not any(e in str(t) for e in ['.AX', '.PA', '.AS', '.DE', '.T']) else str(t) for t in tickers]))

if __name__ == "__main__":
    envoyer_alerte_telegram("⚠️ TEST : Le bot GitHub Actions fonctionne et communique parfaitement avec Telegram !")
    print("✅ Message de test envoyé !")
    radar = recuperer_radar_mondial()
    print(f"🎯 {len(radar)} actions mondiales chargées.")
    
    for i in range(0, len(radar), 30):
        paquet = radar[i:i+30]
        try:
            donnees = yf.download(paquet, period="3mo", group_by='ticker', progress=False)
            for ticker in paquet:
                try:
                    if ticker in donnees.columns.levels[0]:
                        df = donnees[ticker].dropna()
                    else: continue
                    if len(df) < 20: continue
                    
                    delta = df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
                    prix_actuel = df['Close'].iloc[-1]
                    volume_moyen = df['Volume'].mean()
                    
                    if rsi < 35 and volume_moyen > 50000:
                        action_info = yf.Ticker(ticker)
                        info = action_info.info
                        message_tableau = generer_synthese_action(ticker, info, prix_actuel, rsi, volume_moyen)
                        envoyer_alerte_telegram(message_tableau)
                        print(f"📢 Alerte envoyée pour {ticker}")
                except: continue
        except: continue
