"""Conference Schedule Concierge (Strands) -- thin CLI entry point.

A single agent answers attendee questions about a (fictional) conference by
READING a governed semantic layer at runtime instead of carrying the schedule's
structure in its prompt. This file just builds the agent and asks it a question.

Run:
    python main.py "What AI talks are on Tuesday, and which rooms?"
"""
import sys


def main():
    question = " ".join(sys.argv[1:]) or \
        "What AI talks are on Tuesday, who is speaking, and in which room?"
    try:
        from agent import build_agent
        concierge = build_agent()
    except Exception as e:
        # Graceful failure: guidance, not a stack trace, when the SDK/model
        # is absent. This keeps a first run friendly for a new programmer.
        print("Strands SDK not installed or model not configured.")
        print("Install with:  pip install strands-agents strands-agents-tools")
        print("Then set AWS_REGION + BEDROCK_MODEL_ID (see .env.example).")
        print(f"(import/runtime detail: {e})")
        return
    print(concierge(question))


if __name__ == "__main__":
    main()
