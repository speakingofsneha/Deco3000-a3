# Reframe

Reframe is an AI-powered tool that transforms PDF documents into structured case study decks. Give it a report, paper, or any document in PDF format, and it will automatically create a presentation-ready slide deck with key points, organized sections, and proper citations.

## What It Does

When you have a long PDF document?maybe a research paper, a report, or a case study?Reframe reads through it, understands the content, and creates a slide deck that captures the most important information. It does this by:

1. **Reading your PDF** - Extracts text and identifies the structure
2. **Understanding the content** - Uses AI to understand what the document is about
3. **Creating an outline** - Generates a logical structure for your slides
4. **Finding key points** - Uses retrieval-augmented generation (RAG) to pull out important information from different parts of the document
5. **Building slides** - Organizes everything into a clean, structured slide deck

The result is a JSON file that you can view in your browser using the included slide viewer, or use programmatically in your own applications.

## Requirements

- **Python 3.8 or higher**
- **Ollama** - A free, local AI server that runs on your computer
- **At least 8GB of RAM** (to run the AI model)

## Install on macOS (step-by-step)

Follow these steps if you're on macOS.

### 0) Prerequisites: Homebrew (optional but recommended)

- If you don't have Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- Then follow the on-screen instructions to add Homebrew to your shell.

### 1) Install Python and create a virtual environment

- Check Python:
```bash
python3 --version
```
- If missing/outdated, install via Homebrew:
```bash
brew install python@3
```
- Create and activate a virtual environment in the project root:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2) Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3) Install Ollama

Pick ONE of the options below.

- Using Homebrew (recommended):
```bash
brew install ollama
```

- Or download the macOS app: open `https://ollama.com/download` and install the .dmg, then launch Ollama.

### 4) Start Ollama and download a model

- Start the service (if using CLI install):
```bash
ollama serve
```

- In a new terminal, pull a model (first time only):
```bash
ollama pull llama3
```

### 5) Verify everything works

```bash
python --version
ollama --version
python test_system.py
```

If the test passes, you're ready to process PDFs.

## Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Ollama

Ollama lets you run AI models locally on your computer, completely free and private.

**Install Ollama:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Start Ollama:**
```bash
ollama serve
```

**Download the AI model** (in a new terminal):
```bash
ollama pull llama3
```

This will download the Llama 3 model (about 4GB). The download only happens once.

### 3. Test Everything Works

```bash
python test_system.py
```

This checks that all the components are set up correctly.

### 4. Process Your First PDF

```bash
python main.py process your-document.pdf
```

That's it! Reframe will process your PDF and save a slide deck as `outputs/your-document.json`.

### 5. View Your Slides

Open `ui/deck.html` in your browser (using a local web server if needed). It will automatically load the most recently processed slide deck, or you can specify a file with `?file=outputs/your-document.json`.

## Usage

### Basic Processing

```bash
python main.py process document.pdf
```

### Custom Options

You can adjust how Reframe processes your document:

```bash
python main.py process document.pdf --max-chunks 500 --chunk-size 300 --overlap 25
```

- `--max-chunks`: How many text segments to analyze (default: 1000)
- `--chunk-size`: Size of each text segment (default: 500)
- `--overlap`: How much text overlaps between segments (default: 50)

### View Statistics

See details about a generated slide deck:

```bash
python main.py stats outputs/document.json
```


## How It Works
Reframe processes documents in five main steps:
1. **PDF Parsing** - Extracts all text and basic structure from your PDF
2. **Text Chunking** - Breaks the document into overlapping segments so nothing gets missed
3. **Embedding** - Converts text into numerical vectors that capture meaning (stored using FAISS for fast searching)
4. **Outline Generation** - Uses AI to create a logical structure based on the entire document
5. **Content Generation** - For each section in the outline, searches for relevant information in your document and generates bullet points with citations

The whole process happens locally on your computer so your documents never leave your machine.



## Troubleshooting
**Ollama won't start?** Make sure you've installed it correctly and check that no other application is using port 11434.
**Out of memory errors?** Try reducing `--max-chunks` or `--chunk-size` to process smaller amounts of text at once.
**Slides look incomplete?** Increase the `--max-chunks` parameter to analyze more of the document.


## Project Structure
- `src/` - Core processing modules
  - `pdf_parser.py` - PDF text extraction
  - `chunking_embedding.py` - Text chunking and vector embeddings
  - `outline_generator.py` - AI-powered outline creation
  - `rag_system.py` - Retrieval and content generation
  - `slide_generator.py` - Slide deck creation
  - `processing_service.py` - Main pipeline orchestration
  - `cli.py` - Command-line interface
- `ui/` - Web viewer for slide decks
- `outputs/` - Generated slide decks (JSON files)
- `faiss_index/` - Stored vector embeddings for document search
