"""Entry point for Python PaaS deployment of ARIA Cloud."""
import os

# The platform may provide PORT while ARIA_PORT is empty.
os.environ["ARIA_PORT"] = (os.getenv("ARIA_PORT") or os.getenv("PORT") or "8000").strip()

import uvicorn
from fastapi.responses import JSONResponse

from cloud.aria_cloud import app, ensure_pair_code


@app.get("/")
def home():
    return JSONResponse({"assistant": "ARIA", "status": "online", "health": "/status"})


@app.on_event("startup")
def initialize_aria():
    ensure_pair_code()


if __name__ == "__main__":
    port = int((os.getenv("PORT") or os.getenv("ARIA_PORT") or "8000").strip())
    uvicorn.run(app, host="0.0.0.0", port=port)
