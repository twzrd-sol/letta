"""
TWZRD Agent Intel + Letta: Trust-verified agent-to-agent interactions

This example shows how to use TWZRD Agent Intel MCP tools within Letta agents
to perform trust verification before agent-to-agent communication on Solana.

Requirements:
    pip install letta mcp twzrd-agent-intel

Usage:
    python twzrd_agent_intel_trust_verification.py
"""
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# TWZRD Agent Intel remote MCP server — zero install, no API key needed
TWZRD_MCP_URL = "https://intel.twzrd.xyz/mcp"


async def check_agent_trust(wallet_address: str) -> dict:
    """Score a Solana wallet using TWZRD Agent Intel.

    Args:
        wallet_address: Base58 Solana wallet address of the agent to score

    Returns:
        dict with trust_score (0-100), reputation data, and payment history
    """
    async with streamablehttp_client(TWZRD_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("score_agent", {"wallet": wallet_address})
            return result.content[0].text


async def preflight_check(wallet_address: str) -> dict:
    """Run a preflight trust check before transacting with an agent.

    Use this before sending x402 payments or sharing sensitive data
    with an unknown agent wallet.
    """
    async with streamablehttp_client(TWZRD_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("preflight_check", {"wallet": wallet_address})
            return result.content[0].text


async def verify_trust_receipt(receipt: str) -> dict:
    """Verify an x402 payment receipt from an agent.

    Args:
        receipt: The x402 trust receipt string from the paying agent
    """
    async with streamablehttp_client(TWZRD_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("verify_trust_receipt", {"receipt": receipt})
            return result.content[0].text


async def main():
    # Example: verify counterparty agent before responding to a Letta agent message
    counterparty_wallet = "D1QkbFJKiPsymJ65RKHhF6DFB8sPMfpBaFBzuHKfJGWi"

    print("=== TWZRD Agent Intel Trust Check ===")

    # Step 1: Score the agent
    print(f"Scoring agent wallet: {counterparty_wallet}")
    score = await check_agent_trust(counterparty_wallet)
    print(f"Trust score result: {score}")

    # Step 2: Preflight before transacting
    print("\nRunning preflight check...")
    preflight = await preflight_check(counterparty_wallet)
    print(f"Preflight result: {preflight}")

    # Step 3: Example — only proceed if trust score >= 50
    import json
    try:
        data = json.loads(score) if isinstance(score, str) else score
        trust_score = data.get("trust_score", 0)
        if trust_score >= 50:
            print(f"\nAgent passed trust check (score: {trust_score}). Safe to proceed.")
        else:
            print(f"\nAgent failed trust check (score: {trust_score}). Rejecting interaction.")
    except (json.JSONDecodeError, AttributeError):
        print(f"\nRaw score response: {score}")

    print("\n=== MCP Config for Claude Desktop / other clients ===")
    print('{"mcpServers": {"twzrd-agent-intel": {"url": "https://intel.twzrd.xyz/mcp"}}}')
    print("\nPyPI: pip install twzrd-agent-intel")


if __name__ == "__main__":
    asyncio.run(main())
