import threading
import structlog
from pathlib import Path
from typing import Any, Dict, Optional
from llama_cpp import Llama, LlamaGrammar

logger = structlog.get_logger("llm_client")

class LlamaClient:
    def __init__(self, settings: Any):
        self.settings = settings
        self.model_path = str(settings.llm_model_path) if settings.llm_model_path else None
        self._model: Optional[Llama] = None
        self._lock = threading.Lock()

    def _get_model(self) -> Llama:
        with self._lock:
            if self._model is None:
                if not self.model_path or not Path(self.model_path).exists():
                    logger.error("LLM model path not found or not configured", path=self.model_path)
                    raise ValueError(f"LLM model path {self.model_path} does not exist.")

                logger.info("Loading llama.cpp model", 
                            path=self.model_path, 
                            n_ctx=self.settings.llm_n_ctx,
                            gpu_layers=self.settings.llm_n_gpu_layers)
                
                self._model = Llama(
                    model_path=self.model_path,
                    n_ctx=self.settings.llm_n_ctx,
                    n_gpu_layers=self.settings.llm_n_gpu_layers,
                    verbose=False
                )
            return self._model

    def generate_structured(self, prompt: str, grammar_text: str) -> Dict[str, Any]:
        """
        Generates a structured JSON response using GBNF grammar.
        """
        model = self._get_model()
        grammar = LlamaGrammar.from_string(grammar_text)
        
        logger.info("Generating structured LLM response")
        
        response = model(
            prompt,
            max_tokens=self.settings.llm_max_tokens,
            temperature=self.settings.llm_temperature,
            grammar=grammar,
            stop=["</s>", "Llama:", "User:"]
        )
        
        # Llama-cpp-python returns a dict, the 'choices' list contains the result
        import json
        try:
            text_result = response["choices"][0]["text"]
            return json.loads(text_result)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error("Failed to parse structured LLM output", error=str(e), raw_response=response)
            return {"error": "Failed to parse LLM output", "raw": text_result if 'text_result' in locals() else str(response)}
