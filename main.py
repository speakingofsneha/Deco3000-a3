#!/usr/bin/env python3
"""
reframe

A FastAPI application that converts student visual reoprts into ux case studies
using text processing, chunking, embedding, and RAG (Retrieval-Augmented Generation) etc. 

To start the server:
    python main.py serve
"""

import sys
import os
from pathlib import Path

# add src to python path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent))

# start the fastapi server when this file is run
if __name__ == "__main__":
    import uvicorn
    # run the api app on port 8000 with auto-reload for development
    uvicorn.run("src.backend.api:app", host="0.0.0.0", port=8000, reload=True)