from typing import Literal
from state import State
from agents import orchestrator, participant, summarizer


def human_node(state: State) -> dict:
    """
    Human input node - gets user input and sets volley count.
    """
    user_input = input("\nYou: ").strip()

    human_message = {
        "role": "user",
        "content": f"You: {user_input}"
    }

    return {
        "messages": [human_message],
        "volley_msg_left": 5
    }


def check_exit_condition(state: State) -> Literal["end", "orchestrator"]:
    """
    Check if user typed 'exit' to end conversation.
    """
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        content = last_message.get("content", "")

        if "exit" in content.lower():
            return "end"

    return "orchestrator"


def orchestrator_routing(state: State) -> Literal["participant", "summarizer"]:
    """
    Route from orchestrator based on volley count. When the round is over,
    the summarizer writes a recommendation before it is the human's turn again.
    """
    volley_left = state.get("volley_msg_left", 0)

    if volley_left > 0:
        return "participant"
    else:
        return "summarizer"


def participant_node(state: State) -> dict:
    """
    Participant node - calls the appropriate participant and handles output.
    """
    next_speaker = state.get("next_speaker", "huimin")  # Default fallback

    # Call participant with the selected speaker
    result = participant(next_speaker, state)

    # Print and return messages
    if result and "messages" in result:
        for msg in result["messages"]:
            print(msg.get("content", ""))
        return {"messages": result["messages"]}

    return {}


def summarizer_node(state: State) -> dict:
    """
    Summarizer node - writes a recommendation at the end of each round.
    """
    # Generate and print summary
    summary = summarizer(state)
    print(f"\n{summary}")

    return {}  # Printed only, not added to the conversation
