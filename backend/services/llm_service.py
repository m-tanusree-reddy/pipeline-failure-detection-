import json
import logging
import os
import time
from typing import Type, TypeVar, Any, Dict, List
from pydantic import BaseModel
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, TIMEOUT

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class LLMService:
    """
    A service class to interact with the Google Gemini API with structured JSON output capabilities.
    """
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Real LLM calls will fail.")
            
        # Initialize Google GenAI client
        try:
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = genai.Client()
        except Exception as e:
            logger.error(f"Failed to initialize GenAI client: {e}")
            self.client = None

    def get_structured_completion(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.2
    ) -> T:
        """
        Sends messages to the Gemini API and parses the response into the response_model.
        """
        if not self.client:
            raise ValueError("GenAI client is not initialized due to missing API key configuration.")
            
        # Format messages for Gemini client
        system_instruction = ""
        user_content = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            else:
                user_content.append(content)
                
        # Join user content to form the main prompt
        prompt = "\n\n".join(user_content)
        
        max_retries = 3
        backoff = 1.0
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction if system_instruction else None,
                        response_mime_type="application/json",
                        response_schema=response_model,
                        temperature=temperature
                    )
                )
                
                response_text = response.text
                if not response_text:
                    raise ValueError("Received empty response text from Gemini API.")
                    
                try:
                    return response_model.model_validate_json(response_text)
                except AttributeError:
                    return response_model.parse_raw(response_text)
                    
            except Exception as e:
                logger.warning(f"Gemini API call attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(backoff)
                backoff *= 2
