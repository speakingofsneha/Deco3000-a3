How do you input pdf and get a slide deck ??

  Based on the codebase, this is a PDF to Slide Deck Converter that uses AI to
  convert PDFs into structured slide presentations. Here are the different ways
  to use it:

Cline
  1. Place your PDF file in the project directory (same folder as main.py)
  2. Process the PDF using the command line:


     python main.py process your_document.pdf

  3. View the generated outline and slides:


     1 │   # List all slides in the generated deck
     2 │   python main.py list-slides your_document_slides.json
     3 │   
     4 │   # Show statistics about the slide deck
     5 │   python main.py stats your_document_slides.json



Where will the output be?
  • Generated slide deck: your_document_slides.json in the project directory
  • Uploaded PDFs: uploads/ directory (when using API)
  • All outputs: outputs/ directory


How to test the system
  **1: run system check**
  python test_system.py

  it checks:
  • All imports and dependencies
  • Ollama connection and Llama 3 model
  • PDF parsing functionality
  • Text chunking and embedding
  • AI outline generation
  • RAG system with bullet generation
  • Slide deck creation
  • Full processing pipeline


  **2: test with example usage**
  python example_usage.py
  This will process a sample PDF (you need to place example.pdf in the directory first).

  **3: test individual components**
  You can also test specific parts of the system by running the individual
  modules.

  🔧 **pre reqs**
  Before you can use the system, you need to set up the AI components:
  1. Install Python dependencies:
     pip install -r requirements.txt

  2. Install and set up Ollama (free local AI):
     1 │   # Install Ollama
     2 │   curl -fsSL https://ollama.ai/install.sh | sh
     3 │   
     4 │   # Start Ollama service
     5 │   ollama serve
     6 │   
     7 │   # Pull Llama 3 model (in a new terminal)
     8 │   ollama pull llama3


  **what is the output tho**
  The system generates a JSON slide deck with:
  • Title slide with document information
  • Content slides with AI-generated bullet points
  • Outline structure based on the PDF content
  • Provenance tracking showing which parts of the PDF each bullet came from
  • Confidence scores for each generated bullet point


  **tldr start**
  1. Test the system:
     python test_system.py

  2. Place your PDF in the project directory
  3. Process it:
     python main.py process your_document.pdf

  4. View the results:
     python main.py list-slides your_document_slides.json

  The system will show you a structured outline of your PDF content converted
  into presentation slides with AI-generated bullet points!
  Would you like me to help you set up any specific part of this system or test
  it with a particular PDF?