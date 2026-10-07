"""
Conference Schedule Concierge (Strands) -- entry point.

A single Strands agent that answers attendee questions about a (fictional)
conference by READING a governed semantic layer at runtime, instead of carrying
the schedule's structure in its prompt. Thin: delegates to the concierge package.

Run:
    python main.py "What AI talks are on Tuesday, and which rooms?"
"""
import sys


def main():
    question = " ".join(sys.argv[1:]) or \
        "What AI talks are on Tuesday, who is speaking, and in which room?"
    try:
        from concierge.agent import build_agent
        agent = build_agent()
    except Exception as e:
        print("Strands SDK not installed or model not configured.")
        print("Install with:  pip install strands-agents strands-agents-tools")
        print(f"(import/runtime error: {e})")
        return
    print(agent(question))


if __name__ == "__main__":
    main()
