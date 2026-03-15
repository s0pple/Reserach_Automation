import sys
import json
from src.core.secret import generate_content_with_key_rotation

prompt = "Hello"
response = generate_content_with_key_rotation(
    prompt_parts=[prompt]
)
print("No schema:")
print(response.text)

prompt = "Say hello in JSON."
response = generate_content_with_key_rotation(
    prompt_parts=[prompt],
    generation_config={"response_mime_type": "application/json"}
)
print("With schema:")
print(response.text)
