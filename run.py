"""Start SikandX:  python run.py   (binds to 127.0.0.1; put HTTPS in front, see README)"""
import argparse, os
from waitress import serve
from server import create_app

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("SIKANDX_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("SIKANDX_PORT", "5001")))
    a = ap.parse_args()
    app = create_app()
    print("=" * 60)
    print(f"SikandX running on http://{a.host}:{a.port}")
    print(f"Access token: {app.config['TOKEN']}")
    print("Enter this token in the app. Keep it secret.")
    print("=" * 60)
    serve(app, host=a.host, port=a.port, threads=4)   # single process: engine state lives in memory
