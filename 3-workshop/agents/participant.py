from tools import weather, haze, journey
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from utils import debug
import re


# Persona configurations. Each team member has one tool.
PERSONAS = {
    "huimin": {
        "name": "Hui Min",
        "role": "Weather Forecaster",
        "backstory": "Former NEA meteorologist who plans her family's outings",
        "personality": "Precise and cheerful",
        "speech_style": "Plain English, says which region and time a forecast is for",
        "tools": ["weather"]
    },
    "farah": {
        "name": "Dr. Farah",
        "role": "Health & Safety Officer",
        "backstory": "Family doctor who sees asthma cases every haze season",
        "personality": "Caring but firm",
        "speech_style": "Calm, gives the reading and what it means for the plan",
        "tools": ["haze"]
    },
    "ravi": {
        "name": "Ravi",
        "role": "Getting-there Guide",
        "backstory": "Former bus captain who knows every MRT interchange",
        "personality": "Practical and efficient",
        "speech_style": "Brisk, step-by-step directions with times",
        "tools": ["journey"]
    }
}


# Tool name (what an agent writes after "Action:") -> the function that runs it.
TOOLS = {
    "weather": weather,
    "haze": haze,
    "journey": journey,
}

TOOL_DESCRIPTIONS = {
    "weather": "Returns NEA's 24-hour forecast for the five regions of Singapore.\ne.g. Action: weather",
    "haze": "Returns the 24-hour PSI (haze) for the five regions, with NEA's label.\ne.g. Action: haze",
    "journey": "Plans public transport leaving now. Input: start -> destination.\ne.g. Action: journey: Tampines Mall -> Gardens by the Bay",
}


def execute_tool(persona_id, tool_name, tool_input=""):
    """
    Execute a tool for a persona, if that persona is allowed to use it.
    Returns Tool output as string
    """
    tool_name = tool_name.lower().strip()

    if tool_name not in TOOLS:
        return f"Unknown tool: {tool_name}"

    # The prompt tells each agent which tools it has; this check makes sure
    # an agent can't use any other tool, whatever it writes.
    if tool_name not in PERSONAS[persona_id]["tools"]:
        debug(f"ACCESS DENIED: {PERSONAS[persona_id]['name']} tried to use '{tool_name}'")
        return f"ACCESS DENIED: you do not have permission to use '{tool_name}'. Ask the teammate who has it."

    return TOOLS[tool_name](tool_input)


def participant(persona_id, state) -> dict:
    """
    Generate speech for a persona using ReAct workflow with real tool calling.

    Args:
        persona_id: One of "huimin", "farah", "ravi"
        state: Current conversation state

    Returns:
        Dict with message updates for state
    """
    if persona_id not in PERSONAS:
        return {"messages": [{"role": "assistant", "content": f"Unknown persona: {persona_id}"}]}

    persona = PERSONAS[persona_id]
    debug(f"\n=== {persona['name']} is thinking... ===")

    # Get recent conversation for context
    messages = state.get("messages", [])
    conversation_text = ""
    for msg in messages:
        conversation_text += f"{msg.get('content', '')}\n"

    # Build available actions list based on persona's tools
    available_actions = ""
    for tool in persona['tools']:
        available_actions += f"\n\n{tool}:\n{TOOL_DESCRIPTIONS[tool]}"

    # System prompt for ReAct
    system_prompt = f"""You are {persona['name']}, {persona['role']}.
Background: {persona['backstory']}
Personality: {persona['personality']}
Speech style: {persona['speech_style']}

You are part of a small team planning a day out in Singapore for the human ("You").
Teammates: Hui Min (weather), Dr. Farah (haze), Ravi (public transport).

You run in a loop of Thought, Action, Observation.
At the end of the loop you output a Message.

Use Thought to describe your thoughts about the plan.
Use Action to run one of the actions available to you, written as "Action: tool_name" or "Action: tool_name: input".
Observation will be the result of running those actions.

Possible actions are:

{available_actions}

You only have access to the tools/actions listed above. Do not call tools that you do not have access to.
If you need something you cannot check yourself, look for it in the conversation first.
Ask the right teammate only if no one has said it yet.

------

Example session:

Thought: I should check the forecast before suggesting anything outdoors
Action: weather

You will be called again with:
Observation: [The actual result of the tool]

You must never guess the weather, the haze or a route. Rely on the Observation for those.
If a tool says UNAVAILABLE, say so plainly.

You then continue thinking or output:
Message: [Your response in character]

IMPORTANT:
- You can use multiple actions by continuing the loop
- You must not be providing Observation in your response. Observation is a result from tool, not for you to respond.
- Once you have enough information, output Message: followed by your response
- Keep your Message concise (1-3 sentences) and in character
"""

    # Internal loop for ReAct
    max_iterations = 5  # Prevent infinite loops
    internal_context = f"Planning conversation so far:\n{conversation_text}\n\nContinue as {persona['name']}.\n"

    for iteration in range(max_iterations):
        user_prompt = internal_context
        debug(f"Iteration {iteration + 1}/{max_iterations}")

        try:
            llm = ChatOpenAI(model="gpt-5-mini", temperature=1)
            # llm = ChatOpenAI(model="gpt-5-mini", temperature=1, base_url=os.getenv("https://127.0.0.1:1337/v1"))

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            content = response.content.strip()
            debug(f"LLM Response:\n{content}\n")

            # Check for an Action first. If a reply has both an Action and a
            # Message, the Message was written before the tool ran, so run the
            # tool and ignore the rest of the reply.
            if "Action:" in content:
                # Extract the action. "Action: haze" or "Action: journey: A -> B":
                # group(1) is the tool name, group(2) the input after the second colon.
                action_match = re.search(r'Action:\s*(\w+)(?:\s*:\s*(.*))?', content)
                if action_match:
                    tool_name = action_match.group(1)
                    tool_input = (action_match.group(2) or "").strip()
                    debug(f"Executing tool: {tool_name}({tool_input})")

                    # Execute the tool
                    observation = execute_tool(persona_id, tool_name, tool_input)
                    debug(f"Observation: {observation}")
                    debug("")  # Empty line for readability

                    # Add observation to internal context (without anything written after the Action)
                    internal_context += f"\n{content[:action_match.end()]}\n\nObservation: {observation}\n"
                    continue

            # Check if the response contains Message:
            if "Message:" in content:
                # Extract the message
                message_match = re.search(r'Message:\s*(.*)', content, re.DOTALL)
                if message_match:
                    final_message = message_match.group(1).strip()
                    debug(f"Final Message: {final_message}")
                    debug(f"=== End of {persona['name']}'s thought process ===\n")

                    # Return the message to state
                    return {
                        "messages": [{
                            "role": "assistant",
                            "name": persona['name'],
                            "content": f"\n{persona['name']}: {final_message}\n\n"
                        }]
                    }

            # If we get here without action or message, add to context and continue
            internal_context += f"\n{content}\n"

        except Exception as e:
            # Fallback response if LLM fails
            return {
                "messages": [{
                    "role": "assistant",
                    "name": persona['name'],
                    "content": f"{persona['name']}: Sorry, I lost my connection for a moment."
                }]
            }

    # If we exhausted iterations without getting a Message, provide default
    return {
        "messages": [{
            "role": "assistant",
            "name": persona['name'],
            "content": f"{persona['name']}: Let me come back to you on that."
        }]
    }
