"""SikandX API server. JSON only, bearer-token auth, serves the web app at /."""
import hmac, os, secrets, time
from flask import Flask, jsonify, request, send_from_directory

from core.config import Settings, Store, DATA_DIR, ROOT
from core.engine import Engine
from core.data import make_sample_m1, load_csv
from core.backtest import run_backtest

WEB = os.path.join(ROOT, "web")


def load_token() -> str:
    t = os.environ.get("SIKANDX_TOKEN", "").strip()
    if t:
        return t
    os.makedirs(DATA_DIR, exist_ok=True)
    p = os.path.join(DATA_DIR, "token.txt")
    if os.path.exists(p):
        return open(p).read().strip()
    t = secrets.token_urlsafe(32)
    with open(p, "w") as f:
        f.write(t)
    return t


def create_app(engine=None, token=None, start_engine=True):
    app = Flask(__name__, static_folder=None)
    app.config["TOKEN"] = token or load_token()
    eng = engine or Engine(Settings(), Store())
    app.config["ENGINE"] = eng
    if start_engine:
        eng.start()
    origins = {o.strip() for o in os.environ.get(
        "SIKANDX_ORIGINS", "https://localhost,http://localhost,capacitor://localhost").split(",")}

    @app.after_request
    def cors(r):
        o = request.headers.get("Origin")
        if o and o in origins:
            r.headers["Access-Control-Allow-Origin"] = o
            r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            r.headers["Vary"] = "Origin"
        r.headers["Cache-Control"] = "no-store" if request.path.startswith("/api/") else r.headers.get("Cache-Control", "no-cache")
        return r

    @app.before_request
    def auth():
        if not request.path.startswith("/api/") or request.method == "OPTIONS" or request.path == "/api/ping":
            return
        tok = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(tok.encode(), app.config["TOKEN"].encode()):
            time.sleep(0.4)
            return jsonify(ok=False, error="Wrong or missing access token."), 401

    def body():
        return request.get_json(silent=True) or {}

    @app.get("/api/ping")
    def ping():
        return jsonify(ok=True, app="SikandX")

    @app.get("/api/state")
    def state():
        return jsonify(ok=True, **eng.state())

    @app.get("/api/chart")
    def chart():
        return jsonify(ok=True, **eng.chart_data())

    @app.post("/api/command")
    def command():
        return jsonify(ok=True, reply=eng.command(str(body().get("text", ""))))

    @app.post("/api/scan")
    def scan():
        try:
            return jsonify(ok=True, reply=eng.scan())
        except Exception as e:
            return jsonify(ok=False, error=str(e)), 500

    @app.post("/api/settings")
    def settings():
        return jsonify(ok=True, changed=eng.set_settings(body()))

    @app.post("/api/auto")
    def auto():
        return jsonify(ok=True, reply=eng.set_auto(bool(body().get("on"))))

    @app.post("/api/pause")
    def pause():
        return jsonify(ok=True, reply=eng.pause())

    @app.post("/api/resume")
    def resume():
        t = body().get("target")
        return jsonify(ok=True, reply=eng.resume(float(t) if t else None))

    @app.post("/api/close-all")
    def close_all():
        return jsonify(ok=True, reply=eng.close_all())

    @app.post("/api/confirm-live")
    def confirm_live():
        return jsonify(ok=True, reply=eng.confirm_live(body().get("text", "")))

    @app.post("/api/revoke-live")
    def revoke_live():
        eng.live_confirmed = False
        return jsonify(ok=True, reply="Live authorization revoked.")

    @app.post("/api/connect")
    def connect():
        b = body()
        ok, msg = eng.connect_mt5(str(b.get("login", "")), str(b.get("password", "")), str(b.get("server", "")))
        return jsonify(ok=ok, reply=msg), (200 if ok else 400)

    @app.post("/api/disconnect")
    def disconnect():
        return jsonify(ok=True, reply=eng.disconnect())

    @app.post("/api/backtest")
    def backtest():
        b = body()
        try:
            bars = max(1000, min(8000, int(b.get("bars", 3000))))
            res = run_backtest(make_sample_m1(bars, seed=int(b.get("seed", 11))), eng.cfg)
            res["data"] = "synthetic"
            return jsonify(ok=True, **res)
        except Exception as e:
            return jsonify(ok=False, error=str(e)), 500

    @app.get("/", defaults={"p": "index.html"})
    @app.get("/<path:p>")
    def web(p):
        if p.startswith("api/"):
            return jsonify(ok=False, error="Not found"), 404
        return send_from_directory(WEB, p)

    return app
