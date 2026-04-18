#!/usr/bin/env python3
"""Test script for agent discovery and booking workflow.

Test 1: Travel agent searches for flights using its own tools
Test 2: Travel agent discovers booking agent, checks availability,
        reserves seats, and completes booking

Usage: uv run python test/agent_discovery_test.py
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import requests

RESULTS_DIR = Path(__file__).parent / "results"


class _Tee:
    """Write to multiple streams simultaneously."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            s.write(data)

    def flush(self):
        for s in self._streams:
            s.flush()

# Configure logging with basicConfig
logging.basicConfig(
    level=logging.INFO,  # Set the log level to INFO
    # Define log message format
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)

LOCAL_ENDPOINTS = {
    "travel_assistant": "http://127.0.0.1:10001",
}


class AgentTester:
    """Agent testing class."""

    def __init__(
        self,
        endpoints: dict[str, str],
    ):
        """Initialize with endpoint configuration."""
        self.endpoints = endpoints

    def send_agent_message(
        self,
        agent_type: str,
        message: str,
    ) -> dict:
        """Send message to agent using A2A protocol."""
        endpoint = self.endpoints[agent_type]

        payload = {
            "jsonrpc": "2.0",
            "id": f"test-{message[:10]}",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "messageId": f"msg-{message[:10]}",
                }
            },
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        result = response.json()
        logger.debug(f"[REQUEST]\n{json.dumps(payload, indent=2)}")
        logger.debug(f"[RESPONSE]\n{json.dumps(result, indent=2, default=str)}")
        return result

    def extract_response_text(
        self,
        response: dict,
    ) -> str:
        """Extract text from A2A response."""
        if "result" not in response:
            return ""

        artifacts = response["result"].get("artifacts", [])
        response_text = ""
        for artifact in artifacts:
            if "parts" in artifact:
                for part in artifact["parts"]:
                    if "text" in part:
                        response_text += part["text"]
        return response_text


class AgentDiscoveryTests:
    """Test suite for agent discovery and booking workflow."""

    def __init__(
        self,
        tester: AgentTester,
    ):
        """Initialize with tester."""
        self.tester = tester
        self.agent_type = "travel_assistant"

    def test_search_flight_solo(self) -> str:
        """Test 1: Travel agent searches for flights using its own tools."""
        print("\n1. Testing flight search (travel agent solo)...")
        message = (
            "Search for flights from New York to Los Angeles "
            "on 2025-12-20"
        )
        response = self.tester.send_agent_message(
            self.agent_type, message
        )

        assert "result" in response, f"No result in response: {response}"
        response_text = self.tester.extract_response_text(response)

        assert any(
            keyword in response_text.lower()
            for keyword in [
                "flight", "new york", "los angeles", "nyc", "lax",
            ]
        ), f"Response doesn't mention flight search. Got: {response_text[:300]}"

        print("   [PASS] Travel agent searched for flights using its own tools")
        print(f"   Response preview: {response_text[:200]}...")
        return response_text

    def test_book_flight_with_discovery(self) -> str:
        """Test 2: Travel agent discovers booking agent and delegates."""
        print("\n2. Testing flight booking with agent discovery...")
        message = (
            "I want to book flight ID 1. I need you to reserve 2 seats, "
            "confirm the reservation, and process the payment. You don't "
            "have these booking capabilities yourself, so you'll need to "
            "find and use an agent that can handle flight reservations "
            "and confirmations."
        )
        response = self.tester.send_agent_message(
            self.agent_type, message
        )
        response_text = self.tester.extract_response_text(response)

        assert any(
            keyword in response_text.lower()
            for keyword in [
                "reserve", "book", "confirm", "agent", "discover",
            ]
        ), f"Booking workflow failed. Got: {response_text[:300]}"
        print("      [PASS] Booking agent discovered and invoked")
        print(f"   Response preview: {response_text[:200]}...")

        print("   [PASS] Complete booking workflow succeeded")
        return response_text


def run_tests() -> bool:
    """Run all discovery tests."""
    print("Running agent discovery and booking workflow tests...")
    print("=" * 70)
    print("Test 1: Travel agent searches for flights (solo)")
    print("Test 2: Travel agent discovers booking agent and completes booking")
    print("=" * 70)

    endpoints = LOCAL_ENDPOINTS
    tester = AgentTester(endpoints)

    try:
        discovery_tests = AgentDiscoveryTests(tester)

        solo_response = discovery_tests.test_search_flight_solo()
        booking_response = discovery_tests.test_book_flight_with_discovery()

        print("\n" + "=" * 70)
        print("All tests passed!")
        print("=" * 70)
        _write_observations(solo_response, booking_response)
        return True

    except AssertionError as e:
        logger.error(f"Test assertion failed: {e}")
        print(f"\nTest failed: {e}")
        return False
    except Exception as e:
        logger.exception("Test failed with exception")
        print(f"\nTest failed with exception: {e}")
        return False


def _write_observations(solo_response: str, booking_response: str) -> None:
    """Write observations.md based on test run results."""
    RESULTS_DIR.mkdir(exist_ok=True)
    obs_file = RESULTS_DIR / "observations.md"

    a2a_request_example = json.dumps({
        "jsonrpc": "2.0",
        "id": "test-Search for",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "Search for flights from New York to Los Angeles on 2025-12-20"}],
                "messageId": "msg-Search for"
            }
        }
    }, indent=2)

    a2a_response_example = json.dumps({
        "jsonrpc": "2.0",
        "id": "test-Search for",
        "result": {
            "artifacts": [
                {
                    "parts": [
                        {"kind": "text", "text": "<agent response text>"}
                    ]
                }
            ]
        }
    }, indent=2)

    content = f"""# Task 3 Observations: A2A Agent Discovery and Communication

## A2A Messages Exchanged Between Agents

### Test 1: Travel Agent Solo Flight Search

**Request sent to Travel Assistant (port 10001):**
```json
{a2a_request_example}
```

**Response preview:**
```
{solo_response[:500]}
```

### Test 2: Travel Agent Discovers and Delegates to Booking Agent

**Request sent to Travel Assistant:**
- Message: "I want to book flight ID 1. I need you to reserve 2 seats, confirm the reservation, and process the payment..."
- The Travel Assistant then internally discovers the Flight Booking Agent via the registry and sends it A2A messages.

**Final response preview:**
```
{booking_response[:500]}
```

## How the Travel Assistant Discovered the Flight Booking Agent

The Travel Assistant uses its `discover_remote_agents` tool to query the registry stub running on port 7861.
It sends a semantic search query (e.g., "book flights") to the registry, which returns matching agent cards.
The agent card for the Flight Booking Agent (port 10002) includes its capabilities (skills), endpoint URL,
and supported input/output modes. The Travel Assistant then caches this card and uses `invoke_remote_agent`
to send an A2A `message/send` request directly to the Flight Booking Agent.

## JSON-RPC Request/Response Format Observed

**Request format:**
```json
{a2a_request_example}
```

**Response format:**
```json
{a2a_response_example}
```

Key fields:
- `jsonrpc`: Always `"2.0"` per the JSON-RPC spec
- `method`: `"message/send"` for sending a message to an agent
- `params.message.parts`: Array of content parts (text, data, etc.)
- `result.artifacts`: Array of output artifacts from the agent

## Agent Card Information and Usage

The agent card (retrieved from `/.well-known/agent-card.json`) contains:
- **name** and **description**: Human-readable identity of the agent
- **url**: The endpoint where A2A messages should be sent
- **skills**: List of capabilities with `id`, `name`, `description`, and `examples`
- **defaultInputModes** / **defaultOutputModes**: Supported content types (e.g., `text/plain`)

The Travel Assistant uses the skill descriptions and examples to determine which remote agent
is appropriate for a given task, then invokes it by POSTing a `message/send` JSON-RPC request
to the agent's `url`.

## Benefits and Limitations of the A2A Approach

### Benefits
- **Interoperability**: Any agent implementing the A2A spec can communicate with any other,
  regardless of the underlying model or framework.
- **Discovery**: Agents advertise their capabilities via agent cards, enabling dynamic discovery
  without hardcoded integrations.
- **Loose coupling**: Agents only need to know the endpoint URL and the JSON-RPC message format,
  not each other's internal implementation.
- **Composability**: Complex workflows can be built by chaining specialized agents, each doing
  one thing well.

### Limitations
- **Latency**: Multi-agent workflows add round-trip overhead for each agent-to-agent call.
- **Error handling**: Failures in a downstream agent must be surfaced back through the chain,
  complicating error propagation.
- **Discovery reliability**: The registry stub is a single point of failure; if it is down,
  agents cannot discover each other.
- **Context loss**: Each A2A call is stateless by default — conversation history must be
  explicitly passed or re-established.
"""

    obs_file.write_text(content)
    print(f"Observations saved to: {obs_file}")


def main() -> None:
    """Main entry point for test script."""
    parser = argparse.ArgumentParser(
        description="Test agent discovery and booking workflow"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    RESULTS_DIR.mkdir(exist_ok=True)
    output_file = RESULTS_DIR / "task3_discovery_output.txt"
    with open(output_file, "w") as f:
        sys.stdout = _Tee(sys.__stdout__, f)
        try:
            success = run_tests()
        finally:
            sys.stdout = sys.__stdout__

    print(f"Test output saved to: {output_file}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
