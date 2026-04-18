#!/bin/bash

# Check agent cards for local deployments and save to local files

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Checking Agent Cards..."
echo "================================"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Warning: jq not installed. Output will not be formatted."
    JQ_CMD="cat"
else
    JQ_CMD="jq ."
fi

echo ""
echo "Travel Assistant Agent Card:"
echo "--------------------------------"
mkdir -p "$SCRIPT_DIR/results"
TRAVEL_CARD_FILE="$SCRIPT_DIR/results/travel_assistant_agent_card.json"
TRAVEL_CARD_RESPONSE=$(curl -s http://127.0.0.1:10001/.well-known/agent-card.json)

if [ -n "$TRAVEL_CARD_RESPONSE" ]; then
    echo "$TRAVEL_CARD_RESPONSE" | $JQ_CMD
    if command -v jq &> /dev/null; then
        echo "$TRAVEL_CARD_RESPONSE" | jq . > "$TRAVEL_CARD_FILE"
    else
        echo "$TRAVEL_CARD_RESPONSE" > "$TRAVEL_CARD_FILE"
    fi
    echo "[PASS] Travel Assistant agent card retrieved"
    echo "   Saved to: $TRAVEL_CARD_FILE"
else
    echo "[FAIL] Failed to retrieve Travel Assistant agent card"
    echo "   Is the agent running on port 10001?"
fi

echo ""
echo "Flight Booking Agent Card:"
echo "--------------------------------"
BOOKING_CARD_FILE="$SCRIPT_DIR/results/flight_booking_agent_card.json"
BOOKING_CARD_RESPONSE=$(curl -s http://127.0.0.1:10002/.well-known/agent-card.json)

if [ -n "$BOOKING_CARD_RESPONSE" ]; then
    echo "$BOOKING_CARD_RESPONSE" | $JQ_CMD
    if command -v jq &> /dev/null; then
        echo "$BOOKING_CARD_RESPONSE" | jq . > "$BOOKING_CARD_FILE"
    else
        echo "$BOOKING_CARD_RESPONSE" > "$BOOKING_CARD_FILE"
    fi
    echo "[PASS] Flight Booking agent card retrieved"
    echo "   Saved to: $BOOKING_CARD_FILE"
else
    echo "[FAIL] Failed to retrieve Flight Booking agent card"
    echo "   Is the agent running on port 10002?"
fi

echo ""
echo "================================"
echo "Summary:"
if [ -f "$TRAVEL_CARD_FILE" ]; then
    echo "[PASS] Travel Assistant agent card saved"
fi
if [ -f "$BOOKING_CARD_FILE" ]; then
    echo "[PASS] Flight Booking agent card saved"
fi
echo "================================"
