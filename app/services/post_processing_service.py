import structlog
from pathlib import Path
from typing import Any, Dict
from app.core.llm_client import LlamaClient
from app.core.prompts import get_dispatch_summary_prompt

logger = structlog.get_logger("post_processing")

class PostProcessingService:
    def __init__(self, settings: Any, llm_client: LlamaClient):
        self.settings = settings
        self.llm_client = llm_client
        self.grammar_path = Path(__file__).parent.parent / "core" / "grammar.gbnf"

    async def process_transcript(self, transcript_text: str) -> Dict[str, Any]:
        """
        Analyzes a transcript and returns structured data.
        """
        import asyncio
        loop = asyncio.get_event_loop()

        if not transcript_text or len(transcript_text.strip()) < 5:
            logger.info("Transcript too short for processing", length=len(transcript_text))
            return {"status": "skipped", "reason": "text_too_short"}

        logger.info("Processing transcript for structured data")
        
        try:
            prompt = get_dispatch_summary_prompt(transcript_text)
            
            # Read grammar
            if not self.grammar_path.exists():
                logger.error("Grammar file not found", path=str(self.grammar_path))
                return {"error": "Grammar file missing"}
                
            grammar_text = self.grammar_path.read_text()
            
            # LLM generation is CPU-bound, run in executor
            result = await loop.run_in_executor(
                None, 
                self.llm_client.generate_structured, 
                prompt, 
                grammar_text
            )
            
            logger.info("Transcript processed successfully")
            return result
            
        except Exception as e:
            logger.error("Post-processing failed", error=str(e), exc_info=True)
            return {"error": str(e)}
