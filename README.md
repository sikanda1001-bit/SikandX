# SikandX

XAUUSD supply/demand trading bot with an Android app. Black, gold and white.

```
Android app / browser  --HTTPS-->  your Windows PC or VPS (this server + MT5)  -->  broker
```

The phone is only the remote control. The bot runs on the machine that has MetaTrader 5, because the
`MetaTrader5` Python package works on Windows only.

## 1. Run the server (Windows, with MT5 installed and logged in once)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install MetaTrader5
python run.py
```

It prints an **access token**. Keep it secret; the app asks for it. Without MT5 (or on Mac/Linux) it runs
a **paper account on a synthetic price feed**, which is good for trying the app but is not real market data.

Open it on the PC with `http://127.0.0.1:5001` (use the IP, not `localhost`).

Tests: `python tests/test_api.py`

## 2. Reach it from your phone over HTTPS

The server binds to 127.0.0.1 on purpose. Do not expose port 5001 directly. Pick one:

* **Tailscale (simplest, private):** install on PC and phone, then on the PC run
  `tailscale serve --bg 5001`. Your address is `https://<pc-name>.<tailnet>.ts.net`.
* **Cloudflare Tunnel:** `cloudflared tunnel --url http://127.0.0.1:5001` gives an https address.

## 3. Get the app on your phone

**Fastest:** open the https address in Chrome on Android, enter the token, then menu > *Add to Home screen*.

**APK (needs Node.js and Android Studio):**

```
cd mobile
npm install
npm run setup        # bundles ../web and creates the android project
npm run open         # opens Android Studio: Build > Build APK(s)
```

Re-run `npm run sync` after changing anything in `web/`. In the APK, enter your https address and token on the first screen.
If the page cannot reach the server, add the app origin to `SIKANDX_ORIGINS` (default already allows `https://localhost`).

## How trading decisions are made

* M15 sets the bias, M5 finds the setup, M1 confirms or vetoes. Closed candles only.
* Score = scored supply/demand zone + reversal candle + break of structure + trendline + trend + supply/demand meter.
* **Auto entries require all of:** score >= your minimum, price inside a scored zone, and a break of structure or trendline.
  Nothing overrides this. Chat orders (`buy`, `sell`) are your explicit override of direction only; sizing and limits still apply.
* Stops sit beyond the zone; targets at the next opposing zone, stretched to at least 1.5R. Setups with a stop wider than 4 ATR are rejected.

## Protection (checked every scan, auto on or off)

* **Equity target:** closes everything, halts, and stays halted until you say `resume` (optionally `resume target 500`).
  If closing fails it is retried each scan and an alert appears in chat.
* **Daily loss limit** (default 5%): same halt.
* **Restart-safe:** target, limits, pause and halt are saved to `data/state.json`.
* **Live accounts:** demo vs live is read from the MT5 terminal, not from a form. Real orders need `CONFIRM LIVE`, re-required after
  every server restart or broker change. Closing positions is never blocked.
* **No fake data on a real account:** if MT5 candles fail, the scan is skipped. The bot never trades on synthetic prices.
* **Honest sizing:** if the broker's smallest lot would risk more than 2x your intended risk, the trade is skipped (relevant on small accounts).
* Credentials live in server memory only. Disconnecting or restarting drops them. The access token is stored in `data/token.txt` (or set `SIKANDX_TOKEN`).

## Chat commands

`buy`, `sell`, `buy 0.05`, `close all`, `pause`, `resume`, `resume target 500`, `set target 500`, `max positions 3`,
`min score 55`, `risk 0.5`, `auto on`, `auto off`, `scan`, `status`, `confirm live`, `revoke live`, `help`.

## Not included / honest limits

* **MT4** has no Python API; this version supports MT5 and paper only.
* The built-in backtest runs on synthetic prices to prove the machinery. Run `python -m core.backtest --csv XAUUSD_M1.csv`
  with real broker history (columns: time, open, high, low, close) before judging the strategy. Even then, a backtest is not a guarantee.
* No spread/market-hours filter yet. Gold gaps at the weekly open and around news.
* Run on a **demo account for weeks** before going live. Leveraged gold trading can lose money quickly. This is not financial advice.
