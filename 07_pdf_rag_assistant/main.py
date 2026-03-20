"""
Application entrypoint.
This file is a thin wrapper — all logic lives inside app/.
Run with: uvicorn main:app --reload
"""

import uvicorn
from app.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)