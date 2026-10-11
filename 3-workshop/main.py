from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from state import State
from agents import orchestrator
from nodes import (
    human_node,
    check_exit_condition,
    orchestrator_routing,
    participant_node,
    summarizer_node
)


load_dotenv(override=True)  # Override, so it would use your local .env file




def build_graph():
    """
    Build the LangGraph workflow.
    """

    builder = StateGraph(State)

    builder.add_node("human", human_node)
    builder.add_node("orchestrator", orchestrator)  # Use orchestrator directly
    builder.add_node("participant", participant_node)
    builder.add_node("summarizer", summarizer_node)

    # Edges
    builder.add_edge(START, "human")

    builder.add_conditional_edges(
        "human",
        check_exit_condition,
        {
            "end": END,
            "orchestrator": "orchestrator"
        }
    )

    builder.add_conditional_edges(
        "orchestrator",
        orchestrator_routing,
        {
            "participant": "participant",
            "summarizer": "summarizer"
        }
    )

    builder.add_edge("participant", "orchestrator")

    builder.add_edge("summarizer", "human")

    return builder.compile()


def main():
    print("=== SINGAPORE OUTING PLANNER ===")
    print("Tell the team what you'd like to do. After each round the team gives you a")
    print("recommendation, and you can reply. Type 'exit' to finish.\n")
    print("The team checks live data: Hui Min (weather), Dr. Farah (haze)")
    print("and Ravi (public transport). The Trip Planner decides who speaks next.\n")
    print("Try: 'We want to go to Gardens by the Bay now, from Tampines Mall.'\n")

    graph = build_graph()

    print(graph.get_graph().draw_ascii())

    initial_state = State(
        messages=[],
        volley_msg_left=0,
        next_speaker=None
    )

    try:
        # LangGraph stops after 25 steps by default, and each message to the team
        # uses about 13, so the third message would crash. 500 is plenty.
        graph.invoke(initial_state, {"recursion_limit": 500})
        print("\nEnjoy your day out!")
    except KeyboardInterrupt:
        print("\n\nConversation interrupted. Goodbye!")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Ending conversation...")


if __name__ == "__main__":
    main()
