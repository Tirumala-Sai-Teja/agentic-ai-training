# ADK v2 Sessions and State Guide

## What I Modified

### Question Answering Agent Changes
- **Agent Class**: `Agent` → `LlmAgent` (ADK v2)
- **Model**: Updated to `gemini/gemini-3.6-flash` (consistent with other agents)
- **Instruction**: Updated to use session state syntax `{state}` instead of `{user_name}` placeholders
- **Output Key**: Added `output_key="answer"` for ADK v2 state management

### Email Agent Fix
- **Syntax Error**: Removed trailing comma after `output_key="email"`

## ADK v2 Sessions and State Explained

### 1. What are Sessions?

A **session** represents a single conversation between a user and an agent. It maintains:
- **Conversation history**: All messages exchanged
- **State**: Key-value pairs that persist across turns
- **Session ID**: Unique identifier for the session
- **User ID**: Identifier for the user

### 2. What is State?

**State** is a dictionary that stores persistent information across conversation turns. Think of it as the agent's "memory" that carries information between messages.

## Syntax for Building Sessions

### Basic Session Creation

```python
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# Create session service
session_service = InMemorySessionService()

# Create a session with initial state
session = await session_service.create_session(
    app_name="MyApp",
    user_id="user123",
    state={
        "user_name": "John",
        "preferences": ["tech", "sports"],
        "conversation_count": 0
    }
)
```

### Session with Runner

```python
# Create runner with session service
runner = Runner(
    agent=my_agent,
    app_name="MyApp",
    session_service=session_service,
)

# Run the agent with session
async for event in runner.run_async(
    user_id="user123",
    session_id=session.id,
    new_message="Hello",
):
    print(event)
```

## State Syntax in Agent Instructions

### Accessing State in Instructions

```python
agent = LlmAgent(
    name="my_agent",
    instruction="""
    You are a helpful assistant.
    
    Access user information from state:
    - User name: {state.user_name}
    - Preferences: {state.preferences}
    - Conversation count: {state.conversation_count}
    
    Update state when user provides new information.
    """,
)
```

### State Updates

State is automatically updated when:
1. Agent outputs structured data with `output_key`
2. Tools return data that modifies state
3. Explicit state updates in workflows

## Complete Example: Session-Based Agent

```python
import asyncio
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
import os

load_dotenv()

# Create agent
model = LiteLlm(
    model="gemini/gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

agent = LlmAgent(
    name="personal_assistant",
    model=model,
    instruction="""
    You are a personal assistant that remembers user preferences.
    
    Current state: {state}
    
    Remember:
    - User's name when they tell you
    - Their preferences for future conversations
    - Important information they share
    
    Update state when you learn new information about the user.
    """,
    output_key="response",
)

async def main():
    # Create session service
    session_service = InMemorySessionService()
    
    # Create session with initial state
    session = await session_service.create_session(
        app_name="PersonalAssistant",
        user_id="user123",
        state={
            "user_name": None,
            "preferences": [],
            "important_facts": []
        }
    )
    
    # Create runner
    runner = Runner(
        agent=agent,
        app_name="PersonalAssistant",
        session_service=session_service,
    )
    
    # Conversation loop
    print("Chat with your personal assistant (type 'exit' to quit)")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        
        # Run agent with session
        async for event in runner.run_async(
            user_id="user123",
            session_id=session.id,
            new_message=user_input,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent: {part.text}")
    
    # Check final state
    final_session = await session_service.get_session(
        app_name="PersonalAssistant",
        user_id="user123",
        session_id=session.id
    )
    print(f"Final state: {final_session.state}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key State Features in ADK v2

### 1. **Automatic State Injection**
- `{state}` in instructions is automatically replaced with current state
- No manual state passing needed
- State is always available to the agent

### 2. **State Persistence**
- State persists across conversation turns
- Survives agent restarts (with persistent storage)
- Can be saved and loaded

### 3. **Structured State Updates**
```python
# Agent can update state through output_key
agent = LlmAgent(
    output_key="user_info",  # Stores output in state["user_info"]
)

# Access in next turn
instruction="""
Previous user info: {state.user_info}
"""
```

### 4. **Session Storage Options**

```python
# In-memory (ephemeral)
from google.adk.sessions import InMemorySessionService
session_service = InMemorySessionService()

# SQLite (persistent)
from google.adk.sessions import SqliteSessionService
session_service = SqliteSessionService(db_path="sessions.db")

# Custom session service
from google.adk.sessions import SessionService
session_service = MyCustomSessionService()
```

## Benefits of ADK v2 Sessions and State

### 1. **Memory Management**
- Automatic conversation history
- No manual message management
- Efficient storage and retrieval

### 2. **State Consistency**
- Thread-safe state updates
- Automatic conflict resolution
- Consistent state across agents

### 3. **Workflow Integration**
- State flows between workflow nodes
- Each agent can access and modify state
- Supports complex multi-agent workflows

### 4. **Persistence Options**
- In-memory for development
- SQLite for production
- Custom backends for enterprise

## Comparison: ADK v1 vs v2

### ADK v1 (Manual State)
```python
# Manual state management
state = {"user_name": "John"}

# Pass state manually
response = agent.run("Hello", state=state)

# Update state manually
state["last_interaction"] = datetime.now()
```

### ADK v2 (Automatic State)
```python
# Automatic state management
session = await session_service.create_session(state={"user_name": "John"})

# State automatically available
instruction = "Hello {state.user_name}"

# State automatically updated via output_key
agent = LlmAgent(output_key="response")
```

## Advanced State Patterns

### 1. **Counters and Trackers**
```python
state = {
    "message_count": 0,
    "last_topic": None,
    "user_satisfaction": 0
}
```

### 2. **User Profiles**
```python
state = {
    "profile": {
        "name": None,
        "preferences": [],
        "history": []
    }
}
```

### 3. **Contextual Information**
```python
state = {
    "current_context": "shopping",
    "previous_queries": [],
    "active_task": None
}
```

## Best Practices

### 1. **Initialize State with Defaults**
```python
state = {
    "user_name": None,  # Default values
    "preferences": [],
    "conversation_count": 0
}
```

### 2. **Use Descriptive State Keys**
```python
# Good
state = {"user_name": "John"}

# Avoid
state = {"data": "John"}
```

### 3. **Structure Complex State**
```python
state = {
    "user_profile": {
        "name": "John",
        "preferences": ["tech", "sports"]
    },
    "conversation_metadata": {
        "start_time": "2026-08-29",
        "message_count": 5
    }
}
```

## Testing Your Updated Agent

```bash
cd D:\Github\agentic-ai-training\day4\google_adk
adk run ./5-sessions-and-state/question_answering_agent "What's my name?"
```

## Summary

**What I modified:**
- Updated question answering agent to ADK v2
- Fixed syntax error in email agent
- Updated models to current Gemini version
- Added session state syntax to instructions

**ADK v2 Sessions and State:**
- Automatic state management via `{state}` syntax
- Session service for conversation persistence
- Multiple storage options (in-memory, SQLite, custom)
- Seamless workflow integration
- Better memory management and consistency
