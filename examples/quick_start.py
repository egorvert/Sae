#!/usr/bin/env python3
"""Quick start example for the Sae Legal Agent.

This script demonstrates how to:
1. Check if the agent is running
2. Submit a contract for analysis
3. Poll for results
4. Display the analysis

Prerequisites:
    - Sae agent running at http://localhost:8000
    - (Optional) API key if authentication is enabled

Usage:
    python examples/quick_start.py
    python examples/quick_start.py --api-key YOUR_KEY
    python examples/quick_start.py --file contract.pdf
"""

import argparse
import base64
import sys
import time
import uuid
from pathlib import Path

import httpx

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 120  # Max seconds to wait for completion


def check_agent_health(client: httpx.Client) -> bool:
    """Check if the agent is running."""
    try:
        response = client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"Agent: {data.get('agent', 'Unknown')}")
            print(f"Version: {data.get('version', 'Unknown')}")
            print(f"Status: {data.get('status', 'Unknown')}")
            return True
    except httpx.ConnectError:
        print(f"Could not connect to agent at {BASE_URL}")
        print("Make sure the agent is running: uv run uvicorn sae.main:app --reload")
    return False


def get_agent_card(client: httpx.Client) -> dict | None:
    """Fetch the agent card to see capabilities."""
    response = client.get(f"{BASE_URL}/.well-known/agent.json")
    if response.status_code == 200:
        return response.json()
    return None


def send_contract(
    client: httpx.Client,
    contract_text: str | None = None,
    file_path: Path | None = None,
) -> str:
    """Send a contract for analysis.

    Returns:
        Task ID
    """
    task_id = str(uuid.uuid4())

    # Build message parts
    parts: list[dict] = []

    if contract_text:
        parts.append({
            "type": "text",
            "text": contract_text,
        })

    if file_path:
        # Read and encode file as data URI
        mime_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }
        suffix = file_path.suffix.lower()
        mime_type = mime_types.get(suffix, "application/octet-stream")

        with open(file_path, "rb") as f:
            file_bytes = f.read()
        data_uri = f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode()}"

        parts.append({
            "type": "file",
            "file": {
                "uri": data_uri,
                "mimeType": mime_type,
                "name": file_path.name,
            },
        })

    # Send JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "id": "1",
        "params": {
            "id": task_id,
            "message": {
                "role": "user",
                "parts": parts,
            },
        },
    }

    response = client.post(f"{BASE_URL}/a2a", json=request)
    data = response.json()

    if "error" in data:
        raise Exception(f"Failed to send contract: {data['error']}")

    return data["result"]["id"]


def poll_for_result(client: httpx.Client, task_id: str) -> dict:
    """Poll until task is complete."""
    print(f"Task ID: {task_id}")
    print("Waiting for analysis...", end="", flush=True)

    start_time = time.time()

    while time.time() - start_time < TIMEOUT:
        request = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "id": "2",
            "params": {"id": task_id},
        }

        response = client.post(f"{BASE_URL}/a2a", json=request)
        data = response.json()

        if "error" in data:
            raise Exception(f"Failed to get task: {data['error']}")

        result = data["result"]
        state = result["status"]["state"]

        if state == "completed":
            print(" Done!")
            return result
        elif state == "failed":
            print(" Failed!")
            raise Exception(f"Task failed: {result}")
        else:
            print(".", end="", flush=True)
            time.sleep(2)

    raise Exception("Timeout waiting for analysis")


def display_results(result: dict) -> None:
    """Display the analysis results."""
    print("\n" + "=" * 60)
    print("CONTRACT ANALYSIS RESULTS")
    print("=" * 60)

    for artifact in result.get("artifacts", []):
        print(f"\n{artifact['name'].upper()}")
        print("-" * 40)
        for part in artifact.get("parts", []):
            if part.get("type") == "text":
                print(part["text"])


# Sample contract for testing
SAMPLE_NDA = """
NON-DISCLOSURE AGREEMENT

1. CONFIDENTIALITY
The Receiving Party agrees to hold in confidence all Confidential Information
disclosed by the Disclosing Party for a period of five (5) years.

2. LIMITATION OF LIABILITY
THE DISCLOSING PARTY SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
OR CONSEQUENTIAL DAMAGES ARISING FROM THIS AGREEMENT. TOTAL LIABILITY
SHALL NOT EXCEED ONE HUNDRED DOLLARS ($100).

3. TERM AND TERMINATION
This Agreement shall remain in effect for two (2) years. Either party
may terminate with 30 days written notice.

4. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a contract with Sae")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument(
        "--file", type=Path, help="Path to contract file (PDF/DOCX/TXT)"
    )
    parser.add_argument(
        "--text", help="Contract text (uses sample NDA if not provided)"
    )
    parser.add_argument(
        "--url", default=BASE_URL, help=f"Agent URL (default: {BASE_URL})"
    )
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.url

    # Build headers
    headers: dict[str, str] = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    with httpx.Client(headers=headers, timeout=30) as client:
        # 1. Check health
        print("Checking agent health...")
        if not check_agent_health(client):
            sys.exit(1)

        print()

        # 2. Show agent capabilities
        card = get_agent_card(client)
        if card:
            print(f"Agent: {card.get('name')}")
            skills = [s["name"] for s in card.get("skills", [])]
            print(f"Skills: {skills}")
            print()

        # 3. Send contract
        print("Sending contract for analysis...")
        contract_text = args.text or (None if args.file else SAMPLE_NDA)
        task_id = send_contract(client, contract_text, args.file)

        # 4. Wait for result
        result = poll_for_result(client, task_id)

        # 5. Display
        display_results(result)


if __name__ == "__main__":
    main()
