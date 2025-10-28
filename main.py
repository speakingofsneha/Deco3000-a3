#!/usr/bin/env python3
"""
PDF to Slide Deck Converter

A CLI and FastAPI application that converts PDF documents into structured slide decks
using AI-powered text processing, chunking, embedding, and RAG (Retrieval-Augmented Generation).

Usage:
    python main.py process <pdf_file> [options]
    python main.py serve [options]
    python main.py list-slides <json_file>
    python main.py stats <json_file>
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli import app

if __name__ == "__main__":
    app()