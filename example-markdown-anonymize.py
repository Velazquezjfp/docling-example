import json
import re
from pathlib import Path
import requests

# --- Configuration & Paths ---
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "output"

INPUT_FILE = INPUT_DIR / "docling_output.md"
OUTPUT_FILE = OUTPUT_DIR / "anonymized_output.md"

# LiteLLM Configuration
API_URL = "http://localhost:4000/v1/chat/completions"
API_KEY = "your-litellm-key"
MODEL_NAME = "qwen-coder-30b"


def get_anonymization_mapping(markdown_text: str) -> dict:
    system_prompt = (
       "You are an entity anonymization tool. Scan the text to identify all sensitive identifiers "
        "and map them to standardized, indexed category placeholders.\n\n"
        "Use sequential schemes such as:\n"
        "- Organizations / Companies -> 'Company A', 'Company B', 'Firm A'\n"
        "- Projects / Initiatives -> 'Project A', 'Project B'\n"
        "- Contracts / Agreements -> 'Contract A', 'Contract B'\n"
        "- Individuals / Names -> 'Person 1', 'User 1'\n"
        "- Internal systems, IDs, endpoints -> 'System A', 'ID-001', 'service-alpha'\n\n"
        "Rules:\n"
        "1. Maintain 1:1 consistency (the same entity must always receive the same indexed placeholder).\n"
        "2. Do not invent arbitrary fictional names (like 'HOH' or 'Bambu'); use generic categorizations.\n"
        "3. Return ONLY a valid JSON object where keys are original terms and values are their assigned placeholders."
    )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Extract and replace all sensitive identifiers:\n\n{markdown_text[:16000]}",
            },
        ],
    }

    res = requests.post(API_URL, json=payload, headers=headers, timeout=90)
    res.raise_for_status()

    raw_text = res.json()["choices"][0]["message"]["content"].strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\n|```$", "", raw_text)

    return json.loads(raw_text)


def anonymize_markdown(input_path: Path, output_path: Path):
    if not input_path.exists():
        raise FileNotFoundError(f"Source file not found at: {input_path}")

    # Ensure destination directory exists before writing
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = input_path.read_text(encoding="utf-8")

    mapping = get_anonymization_mapping(content)
    print("Generated Replacement Mapping:")
    print(json.dumps(mapping, indent=2))

    # Sort descending by key length to avoid prefix collisions
    sorted_keys = sorted(mapping.keys(), key=len, reverse=True)

    anonymized_content = content
    for original in sorted_keys:
        replacement = mapping[original]
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        anonymized_content = pattern.sub(replacement, anonymized_content)

    output_path.write_text(anonymized_content, encoding="utf-8")
    print(f"\nSaved anonymized markdown to: {output_path.resolve()}")


if __name__ == "__main__":
    anonymize_markdown(INPUT_FILE, OUTPUT_FILE)
