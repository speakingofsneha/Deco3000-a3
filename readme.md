# Reframe

Reframe is a web application that converts student visual reports into into engaging case studies. Upload a PDF, review and edit the generated outline, and export your slides as PNG or SVG.

## Getting Started
### Prerequisites

- Python 3.8 or higher
- Node.js (for SCSS compilation, or use the built-in SCSS middleware)
- `sass` compiler (install with `npm install -g sass` or use the middleware)

### Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (if needed):
   Create a `.env` file in the root directory with your API keys if the application requires them.

### Running the Application

1. **Start the server**:
   ```bash
   python main.py serve
   ```

   Or with custom host/port:
   ```bash
   python main.py serve --host 0.0.0.0 --port 8000
   ```

2. **Open your browser**:
   Navigate to `http://localhost:8000`

3. **Upload a PDF**:
   - Click the upload area or drag and drop a PDF file
   - Click "Reframe it" to start processing

## How It Works

1. **Upload**: Select a PDF file from your computer
2. **Processing**: The app extracts text, generates an outline, and creates a narrative plan
3. **Review**: Edit the narrative and adjust the tone if needed
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
- **AI/ML**: Sentence Transformers, FAISS (for embeddings and similarity search)
- **PDF Processing**: PyPDF2
- **Styling**: SCSS with custom design system


