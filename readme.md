# reframe :D

## Installation
1. Clone the repository:
```bash
git clone <repository-url>
cd pdf-to-slides
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install and set up Ollama (free local LLM):
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull Llama 3 model (in a new terminal)
ollama pull llama3
```

4. Test the installation:
```bash
python test_system.py
```

## Quick Start

1. **Test the system**:
```bash
python test_system.py
```

2. **Process a PDF file**:
```bash
python main.py process document.pdf
```

3. **Process with custom parameters**:
```bash
python main.py process document.pdf --max-chunks 500 --chunk-size 300 --overlap 25
```

4. **List slides from generated deck**:
```bash
python main.py list-slides document_slides.json
```

5. **Show statistics**:
```bash
python main.py stats document_slides.json
```

6. **Start the API server**:
```bash
python main.py serve --host 0.0.0.0 --port 8000
```

### API Usage
1. **Start the server**:
```bash
python main.py serve
```

2. **Upload and process a PDF**:
```bash
# Upload PDF
curl -X POST "http://localhost:8000/upload" -F "file=@document.pdf"

# Process PDF
curl -X POST "http://localhost:8000/process" \
  -F "pdf_path=uploads/document.pdf" \
  -F "max_chunks=1000" \
  -F "chunk_size=500" \
  -F "overlap=50"
```

3. **Get slide deck**:
```bash
curl "http://localhost:8000/slides/document"
```

4. **Download JSON**:
```bash
curl "http://localhost:8000/download/document" -o document_slides.json
```

## Architecture
The application follows a modular architecture with the following components:

### Core Modules
- **`pdf_parser.py`**: PDF text extraction and structure analysis
- **`chunking_embedding.py`**: Text chunking and FAISS vector storage
- **`outline_generator.py`**: AI-powered outline generation
- **`rag_system.py`**: Retrieval-Augmented Generation for bullet points
- **`slide_generator.py`**: JSON slide deck creation
- **`processing_service.py`**: Main processing pipeline orchestration

### API Layer
- **`api.py`**: FastAPI application with REST endpoints
- **`cli.py`**: Command-line interface using Typer
- **`models.py`**: Pydantic data models

## Processing Pipeline
1. **PDF Ingestion**: Parse PDF and extract text with basic structure
2. **Chunking**: Split text into overlapping chunks with unique IDs
3. **Embedding**: Generate vector embeddings and store in FAISS index
4. **Outline Generation**: Create comprehensive outline using global pass
5. **RAG Processing**: For each outline item, retrieve relevant chunks and generate bullets
6. **Slide Generation**: Create structured JSON slide deck

### Prerequisites
- **Python 3.8+**: Required for all functionality
- **Ollama**: Free local LLM server (https://ollama.ai/)
- **Llama 3**: Free open-source language model

### CLI Options
- `--max-chunks`: Maximum number of chunks to process (default: 1000)
- `--chunk-size`: Size of each text chunk (default: 500)
- `--overlap`: Overlap between chunks (default: 50)
- `--output`: Output directory for generated files
- `--verbose`: Enable verbose logging

### System Requirements
- **RAM**: At least 8GB recommended (for Llama 3)
- **Storage**: ~4GB for Llama 3 model
- **CPU**: Any modern processor (GPU optional but recommended)

## Output Format
The application generates a JSON slide deck with the following structure:

```json
{
  "title": "Document Title",
  "slides": [
    {
      "id": "slide_1",
      "type": "title",
      "title": "Document Title",
      "content": [
        {
          "text": "Generated from: document.pdf",
          "provenance": [],
          "confidence": 1.0
        }
      ],
      "metadata": {
        "slide_number": 1,
        "is_title": true
      }
    }
  ],
  "metadata": {},
  "created_at": "2024-01-01T00:00:00",
  "source_pdf": "document.pdf"
}
```

## API Endpoints
- `GET /`: Root endpoint with API information
- `GET /health`: Health check
- `POST /upload`: Upload PDF file
- `POST /process`: Process uploaded PDF
- `GET /status/{pdf_name}`: Get processing status
- `GET /download/{pdf_name}`: Download slide deck JSON
- `GET /slides/{pdf_name}`: Get slide deck data
- `GET /slides/{pdf_name}/stats`: Get slide deck statistics

## Dependencies
- **FastAPI**: Web framework for API
- **PyMuPDF**: PDF parsing
- **sentence-transformers**: Text embeddings
- **faiss-cpu**: Vector similarity search
- **Ollama**: Free local LLM server
- **Llama 3**: Free open-source language model
- **Typer**: CLI framework
- **Rich**: Terminal formatting
- **Pydantic**: Data validation

