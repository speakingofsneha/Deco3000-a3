import requests
import json
import logging
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

class OllamaLLMService:
    """Free LLM service using Ollama with Llama 3"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()
        
        # Check if Ollama is running and model is available
        self._check_ollama_availability()
    
    def _check_ollama_availability(self):
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Ollama is not running. Please start it with: ollama serve")
            
            # Check if model is available
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            if not any(self.model in name for name in model_names):
                logger.warning(f"Model {self.model} not found. Available models: {model_names}")
                logger.info("To install llama3, run: ollama pull llama3")
                raise ValueError(f"Model {self.model} not available. Run: ollama pull llama3")
            
            logger.info(f"✓ Ollama is running with model: {self.model}")
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Cannot connect to Ollama. Please install and start it:\n"
                "1. Install Ollama: https://ollama.ai/\n"
                "2. Start Ollama: ollama serve\n"
                "3. Pull model: ollama pull llama3"
            )
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {str(e)}")
            raise
    
    def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """Generate text using Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120  # 2 minutes timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            result = response.json()
            return result.get("response", "").strip()
            
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. The model might be too slow or overloaded.")
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            raise
    
    def generate_chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """Generate chat completion using Ollama"""
        try:
            # Convert messages to a single prompt
            prompt = self._messages_to_prompt(messages)
            return self.generate_text(prompt, max_tokens, temperature)
            
        except Exception as e:
            logger.error(f"Error generating chat completion: {str(e)}")
            raise
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to a single prompt"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts) + "\n\nAssistant:"
    
    def test_connection(self) -> bool:
        """Test if the LLM service is working"""
        try:
            test_prompt = "Hello! Please respond with just 'OK' to confirm you're working."
            response = self.generate_text(test_prompt, max_tokens=10)
            logger.info(f"✓ LLM test successful. Response: {response}")
            return True
        except Exception as e:
            logger.error(f"✗ LLM test failed: {str(e)}")
            return False

# Global instance
llm_service = None

def get_llm_service() -> OllamaLLMService:
    """Get or create the global LLM service instance"""
    global llm_service
    if llm_service is None:
        llm_service = OllamaLLMService()
    return llm_service