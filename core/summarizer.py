import logging
import json
from llama_cpp import Llama, LlamaGrammar
from core.config import Config
from core.model_manager import model_manager

logger = logging.getLogger("EchoSummarizer[GGUF]")

class Summarizer:
    def __init__(self):
        self.llm = None
        self._grammar = None

    def _get_grammar(self):
        """
        Constructs the GBNF grammar for strict JSON output.
        Target Schema: { "summary": string, "action_items": [ { "task": string, "owner": string } ] }
        """
        if self._grammar is None:
            # Simplified GBNF for JSON
            gbnf = r"""
            root ::= "{" space "\"summary\"" space ":" space string "," space "\"action_items\"" space ":" space items "}"
            items ::= "[" space (item ("," space item)*)? "]"
            item ::= "{" space "\"task\"" space ":" space string "," space "\"owner\"" space ":" space string "}"
            string ::= "\"" ( [^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4}) )* "\""
            space ::= [ \t\n]*
            """
            self._grammar = LlamaGrammar.from_string(gbnf)
        return self._grammar

    def load_model(self):
        """Loads Qwen GGUF model."""
        if self.llm is None:
            model_path = model_manager.get_slm_model_path()
            logger.info(f"Loading SLM: {model_path}")
            # Context size 2048 matches 0.5B limits generally
            self.llm = Llama(model_path=model_path, n_ctx=2048, n_threads=4, verbose=False)
            logger.info("SLM loaded.")

    def unload_model(self):
        """Unloads Qwen to free RAM."""
        if self.llm:
            del self.llm
            self.llm = None
            logger.info("SLM unloaded.")

    def summarize(self, new_text, existing_summary=""):
        """
        Generates summary and action items using Rolling Context.
        Configurable prompt tailored for meeting minutes.
        """
        self.load_model()
        
        # Prompt Engineering for Qwen
        prompt = f"""<|im_start|>system
You are Echo, a meeting assistant. Analyze the TRANSCRIPT segment below.
1. Update the 'summary' to include new key details.
2. Extract 'action_items' (tasks) assigned to people.
OUTPUT JSON ONLY.
<|im_start|>user
PREVIOUS SUMMARY: {existing_summary}
TRANSCRIPT SEGMENT: {new_text}
<|im_start|>assistant
"""
        
        try:
            logger.info("Running inference (Summarization)...")
            output = self.llm(
                prompt,
                max_tokens=512,
                temperature=0.2,
                grammar=self._get_grammar(), # GBNF Enforcement
                stop=["<|im_end|>"]
            )
            
            text_result = output['choices'][0]['text']
            
            # Simple cleanup: sometimes models add extra whitespace or partial json
            text_result = text_result.strip()
            
            try:
                parsed_json = json.loads(text_result)
            except json.JSONDecodeError:
                logger.error(f"JSON Decode Failed. Raw output: {text_result}")
                # Fallback: wrap raw text in a partial structure
                parsed_json = {"summary": text_result, "action_items": []}
            
            self.unload_model()
            return parsed_json
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            self.unload_model()
            raise

summarizer = Summarizer()
