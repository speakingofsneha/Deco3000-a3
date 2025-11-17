# Reframe

Good case studies are a combination of narrative, information design and personality. But not everyone has the time, patience or skills to do all of that, especially after working on a gruelling project. Introducing Re-frame, an intelligent system that transforms student visual reports into meaningful case studies that reflect real thinking.

## Getting Started
### Prerequisites

- Python 3.8 or higher
- Node.js (for SCSS compilation, or use the built-in SCSS middleware)
- `sass` compiler (install with `npm install -g sass` or use the middleware)
- **Ollama** - A local AI service that powers the text generation (no API keys needed!)

### Installation

1. **Clone or download this repository**

2. **Install Ollama**:
   - Visit [https://ollama.ai/](https://ollama.ai/) and download Ollama for your operating system
   - After installation, open a terminal and run:
     ```bash
     ollama pull llama3
     ```
   - This downloads the AI model that Reframe uses. It's free and runs entirely on your computer.

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

That's it! No API keys or environment variables needed. Everything runs locally on your machine.

### Running the Application

1. **Make sure Ollama is running**:
   - Ollama usually starts automatically when you install it
   - If it's not running, open a terminal and run: `ollama serve`
   - Keep this terminal open while using Reframe

2. **Start the Reframe server**:
   ```bash
   python main.py serve
   ```

   Or with custom host/port:
   ```bash
   python main.py serve --host 0.0.0.0 --port 8000
   ```

3. **Open your browser**:
   Navigate to `http://localhost:8000`

4. **Upload a PDF**:
   - Click the upload area or drag and drop a PDF file
   - Click "Reframe it" to start processing

## How It Works

1. **Upload**: Select a PDF file from your computer
2. **Processing**: The app extracts text, generates an outline, and creates a narrative plan
3. **Review**: Edit the narrative outline to match your vision
4. **Generate**: Create your slide deck with the customized content
5. **Export**: Download individual slides or the entire deck as PNG or SVG

## Project Structure

```
.
├── main.py                 # Entry point for the CLI
├── public/                 # Static files
│   └── index.html          # Main HTML file
├── src/                    # Source code
│   ├── backend/            # Python backend
│   │   ├── api.py          # FastAPI routes and middleware
│   │   ├── processing_service.py  # PDF processing logic
│   │   ├── slide_generator.py     # Slide generation
│   │   └── ...             # Other backend modules
│   ├── components/         # React components
│   │   ├── UploadScreen.jsx
│   │   ├── EditScreen.jsx
│   │   ├── DeckScreen.jsx
│   │   ├── Sidebar.jsx
│   │   └── ...
│   ├── styles/            # SCSS stylesheets
│   │   ├── base.scss
│   │   ├── upload.scss
│   │   └── ...
│   ├── services/           # JavaScript services
│   │   └── historyService.js
│   ├── utils/              # Utility functions
│   │   └── deckUtils.js
│   └── App.jsx             # Main React app
├── uploads/                # Uploaded PDF files
├── outputs/                # Generated slide decks
└── requirements.txt        # Python dependencies
```

## Development

### SCSS Compilation

The application uses SCSS middleware that automatically compiles `.scss` files on-the-fly. No manual compilation needed during development.

If you prefer manual compilation:
```bash
sass src/styles/base.scss:src/styles/base.css
```

### Making Changes

- **Frontend**: Edit React components in `src/components/` or styles in `src/styles/`
- **Backend**: Modify Python files in `src/backend/`
- The server auto-reloads on Python file changes (with `--reload` flag)
- Refresh your browser to see frontend changes (no-cache headers are set for development)

### CLI Commands
The application also supports command-line usage:

```bash
# Process a PDF file directly
python main.py process <pdf_file> [options]

# List slides from a generated JSON file
python main.py list-slides <json_file>

# Get statistics from a slide deck
python main.py stats <json_file>
```

## Technologies Used
- **Frontend**: React (via Babel Standalone), SCSS
- **Backend**: FastAPI, Python
- **AI/ML**: Ollama (Llama 3), Sentence Transformers, FAISS (for embeddings and similarity search)
- **PDF Processing**: PyPDF2
- **Styling**: SCSS with custom design system


