"""Entry point for Python PaaS deployment of ARIA Cloud."""
import os

import uvicorn

from cloud.aria_cloud import app, ensure_pair_code


if __name__ == "__main__":
    ensure_pair_code()
    port = int((os.getenv("PORT") or os.getenv("ARIA_PORT") or "8000").strip())
    uvicorn.run(app, host="0.0.0.0", port=port)
