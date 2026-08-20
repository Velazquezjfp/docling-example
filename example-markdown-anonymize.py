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
    SYSTEM_PROMPT = """You are an expert infrastructure, networking, and API data anonymization engine.
    Scan the input technical documentation and extract ALL private, sensitive, internal, or identifying entities.
    
    Map every identified entity to a deterministic, indexed, generic category placeholder following these standards:
    
    1. URLs, Endpoints & APIs:
       - Full API URLs -> 'https://api.domain-a.internal/v1/endpoint-a'
       - URI Paths / Specific Endpoints -> '/api/v1/endpoint-a', '/endpoint-b', '/webhook-1'
       - Internal FQDNs / Base Domains -> 'domain-a.internal', 'srv-a.local'
    
    2. Networks & Addressing:
       - Private IPs / CIDRs -> '10.0.X.X', '192.168.X.X', 'Subnet-A'
       - VLANs -> 'VLAN-1', 'VLAN-2'
    
    3. Infrastructure & Compute:
       - Hostnames / Clusters -> 'Host-A', 'Cluster-1', 'Node-A'
       - Buckets / Repositories -> 'bucket-a', 'repo-alpha'
       - Databases / Schemas -> 'db-instance-1', 'schema_a'
    
    4. Organization & Projects:
       - Companies / Clients / Vendors -> 'Company A', 'Client 1', 'Vendor A'
       - Project / Initiative names -> 'Project A', 'Project B'
       - Contracts / Agreements -> 'Contract A', 'SLA-1'
    
    5. Identities & Secrets:
       - Real person names -> 'Person 1', 'Person 2'
       - Account / Tenant IDs -> 'ID-001', 'Tenant-A'
       - Secrets / API Keys / Tokens -> '[REDACTED_SECRET_1]', '[AUTH_TOKEN_A]'
    
    CRITICAL RULES:
    1. Return ONLY a valid JSON object: {"<original_term>": "<assigned_placeholder>"}.
    2. Maintain strict 1:1 consistency (the exact same endpoint or URL must always map to the exact same placeholder).
    3. Capture both full URLs and isolated endpoint paths (e.g., capture both 'https://api.company.com/v1/auth' and standalone '/v1/auth').
    4. Do NOT use arbitrary proper nouns; use indexed category names ('Endpoint-A', 'domain-a.internal')."""

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
