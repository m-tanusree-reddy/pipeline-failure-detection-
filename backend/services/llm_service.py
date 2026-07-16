"""
LLM Service module for automated CI/CD pipeline failure investigation.
Interacts with the Gemini API to analyze failures using retrieved evidence.
"""

import logging
import os
import sys
from typing import List, Optional
from pydantic import BaseModel, Field

# Add project root to sys.path at startup to enable consistent imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from google import genai
from google.genai import types
from google.genai.errors import APIError

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.retrieval.retriever import RetrievedDocument

logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    """
    Pydantic model representing the structured result of the root cause analysis.
    """
    root_cause: str = Field(
        ..., 
        description="A concise summary of the determined root cause of the failure."
    )
    confidence: int = Field(
        ..., 
        description="Confidence score from 0 to 100 based on the supporting evidence.",
        ge=0,
        le=100
    )
    explanation: str = Field(
        ..., 
        description="Detailed explanation of how the evidence supports the root cause."
    )
    suggested_fixes: List[str] = Field(
        ..., 
        description="List of actionable, suggested fixes to resolve the pipeline failure."
    )
    supporting_documents: List[int] = Field(
        ..., 
        description="1-based indices of the retrieved documents that support the analysis."
    )


class LLMService:
    """
    Interacts directly with the Gemini API to analyze pipeline failures.
    Does not know about FAISS, Retrieval, GitHub, Planner, or Chunker.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initializes the LLMService.

        Args:
            api_key: Optional Gemini API Key override.
            model: Optional Gemini Model name override.
        """
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL

        if not self.api_key:
            logger.warning(
                "GEMINI_API_KEY is not set. API calls will fail unless "
                "provided via alternative environmental credentials."
            )

        try:
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = genai.Client()
        except Exception as e:
            logger.error(f"Failed to initialize GenAI client: {e}")
            self.client = None

    def analyze_failure(
        self, 
        pipeline_error: str, 
        retrieved_documents: List[RetrievedDocument]
    ) -> AnalysisResult:
        """
        Analyzes the given pipeline error using the retrieved documents as context.

        Args:
            pipeline_error: The raw pipeline traceback or error message.
            retrieved_documents: Chunks from retrieval store to serve as evidence.

        Returns:
            An AnalysisResult object containing root cause, confidence, 
            explanations, suggested fixes, and supporting documents list.
        """
        # Construct the prompt based on the specified structure
        prompt_lines = [
            "You are an expert DevOps engineer.",
            "Analyze the following CI/CD failure.",
            "",
            "Pipeline Error",
            "<error>",
            pipeline_error,
            "</error>",
            "",
            "Relevant Evidence"
        ]

        for i, doc in enumerate(retrieved_documents, 1):
            prompt_lines.extend([
                f"Document {i}",
                f"Source: {doc.chunk.source if hasattr(doc, 'chunk') else 'Unknown'}",
                f"Content:\n{doc.chunk.content if hasattr(doc, 'chunk') else ''}",
                "-------------------"
            ])

        prompt_lines.extend([
            "Based ONLY on the supplied evidence",
            "Determine",
            "1 Root Cause",
            "2 Confidence (0-100)",
            "3 Explanation",
            "4 Suggested Fixes",
            "5 Which retrieved documents support your answer",
            "Return STRICT JSON."
        ])

        prompt = "\n".join(prompt_lines)

        if not self.client:
            logger.error("LLMService client is not initialized.")
            return self._create_fallback_result("GenAI client not initialized.")

        try:
            logger.info(f"Invoking Gemini model '{self.model}' for structured failure analysis...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AnalysisResult,
                    temperature=0.1,
                )
            )

            if not response.text:
                logger.error("Received empty response from Gemini API.")
                return self._create_fallback_result("Empty response from Gemini API.")

            logger.info("Structured response successfully retrieved from Gemini.")
            try:
                result = AnalysisResult.model_validate_json(response.text)
                # Bounding confidence scores to 0-100 range in case LLM ignored field validation
                result.confidence = max(0, min(100, result.confidence))
                return result
            except Exception as parse_err:
                logger.error(f"Failed to parse or validate JSON response: {parse_err}. Raw text: {response.text}")
                return self._create_fallback_result(f"Invalid JSON format or model validation failure: {parse_err}")

        except APIError as api_err:
            logger.error(f"Gemini API Error occurred: {api_err}")
            return self._create_fallback_result(f"Gemini API Error: {api_err}")
        except Exception as e:
            logger.error(f"Unexpected error in LLM Service generation: {e}")
            return self._create_fallback_result(f"Unexpected error: {e}")

    def _create_fallback_result(self, error_message: str) -> AnalysisResult:
        """
        Creates a graceful fallback AnalysisResult object when API/generation failures occur.
        """
        return AnalysisResult(
            root_cause="Unknown root cause due to generation error.",
            confidence=0,
            explanation=f"Failed to analyze the pipeline error because of: {error_message}",
            suggested_fixes=[
                "Check the LLM service configuration and API key.",
                "Verify connection and quota for the Gemini API."
            ],
            supporting_documents=[]
        )


if __name__ == "__main__":
    # Test suite with mocked retrieval output
    from backend.retrieval.chunker import Chunk

    # Create logger console handler for test execution
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("\n--- Running LLMService Mock Test ---")

    # Construct mock retrieved document 1
    mock_chunk_1 = Chunk(
        chunk_id="chunk-f3a1-4a4b",
        document_id="doc-101",
        source="requirements.txt",
        title="Python Project Requirements",
        content="requests==2.31.0\nurllib3==2.0.7\n# PyYAML is commented out\n# pyyaml==6.0.1",
        url="https://github.com/org/repo/blob/main/requirements.txt",
        metadata={},
        chunk_index=1,
        total_chunks=1
    )
    doc_1 = RetrievedDocument(chunk=mock_chunk_1, score=0.12, rank=1)

    # Construct mock retrieved document 2
    mock_chunk_2 = Chunk(
        chunk_id="chunk-c4b2-9d3f",
        document_id="doc-102",
        source="config_loader.py",
        title="Configuration Parser Module",
        content="import yaml\n\ndef load_config(path):\n    with open(path, 'r') as f:\n        return yaml.safe_load(f)",
        url="https://github.com/org/repo/blob/main/config_loader.py",
        metadata={},
        chunk_index=1,
        total_chunks=1
    )
    doc_2 = RetrievedDocument(chunk=mock_chunk_2, score=0.25, rank=2)

    # Mock error trace
    mock_error = (
        "Traceback (most recent call last):\n"
        "  File \"main.py\", line 4, in <module>\n"
        "    from config_loader import load_config\n"
        "  File \"config_loader.py\", line 1, in <module>\n"
        "    import yaml\n"
        "ModuleNotFoundError: No module named 'yaml'"
    )

    # Instantiate service
    service = LLMService()
    
    # Run analysis
    analysis_result = service.analyze_failure(
        pipeline_error=mock_error,
        retrieved_documents=[doc_1, doc_2]
    )

    print("\n[Mock Analysis Result Output]")
    print(analysis_result.model_dump_json(indent=2))
