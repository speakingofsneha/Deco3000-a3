#!/bin/bash

echo "Reframe"
echo "=================================================="

# check if python is installed before we do anything
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# install all the python packages we need
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully"
else
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

# check if ollama is already installed, if not install it
if ! command -v ollama &> /dev/null; then
    echo "📥 Installing Ollama..."
    
    # download and run the ollama install script
    curl -fsSL https://ollama.ai/install.sh | sh
    
    if [ $? -eq 0 ]; then
        echo "✅ Ollama installed successfully"
    else
        echo "❌ Failed to install Ollama"
        echo "Please install manually from: https://ollama.ai/"
        exit 1
    fi
else
    echo "✅ Ollama already installed: $(ollama --version)"
fi

# start ollama in the background so we can download the model
echo "🔄 Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# give ollama a sec to start up before we try to download
sleep 3

# download the llama3 model we need for text generation
echo "📥 Downloading Llama 3 model (this may take a few minutes)..."
ollama pull llama3

if [ $? -eq 0 ]; then
    echo "✅ Llama 3 model downloaded successfully"
else
    echo "❌ Failed to download Llama 3 model"
    kill $OLLAMA_PID 2>/dev/null
    exit 1
fi

# stop the background ollama process since we're done
kill $OLLAMA_PID 2>/dev/null

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Start Ollama: ollama serve"
echo "2. Test the system: python3 test_system.py"
echo "3. Process a PDF: python3 main.py process your_document.pdf"
echo ""
echo "🔧 Troubleshooting:"
echo "- If Ollama fails to start, try: ollama serve"
echo "- If model download fails, try: ollama pull llama3"
echo "- For help, run: python3 test_system.py"