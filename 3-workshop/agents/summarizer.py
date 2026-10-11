from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage


def summarizer(state) -> str:
    """
    Generate a recommendation using LLM at the end of each round.

    Args:
        state: Current conversation state with messages

    Returns:
        Formatted summary string
    """
    messages = state.get("messages", [])

    if not messages:
        return "No conversation to summarize."

    # Extract conversation text
    conversation_text = ""
    for msg in messages:
        # Messages are now always dicts
        conversation_text += f"{msg.get('content', '')}\n"

    if not conversation_text.strip():
        return "No conversation content to summarize."

    # System prompt for summarization
    system_prompt = """You are writing a recommendation for the human after a planning conversation about a day out in Singapore.

Start with your recommendation: whether to go, and when. Then give the weather and haze
readings the team found, how to get there, and a backup if it rains. Only use facts from
the conversation so far. If something was not checked, write "not checked". Keep it short."""

    user_prompt = f"""Here's the planning conversation:

{conversation_text}

Please write the recommendation."""

    try:
        # Call LLM
        llm = ChatOpenAI(model="gpt-5-nano", temperature=1)
        # llm = ChatOpenAI(model="gpt-5-nano", temperature=1, base_url="http://127.0.0.1:1337/v1")

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        if isinstance(response.content, list):
            summary = " ".join(str(item) for item in response.content).strip()
        else:
            summary = str(response.content).strip()

        # Format with header
        return f"=== RECOMMENDATION ===\n\n{summary}"

    except Exception as e:
        # Fallback to basic summary if LLM fails
        return f"""=== RECOMMENDATION ===

Total messages: {len(messages)}

Unable to write the recommendation at this time.
Scroll up to see the conversation."""
