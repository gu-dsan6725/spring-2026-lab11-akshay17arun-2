# Task 3 Observations: A2A Agent Discovery and Communication

## A2A Messages Exchanged Between Agents

### Test 1: Travel Agent Solo Flight Search

**Request sent to Travel Assistant (port 10001):**
```json
{
  "jsonrpc": "2.0",
  "id": "test-Search for",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Search for flights from New York to Los Angeles on 2025-12-20"
        }
      ],
      "messageId": "msg-Search for"
    }
  }
}
```

**Response preview:**
```
I still don't see any flights available from New York to Los Angeles on December 20, 2025. The system shows 0 flights for this route and date.

Would you like me to:
1. Search for flights on nearby dates (December 19, 21, or other dates)?
2. Try a different route or city pair?
3. Check if there are flights available from Los Angeles to New York instead?

Let me know how I can help!

```

### Test 2: Travel Agent Discovers and Delegates to Booking Agent

**Request sent to Travel Assistant:**
- Message: "I want to book flight ID 1. I need you to reserve 2 seats, confirm the reservation, and process the payment..."
- The Travel Assistant then internally discovers the Flight Booking Agent via the registry and sends it A2A messages.

**Final response preview:**
```
Unfortunately, the Flight Booking Agent is the only agent available that has the capabilities to reserve seats, confirm bookings, and process payments, but it's currently not responding to requests.

This could indicate:
- The booking service is temporarily down
- The agent may require a specific format or additional information (passenger details, payment method, etc.)
- There may be a connectivity issue with the remote agent

**Flight Details You're Trying to Book:**
- Flight ID: 1
- Flight: U
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
{
  "jsonrpc": "2.0",
  "id": "test-Search for",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Search for flights from New York to Los Angeles on 2025-12-20"
        }
      ],
      "messageId": "msg-Search for"
    }
  }
}
```

**Response format:**
```json
{
  "jsonrpc": "2.0",
  "id": "test-Search for",
  "result": {
    "artifacts": [
      {
        "parts": [
          {
            "kind": "text",
            "text": "<agent response text>"
          }
        ]
      }
    ]
  }
}
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
