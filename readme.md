# Reframe

Good case studies are a combination of narrative, information design and personality. But not everyone has the time, patience or skills to do all of that, especially after working on a gruelling project. Introducing Reframe, an intelligent system that transforms student visual reports into meaningful case studies that reflect real thinking.

## Overview

Reframe is a web application that:
- Takes your visual report PDF as input
- Generates a narrative outline using AI
- Lets you edit and refine the outline
- Creates a beautiful slide deck with your content
- All running locally on your computer (no cloud services needed!)

## System Requirements

- **Operating System**: macOS, Linux, or Windows
- **Python**: 3.8 or higher
- **RAM**: At least 4GB (8GB recommended for better performance)
- **Storage**: ~2GB free space (for AI models and dependencies)
- **Internet**: Required only for initial installation (downloads models and dependencies)

## Quick Start

### Option 1: Automated Installation (Recommended)

We've created an installation script that handles everything for you:

1. **Make the script executable** (macOS/Linux):
   ```bash
   chmod +x install.sh
   ```

2. **Run the installation script**:
   ```bash
   ./install.sh
   ```

   On Windows, you can use Git Bash or WSL to run the script, or follow the manual installation steps below.

The script will:
- Check if Python 3 is installed
- Install all Python dependencies
- Install Ollama (if not already installed)
- Download the Llama 3 AI model
- Set everything up for you

### Option 2: Manual Installation

If you prefer to install step-by-step or the script doesn't work:

#### Step 1: Install Python

1. **Check if Python is installed**:
   ```bash
   python3 --version
   ```
   You should see something like `Python 3.8.x` or higher.

2. **If Python is not installed**:
   - **macOS**: Install via Homebrew: `brew install python3` or download from [python.org](https://www.python.org/downloads/)
   - **Linux**: Use your package manager: `sudo apt install python3` (Ubuntu/Debian) or `sudo yum install python3` (CentOS/RHEL)
   - **Windows**: Download from [python.org](https://www.python.org/downloads/) and make sure to check "Add Python to PATH" during installation

#### Step 2: Install Ollama

1. **Visit [https://ollama.ai/](https://ollama.ai/)** and download Ollama for your operating system

2. **Install Ollama**:
   - **macOS**: Double-click the downloaded `.dmg` file and follow the installer
   - **Linux**: Run the install script: `curl -fsSL https://ollama.ai/install.sh | sh`
   - **Windows**: Run the downloaded installer

3. **Verify Ollama is installed**:
   ```bash
   ollama --version
   ```

4. **Download the AI model**:
   ```bash
   ollama pull llama3
   ```
   This will take a few minutes depending on your internet connection (the model is about 2GB).

#### Step 3: Set Up Python Environment

1. **Navigate to the project directory**:
   ```bash
   cd /path/to/Deco3000\ a3
   ```

2. **Create a virtual environment** (recommended to keep dependencies isolated):
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**:
   - **macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```
   - **Windows**:
     ```bash
     venv\Scripts\activate
     ```
   
   You should see `(venv)` at the start of your terminal prompt.

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   This will install all required packages. It may take a few minutes.

#### Step 4: Verify Installation

Run the test script to make sure everything is set up correctly:

```bash
python3 test_system.py
```

This will test:
- All imports work correctly
- Ollama connection
- PDF parsing
- Chunking and embedding
- Outline generation
- RAG system
- Slide generation

If all tests pass, you're ready to go!

## Running the Application

### Step 1: Start Ollama

Ollama needs to be running in the background. Open a terminal and run:

```bash
ollama serve
```

Keep this terminal open. You should see output like:
```
2024/01/01 12:00:00 routes.go:1008: INFO server config env="map[OLLAMA_HOST:0.0.0.0:11434]"
```

### Step 2: Start the Reframe Server

Open a **new terminal window** (keep Ollama running in the first one):

1. **Navigate to the project directory**:
   ```bash
   cd /path/to/Deco3000\ a3
   ```

2. **Activate your virtual environment** (if you created one):
   ```bash
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Start the server**:
   ```bash
   python main.py
   ```

   You should see output like:
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   INFO:     Started reloader process
   ```

### Step 3: Open in Browser

Open your web browser and navigate to:

```
http://localhost:8000
```

You should see the Reframe interface!

## Using Reframe

1. **Upload a PDF**:
   - Click the upload area or drag and drop a PDF file
   - Supported formats: `.pdf` files
   - The PDF should be a visual report (like a design portfolio or case study document)

2. **Wait for Processing**:
   - The app will extract text from your PDF
   - Generate an outline structure
   - Create a narrative plan
   - This usually takes 1-3 minutes depending on PDF size

3. **Review and Edit**:
   - Review the generated narrative outline
   - Edit the text to match your vision
   - Make sure it reflects your actual process and thinking

4. **Generate Slide Deck**:
   - Click "Continue" to generate your slide deck
   - The system will create slides with your content
   - Each slide will have appropriate layouts and media placeholders

5. **Export**:
   - Use the export button to download slides as PNG or SVG
   - You can export individual slides or the entire deck

## Troubleshooting

### "Python 3 is not installed"
- Make sure Python 3.8+ is installed: `python3 --version`
- If you see Python 2.x, you need to install Python 3
- On some systems, use `python` instead of `python3`

### "Ollama connection error"
- Make sure Ollama is running: `ollama serve`
- Check if the model is downloaded: `ollama list` (should show `llama3`)
- If the model is missing: `ollama pull llama3`
- Try restarting Ollama

### "Module not found" errors
- Make sure you activated your virtual environment
- Reinstall dependencies: `pip install -r requirements.txt`
- Check that you're in the correct directory

### Server won't start
- Check if port 8000 is already in use
- Try a different port: `uvicorn src.backend.api:app --port 8001`
- Make sure all dependencies are installed

### PDF processing fails
- Make sure the PDF is not corrupted
- Try a different PDF file
- Check that the PDF contains readable text (not just images)
- Ensure the PDF is not password-protected

### Slow performance
- Make sure Ollama is running locally (not over network)
- Close other applications to free up RAM
- The first run is slower as models load into memory

## Project Structure

```
.
├── main.py                 # Server entry point
├── install.sh              # Automated installation script
├── test_system.py          # System test script
├── requirements.txt        # Python dependencies
├── public/                 # Static files
│   └── index.html          # Main HTML file
├── src/                    # Source code
│   ├── backend/            # Python backend
│   │   ├── api.py          # FastAPI routes and middleware
│   │   ├── processing_service.py  # PDF processing logic
│   │   ├── slide_generator.py     # Slide generation
│   │   ├── rag_system.py          # RAG for content generation
│   │   ├── outline_generator.py   # Outline generation
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
├── uploads/                # Uploaded PDF files (created automatically)
├── outputs/                # Generated slide decks (created automatically)
└── vector_stores/          # Vector embeddings cache (created automatically)
```

## Development

### SCSS Compilation

The application uses SCSS middleware that automatically compiles `.scss` files on-the-fly. No manual compilation needed during development.

If you prefer manual compilation:
```bash
./compile-scss.sh
```

Or compile individual files:
```bash
sass src/styles/base.scss:src/styles/base.css
```

### Making Changes

- **Frontend**: Edit React components in `src/components/` or styles in `src/styles/`
- **Backend**: Modify Python files in `src/backend/`
- The server auto-reloads on Python file changes (with `--reload` flag)
- Refresh your browser to see frontend changes (no-cache headers are set for development)

### Testing

Run the test suite to verify everything works:

```bash
python3 test_system.py
```

This will test all components and give you a summary of what's working.

## Technologies Used

- **Frontend**: React (via Babel Standalone), SCSS
- **Backend**: FastAPI, Python
- **AI/ML**: Ollama (Llama 3), Sentence Transformers, FAISS (for embeddings and similarity search)
- **PDF Processing**: PyPDF2, PyMuPDF
- **Styling**: SCSS with custom design system

## Getting Help

If you encounter issues:

1. **Run the test script**: `python3 test_system.py` to identify problems
2. **Check the terminal output** for error messages
3. **Verify Ollama is running**: `ollama serve` should be running in a separate terminal
4. **Check system requirements**: Make sure you have Python 3.8+ and enough RAM


## Credits
 by alyssa & sneha for deco3000
