import json
import re
from typing import Any, Dict, List, Optional, Type, Union

from langchain_core.messages import AIMessage


def parse_sections(response: Union[str, AIMessage]) -> Dict[str, str]:
    """Parse sections from the response based on expected section headers.

    Args:
        response: The input response to parse.
        expected_sections: A list of expected section headers.
    Returns:
        A dictionary mapping section headers to their corresponding content.
    """
    # Create a dictionary to store the parsed sections
    sections = {}
    if isinstance(response, AIMessage):
        response = response.content

    # Find all sections using regex pattern that matches opening and closing tags
    pattern = r"<(\w+)>(.*?)</\1>"
    matches = re.findall(pattern, response, re.DOTALL)

    # Process each match and add to sections dictionary
    for tag, content in matches:
        # Strip whitespace from content
        sections[tag] = content.strip()

    return sections


def parse_json(
    response: Union[str, AIMessage], data_schema: Optional[Type] = None
) -> Dict[str, Any]:
    """Extract and parse JSON object from the response.

    Args:
        response: The input response containing a JSON object.
        data_schema: Optional Pydantic model to validate against.
    Returns:
        The parsed JSON object as a dictionary or validated model instance.
    """
    try:
        if isinstance(response, AIMessage):
            response = response.content
        
        # First try to find JSON content between ```json and ``` markers
        json_pattern = r"```json\s*(.*?)\s*```"
        json_match = re.search(json_pattern, response, re.DOTALL)
        
        if json_match:
            response = json_match.group(1).strip()
        else:
            # If no full markdown block, clean up any partial markers
            response = response.strip()
            
            # Remove ```json or ``` at the start
            if response.startswith("```json"):
                response = response[7:].strip()  # Remove ```json
            elif response.startswith("```"):
                response = response[3:].strip()  # Remove ```
            
            # Remove ``` at the end
            if response.endswith("```"):
                response = response[:-3].strip()
        
        # Parse JSON and filter out None values
        parsed_json = json.loads(response)
        
        if data_schema:
            if parsed_json:
                return data_schema(**parsed_json)
            else:
                return None
        
        return {k: v for k, v in parsed_json.items() if v is not None}
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}\nContent: {response[:200]}...")


def parse_thoughts(text: str) -> List[str]:
    """Parse the thoughts and result from the text.

    Args:
        text: The input text containing <think> and <result> sections.
    Returns:
        A list containing the thoughts and the result JSON object.
    """
    return [t for t in text.split("\n") if t.strip()]
