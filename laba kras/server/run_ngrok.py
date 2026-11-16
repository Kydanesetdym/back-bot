from __future__ import annotations

import os
import uvicorn
from dotenv import load_dotenv
from pyngrok import conf, ngrok

from .config import SERVER_HOST, SERVER_PORT, WEBHOOK_PATH


def main() -> None:
    load_dotenv()
    token = os.getenv("NGROK_AUTHTOKEN", "").strip()
    if token:
        conf.get_default().auth_token = token

    port = int(os.getenv("SERVER_PORT", str(SERVER_PORT)))
    host = os.getenv("SERVER_HOST", SERVER_HOST)

    tunnel = ngrok.connect(port, "http")
    public_url = tunnel.public_url.rstrip("/")
    if public_url.startswith("http://"):
        public_url = "https://" + public_url[len("http://"):]
    os.environ["BASE_URL"] = public_url
    print(f"ngrok tunnel: {public_url}")
    print(f"Webhook URL will be: {public_url}{os.getenv('WEBHOOK_PATH', WEBHOOK_PATH)}")

    # reload config-dependent module state
    import server.config as config
    config.BASE_URL = public_url

    uvicorn.run("server.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
