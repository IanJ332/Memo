#!/usr/bin/env python3
"""scripts/test_jetstream_llm.py

Connectivity verification test for the Jetstream2-hosted LLM service.
Runs using the repository .venv environment and openai client library.
"""

import sys
import time

# Rule: Windows UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ENDPOINT = "https://llm.jetstream-cloud.org/llama-4-scout/v1/"
MODEL = "llama-4-scout"
PROMPT = "Confirm successful Jetstream2 model access in one sentence."

print("==================================================")
print("       JETSTREAM2 LLM CONNECTIVITY TEST           ")
print("==================================================")
print(f"Endpoint:         {ENDPOINT}")
print(f"Model requested:  {MODEL}")
print(f"Prompt sent:      {PROMPT}")
print("Connecting...")

try:
    from openai import OpenAI
except ImportError:
    print("\nERROR: 'openai' library is not installed in the current Python environment.", file=sys.stderr)
    print("Ensure you are running with .venv/bin/python or .venv\\Scripts\\python.exe.", file=sys.stderr)
    sys.exit(1)

client = OpenAI(
    base_url=ENDPOINT,
    api_key="empty",
    timeout=30.0,
)

start_time = time.perf_counter()
success = False
error_type = None
error_msg = None
response_text = ""
returned_model = "N/A"
usage_info = "N/A"

try:
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=64,
        temperature=0.0,
    )
    latency = time.perf_counter() - start_time
    success = True

    if completion.model:
        returned_model = completion.model

    if completion.choices and len(completion.choices) > 0:
        response_text = completion.choices[0].message.content or ""
        response_text = response_text.strip()

    if completion.usage:
        usage_info = (
            f"prompt_tokens={completion.usage.prompt_tokens}, "
            f"completion_tokens={completion.usage.completion_tokens}, "
            f"total_tokens={completion.usage.total_tokens}"
        )

except Exception as exc:
    latency = time.perf_counter() - start_time
    success = False
    error_type = type(exc).__name__
    error_msg = str(exc)

print("\n--- Results ---")
print(f"Status:           {'SUCCESS' if success else 'FAILURE'}")
print(f"Latency:          {latency:.2f} seconds")

if success:
    print(f"Returned Model:   {returned_model}")
    print(f"Token Usage:      {usage_info}")
    print(f"Response Text:    {response_text}")
    print("\nConnectivity verified successfully.")
    sys.exit(0)
else:
    print(f"Error Type:       {error_type}")
    print(f"Error Details:    {error_msg}")
    print("\nConnectivity test failed.")
    sys.exit(2)
