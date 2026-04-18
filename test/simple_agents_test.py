#!/usr/bin/env python3
"""Test script for Travel Assistant and Flight Booking agents.

Usage: uv run python test/simple_agents_test.py [--debug]
"""

import argparse
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import (
    Any,
)

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

import requests

# Configure logging with basicConfig
logging.basicConfig(
    level=logging.INFO,  # Set the log level to INFO
    # Define log message format
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)

LOCAL_ENDPOINTS = {
    "travel_assistant": "http://127.0.0.1:10001",
    "flight_booking": "http://127.0.0.1:10002",
}


class AgentTester:
    """Agent testing class for local endpoints."""

    def __init__(
        self,
        endpoints: dict[str, str],
    ) -> None:
        """Initialize with endpoint configuration."""
        self.endpoints = endpoints

    def send_agent_message(
        self,
        agent_type: str,
        message: str,
    ) -> dict[str, Any]:
        """Send message to agent using A2A protocol."""
        endpoint = self.endpoints[agent_type]
        if not endpoint:
            raise ValueError(f"No endpoint configured for {agent_type}")

        request_id = f"test-{uuid.uuid4().hex[:8]}"
        message_id = f"test-msg-{uuid.uuid4().hex[:8]}"

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "messageId": message_id,
                }
            },
        }

        logger.debug(f"[REQUEST] Agent: {agent_type}, Endpoint: {endpoint}")
        logger.debug(
            f"[REQUEST] Payload:\n{json.dumps(payload, indent=2)}"
        )

        start_time = time.time()
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        response_time = time.time() - start_time

        response_json = response.json()
        logger.debug(
            f"[RESPONSE] Time: {response_time:.3f}s, "
            f"Status: {response.status_code}"
        )
        logger.debug(
            f"[RESPONSE] Body:\n"
            f"{json.dumps(response_json, indent=2, default=str)}"
        )

        return response_json

    def call_api_endpoint(
        self,
        agent_type: str,
        endpoint: str,
        method: str = "POST",
        **params,
    ) -> dict[str, Any]:
        """Call direct API endpoint."""
        url = f"{self.endpoints[agent_type]}{endpoint}"
        if not self.endpoints[agent_type]:
            raise ValueError(f"No endpoint configured for {agent_type}")

        logger.debug(f"[API REQUEST] Agent: {agent_type}, URL: {url}")
        logger.debug(
            f"[API REQUEST] Method: {method}, Params: {params}"
        )

        start_time = time.time()
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=60)
        else:
            response = requests.post(url, params=params, timeout=60)
        response_time = time.time() - start_time

        response_json = response.json()
        logger.debug(
            f"[API RESPONSE] Time: {response_time:.3f}s, "
            f"Status: {response.status_code}"
        )
        logger.debug(
            f"[API RESPONSE] Body:\n"
            f"{json.dumps(response_json, indent=2, default=str)}"
        )

        return response_json

    def ping_agent(
        self,
        agent_type: str,
    ) -> bool:
        """Check if agent is healthy."""
        try:
            url = f"{self.endpoints[agent_type]}/ping"
            logger.debug(f"[PING] Agent: {agent_type}, URL: {url}")

            start_time = time.time()
            response = requests.get(url, timeout=5)
            response_time = time.time() - start_time

            is_healthy = (
                response.status_code == 200
                and response.json().get("status") == "healthy"
            )
            logger.debug(
                f"[PING RESPONSE] Time: {response_time:.3f}s, "
                f"Healthy: {is_healthy}"
            )

            return is_healthy
        except Exception as e:
            logger.debug(f"[PING ERROR] Agent: {agent_type}, Error: {e}")
            return False


class TravelAssistantTests:
    """Test suite for Travel Assistant agent."""

    def __init__(
        self,
        tester: AgentTester,
    ) -> None:
        """Initialize with tester."""
        self.tester = tester
        self.agent_type = "travel_assistant"

    def test_ping(self) -> None:
        """Test agent health check."""
        print("Testing Travel Assistant ping...")
        result = self.tester.ping_agent(self.agent_type)
        assert result, "Travel Assistant ping failed"
        print("[PASS] Travel Assistant is healthy")

    def test_agent_flight_search(self) -> None:
        """Test agent flight search via A2A."""
        print("Testing Travel Assistant flight search...")
        message = "Search for flights from SF to NY on 2025-11-15"
        response = self.tester.send_agent_message(
            self.agent_type, message
        )

        assert "result" in response, (
            f"No result in response: {response}"
        )
        assert "artifacts" in response["result"], (
            "No artifacts in response"
        )

        artifacts = response["result"]["artifacts"]
        assert len(artifacts) > 0, "No artifacts returned"

        response_text = ""
        for artifact in artifacts:
            if "parts" in artifact:
                for part in artifact["parts"]:
                    if "text" in part:
                        response_text += part["text"]

        assert "flight" in response_text.lower(), (
            f"Response doesn't mention flights. "
            f"Got: {response_text[:100]}"
        )
        print("[PASS] Travel Assistant flight search working")

    def test_api_search_flights(self) -> None:
        """Test direct API endpoint."""
        print("Testing Travel Assistant API endpoint...")
        response = self.tester.call_api_endpoint(
            self.agent_type,
            "/api/search-flights",
            departure_city="SF",
            arrival_city="NY",
            departure_date="2025-11-15",
        )

        assert "result" in response, (
            f"No result in API response: {response}"
        )
        result_data = json.loads(response["result"])
        assert "flights" in result_data, "No flights in API response"
        assert len(result_data["flights"]) > 0, "No flights found"
        out = RESULTS_DIR / "search_flights_response.json"
        out.write_text(json.dumps(response, indent=2))
        print(f"   Saved API response to: {out}")
        print("[PASS] Travel Assistant API endpoint working")

    def test_api_recommendations(self) -> None:
        """Test recommendations API."""
        print("Testing Travel Assistant recommendations...")
        response = self.tester.call_api_endpoint(
            self.agent_type,
            "/api/recommendations",
            method="GET",
            max_price=300,
            preferred_airlines="United,Delta",
        )

        assert "result" in response, (
            "No result in recommendations response"
        )
        result_data = json.loads(response["result"])
        assert "recommendations" in result_data, (
            "No recommendations in response"
        )
        out = RESULTS_DIR / "recommendations_response.json"
        out.write_text(json.dumps(response, indent=2))
        print(f"   Saved API response to: {out}")
        print("[PASS] Travel Assistant recommendations working")


class FlightBookingTests:
    """Test suite for Flight Booking agent."""

    def __init__(
        self,
        tester: AgentTester,
    ) -> None:
        """Initialize with tester."""
        self.tester = tester
        self.agent_type = "flight_booking"

    def test_ping(self) -> None:
        """Test agent health check."""
        print("Testing Flight Booking ping...")
        result = self.tester.ping_agent(self.agent_type)
        assert result, "Flight Booking ping failed"
        print("[PASS] Flight Booking is healthy")

    def test_agent_availability_check(self) -> None:
        """Test agent availability check via A2A."""
        print("Testing Flight Booking availability check...")
        message = "Check availability for flight ID 1"
        response = self.tester.send_agent_message(
            self.agent_type, message
        )

        assert "result" in response, (
            f"No result in response: {response}"
        )
        assert "artifacts" in response["result"], (
            "No artifacts in response"
        )

        artifacts = response["result"]["artifacts"]
        assert len(artifacts) > 0, "No artifacts returned"

        response_text = artifacts[0]["parts"][0]["text"]
        assert "available" in response_text.lower(), (
            "Response doesn't mention availability"
        )
        print("[PASS] Flight Booking availability check working")

    def test_agent_booking(self) -> None:
        """Test agent booking via A2A."""
        print("Testing Flight Booking reservation...")
        message = "Book flight ID 1 for Jane Smith, email jane@test.com"
        response = self.tester.send_agent_message(
            self.agent_type, message
        )

        assert "result" in response, (
            f"No result in response: {response}"
        )
        artifacts = response["result"]["artifacts"]
        response_text = artifacts[0]["parts"][0]["text"]

        assert (
            "booking" in response_text.lower()
            or "reserved" in response_text.lower()
        ), "Response doesn't mention booking/reservation"
        print("[PASS] Flight Booking reservation working")

    def test_api_check_availability(self) -> None:
        """Test direct API endpoint."""
        print("Testing Flight Booking API endpoint...")
        response = self.tester.call_api_endpoint(
            self.agent_type, "/api/check-availability", flight_id=1
        )

        assert "result" in response, (
            f"No result in API response: {response}"
        )
        result_data = json.loads(response["result"])
        assert "flight_id" in result_data, (
            "No flight_id in API response"
        )
        assert "available_seats" in result_data, (
            "No available_seats in response"
        )
        out = RESULTS_DIR / "check_availability_response.json"
        out.write_text(json.dumps(response, indent=2))
        print(f"   Saved API response to: {out}")
        print("[PASS] Flight Booking API endpoint working")


def run_tests() -> bool:
    """Run all tests."""
    print("Running tests against local endpoints...")
    print("=" * 50)

    endpoints = LOCAL_ENDPOINTS
    tester = AgentTester(endpoints)

    try:
        # Test Travel Assistant
        print("\nTesting Travel Assistant Agent")
        print("-" * 30)
        travel_tests = TravelAssistantTests(tester)
        travel_tests.test_ping()
        travel_tests.test_agent_flight_search()
        travel_tests.test_api_search_flights()
        travel_tests.test_api_recommendations()

        # Test Flight Booking
        print("\nTesting Flight Booking Agent")
        print("-" * 30)
        booking_tests = FlightBookingTests(tester)
        booking_tests.test_ping()
        booking_tests.test_agent_availability_check()
        booking_tests.test_agent_booking()
        booking_tests.test_api_check_availability()

        print("\n" + "=" * 50)
        print("All tests passed!")
        return True

    except Exception as e:
        logger.exception("Test failed with exception")
        print(f"\nTest failed: {e}")
        return False


def main() -> None:
    """Main entry point for test script."""
    parser = argparse.ArgumentParser(
        description="Test Travel Assistant and Flight Booking agents"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for detailed request/response traces",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")

    RESULTS_DIR.mkdir(exist_ok=True)
    output_file = RESULTS_DIR / "task2_test_output.txt"
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
