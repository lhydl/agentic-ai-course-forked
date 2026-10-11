from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from utils import debug


def orchestrator(state):
    """
    Select next speaker based on conversation context.
    Manages volley control and updates state accordingly.

    Updates state with:
    - next_speaker: Selected agent ID, "human", or None when the round is done
    - volley_msg_left: Decremented counter

    Returns: Updated state
    """

    debug(state)
    volley_left = state.get("volley_msg_left", 0)
    debug(f"Volley messages left: {volley_left}", "ORCHESTRATOR")

    if volley_left <= 0:
        debug("No volleys left, returning to human", "ORCHESTRATOR")
        return {
            "next_speaker": "human",
            "volley_msg_left": 0
        }

    messages = state.get("messages", [])

    conversation_text = ""
    for msg in messages:
        # Messages are now always dicts
        conversation_text += f"{msg.get('content', '')}\n"

    system_prompt = """You are the Trip Planner for a small team that plans a day out in Singapore for the human ("You").
    You don't look anything up yourself; you decide who speaks next.

    Available speakers:
    - huimin: Hui Min, weather forecaster. Can check today's forecast.
    - farah: Dr. Farah, health and safety officer. Can check the haze (PSI).
    - ravi: Ravi, getting-there guide. Can plan public transport.

    Pick the person whose tool the plan needs next, based on what the human asked
    and what has not been checked yet. Don't pick someone to repeat work already done.

    Reply "done" when huimin, farah and ravi have each spoken at least once and the
    human's latest message has been answered. The team then gives its recommendation.

    Respond with ONLY the speaker ID (huimin, farah, or ravi), or done.
    """

    user_prompt = f"""Planning conversation:
{conversation_text}

Who should speak next?"""

    debug("Analyzing conversation context...", "ORCHESTRATOR")

    # Call LLM
    try:
        llm = ChatOpenAI(model="gpt-5-mini", temperature=1)
        # llm = ChatOpenAI(model="gpt-5-nano", temperature=1, base_url=os.getenv("https://127.0.0.1:1337/v1"))

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        # Extract speaker from response
        if isinstance(response.content, list):
            selected_speaker = " ".join(str(item) for item in response.content).strip().lower()
        else:
            selected_speaker = str(response.content).strip().lower()
        debug(f"LLM selected: {selected_speaker}", "ORCHESTRATOR")

        # End the round early. With no messages left, the summarizer runs next.
        if selected_speaker == "done":
            return {"next_speaker": None, "volley_msg_left": 0}

        # Validate speaker
        valid_speakers = ["huimin", "farah", "ravi"]
        if selected_speaker not in valid_speakers:
            # Fallback to a random speaker if invalid
            import random
            selected_speaker = random.choice(valid_speakers)
            debug(f"Invalid speaker, fallback to: {selected_speaker}", "ORCHESTRATOR")

    except Exception as e:
        # Fallback selection if LLM fails
        import random
        valid_speakers = ["huimin", "farah", "ravi"]
        selected_speaker = random.choice(valid_speakers)
        debug(f"LLM error, random selection: {selected_speaker}", "ORCHESTRATOR")

    debug(f"Final selection: {selected_speaker} (volley {volley_left} -> {volley_left - 1})", "ORCHESTRATOR")

    # Return only the updates (LangGraph will merge with existing state)
    return {
        "next_speaker": selected_speaker,
        "volley_msg_left": volley_left - 1
    }
