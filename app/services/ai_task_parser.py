# app/services/ai_task_parser.py

import logging
import os
from typing import Optional, Any
from google import genai
from google.genai import types

from app.services.ai_task_parser_schema import EXTRACT_TASK_FUNCTION

logger = logging.getLogger(__name__)

# Initialize Gemini client with API key from environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")

# Timeout for the Gemini API call, in milliseconds. Prevents a hung/slow
# request from leaving an AITaskRequest stuck in "processing" forever.
GEMINI_TIMEOUT_MS = 15000

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


class GeminiLLMError(Exception):
    """Raised when the call to Gemini itself fails (network, auth, quota, timeout, etc.)."""
    pass


class GeminiParseError(Exception):
    """Raised when Gemini responds but no usable function_call is returned."""
    pass


def parse_task_from_text(
    raw_input: str, 
    current_date: Optional[Any] = None, 
    timezone_name: Optional[str] = None
) -> tuple[Any, dict[str, Any]]:
    """
    Calls Gemini with a forced function call to extract structured task fields.

    Args:
        raw_input: Natural language task description
        current_date: Current date for context (optional)
        timezone_name: Timezone for relative date interpretation (optional)

    Returns:
        tuple: (raw_llm_response, parsed_payload)
            - raw_llm_response: the full Gemini response object (for audit logging)
            - parsed_payload: dict of extracted fields

    Raises:
        GeminiLLMError: the API call itself failed (including timing out)
        GeminiParseError: the call succeeded but no function_call was returned
    """
    if not client:
        logger.error("Gemini client not initialized - GEMINI_API_KEY is missing")
        raise GeminiLLMError("Gemini API key is not configured. Please set GEMINI_API_KEY in your environment.")
    
    tool = types.Tool(function_declarations=[EXTRACT_TASK_FUNCTION])

    context_note = ""
    if current_date:
        context_note += f"Today's date is {current_date}. "
    if timezone_name:
        context_note += f"Interpret relative dates in the {timezone_name} timezone. "

    contents = f"{context_note}{raw_input}" if context_note else raw_input
    
    logger.info(f"Starting AI task parsing with input length: {len(raw_input)}")

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[tool],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                ),
                http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
            ),
        )
        logger.info("Gemini API call successful")
    except Exception as exc:
        logger.error(f"Gemini API call failed: {str(exc)}", exc_info=True)
        raise GeminiLLMError(str(exc)) from exc

    if not response.function_calls:
        logger.error("Gemini did not return a function_call")
        raise GeminiParseError("Gemini did not return a function_call.")

    parsed_payload = dict(response.function_calls[0].args)
    logger.info(f"Successfully parsed task fields: {list(parsed_payload.keys())}")

    return response, parsed_payload