import asyncio
import warnings

# Suppress ADK and dependency warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=RuntimeWarning)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from .agent import root_agent

async def main_async():
    # Setup constants
    APP_NAME = "Greeting Agent"
    USER_ID = "user"
    
    # Create session service
    session_service = InMemorySessionService()
    
    # Create a new session
    new_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )
    SESSION_ID = new_session.id
    print(f"Created new session: {SESSION_ID}")
    
    # Create runner with the agent
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    
    # Interactive conversation loop
    print("\nWelcome to Greeting Agent!")
    print("Type 'exit' or 'quit' to end the conversation.\n")
    
    while True:
        # Get user input
        user_input = input("You: ")
        
        # Check if user wants to exit
        if user_input.lower() in ["exit", "quit"]:
            print("Ending conversation. Goodbye!")
            break
        
        # Process the user query through the agent
        print("Agent: ", end="", flush=True)
        
        # Run the agent
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=user_input,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text, end="", flush=True)
        print()  # New line after response

def main():
    """Entry point for the application."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
