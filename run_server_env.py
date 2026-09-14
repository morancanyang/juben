"""Start uvicorn with values from the project .env taking precedence."""
import os
from pathlib import Path

for line in (Path(__file__).parent / ".env").read_text(encoding="utf-8-sig").splitlines():
    line=line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key,value=line.split("=",1)
    os.environ[key.strip()]=value.strip().strip('"').strip("'")

import uvicorn
uvicorn.run("api.main:app", host="127.0.0.1", port=8765)
