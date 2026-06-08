"""
TWZRD Agent Intel integration for Letta (MemGPT).

Demonstrates how to use the TWZRD Agent Intel MCP server as a tool in a Letta
agent, enabling long-running agents to verify trust scores before authorizing
x402 micropayments or delegating to other autonomous agents.

The TWZRD Agent Intel server provides:
  - score_agent(wallet)       — 0-100 trust score + risk flags (free)
  - preflight_check(wallet)   — PASS/FAIL gate for x402 payments (free)
  - get_trust_receipt(wallet) — signed trust receipt (HTTP 402 paid)

MCP endpoint: https://intel.twzrd.xyz/mcp  (streamable-http, no auth required)
Website: https://intel.twzrd.xyz

Install:
    pip install letta mcp

Usage:
    python examples/notebooks/data/twzrd_agent_intel.py
"""
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from letta import create_client
from letta.schemas.tool import Tool

TWZRD_MCP_URL = "https://intel.twzrd.xyz/mcp"


# --- Standalone MCP helper (use outside Letta, or in tool implementations) ---

async def score_agent_async(wallet: str) -> dict:
    """
    Check an agent's trust score via TWZRD Agent Intel.

    Args:
        wallet: Solana wallet address (base58 string)

    Returns:
        dict with keys: score (int 0-100), risk_flags (list[str])
    """
    async with streamablehttp_client(TWZRD_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("score_agent", {"wallet": wallet})

    text = result.content[0].text if result.content else "{}"
    try:
        return json.loads(text)
    except (json.JSONDecodeError, AttributeError):
        return {"score": 0, "risk_flags": ["parse_error"]}


async def preflight_check_async(wallet: str) -> bool:
    """
    Run preflight check — returns True if agent passes x402 payment gate.

    Args:
        wallet: Solana wallet address (base58 string)

    Returns:
        True if PASS, False if FAIL
    """
    async with streamablehttp_client(TWZRD_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("preflight_check", {"wallet": wallet})

    text = result.content[0].text if result.content else ""
    return "PASS" in text.upper()


# --- Letta tool functions (synchronous wrappers for use as Letta tools) ---

def check_agent_trust_score(wallet: str) -> str:
    """
    Check the TWZRD trust score for a Solana agent wallet.

    Use this tool to verify agent trustworthiness before authorizing x402
    micropayments or delegating sensitive tasks to another agent.

    Args:
        wallet: Solana wallet address (base58 encoded string) of the agent to check.

    Returns:
        JSON string with trust score (0-100) and any risk flags.
        Score >= 60 is required for x402 payment authorization.
        Score >= 80 indicates high-trust agent.
    """
    result = asyncio.run(score_agent_async(wallet))
    score = result.get("score", 0)
    flags = result.get("risk_flags", [])

    if score >= 80:
        trust_level = "HIGH"
    elif score >= 60:
        trust_level = "MEDIUM"
    else:
        trust_level = "LOW"

    return json.dumps({
        "wallet": wallet,
        "score": score,
        "trust_level": trust_level,
        "risk_flags": flags,
        "authorized_for_payments": score >= 60 and not flags,
    })


def run_agent_preflight(wallet: str) -> str:
    """
    Run a preflight trust check on an agent wallet before x402 payment.

    Use this tool as a binary gate: if the result is FAIL, do NOT proceed
    with any payment-sensitive actions involving this agent.

    Args:
        wallet: Solana wallet address (base58 encoded string) of the agent to check.

    Returns:
        "PASS" if the agent is cleared for x402 payments, "FAIL" otherwise.
    """
    passed = asyncio.run(preflight_check_async(wallet))
    return "PASS" if passed else "FAIL"


# --- Letta agent setup ---

def create_trust_aware_letta_agent():
    """Create a Letta agent with TWZRD trust verification tools."""
    client = create_client()

    # Register TWZRD tools
    score_tool = client.create_or_update_tool(
        func=check_agent_trust_score,
        name="check_agent_trust_score",
    )
    preflight_tool = client.create_or_update_tool(
        func=run_agent_preflight,
        name="run_agent_preflight",
    )

    agent = client.create_agent(
        name="trust-verifier",
        memory_blocks=[],
        system=(
            "You are a trust verification agent. "
            "Before any action involving x402 payments or delegating to external agents, "
            "use check_agent_trust_score and run_agent_preflight to verify the agent's "
            "trustworthiness. Only proceed if the trust score >= 60 and preflight = PASS."
        ),
        tool_ids=[score_tool.id, preflight_tool.id],
    )
    return client, agent


if __name__ == "__main__":
    # Test standalone tools
    wallet = "4LkEFjHsF2ubC8K4oF2r3rCFqPZQVGBjL9mV6xkNPZdf"

    print("Testing TWZRD Agent Intel tools:")
    print(f"  score_agent: {asyncio.run(score_agent_async(wallet))}")
    print(f"  preflight_check: {'PASS' if asyncio.run(preflight_check_async(wallet)) else 'FAIL'}")

    print("\nTool function output:")
    print(f"  check_agent_trust_score: {check_agent_trust_score(wallet)}")
    print(f"  run_agent_preflight: {run_agent_preflight(wallet)}")
