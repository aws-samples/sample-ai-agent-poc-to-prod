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

    # Step 1: build the agent. Failures here are setup problems — the SDK is not
    # installed, or the model/config is missing.
    try:
        from agent import build_agent
        concierge = build_agent()
    except Exception as e:
        print("Strands SDK not installed or model not configured.")
        print("Install with:  pip install strands-agents strands-agents-tools")
        print("Then set AWS_REGION + BEDROCK_MODEL_ID (see .env.example).")
        print(f"(setup detail: {e})")
        return

    # Step 2: ask the model. Failures here happen at call time — most often
    # expired AWS credentials, the model not being enabled in your region, or
    # throttling. We print a short, friendly hint instead of a long traceback,
    # because a new programmer running this for the first time will usually hit
    # exactly one of these, and a wall of stack frames hides the real cause.
    try:
        print(concierge(question))
    except Exception as e:
        print("The model call failed. Common causes:")
        print("  - Expired AWS credentials  -> refresh them (e.g. `aws sso login`)")
        print("    and check `aws sts get-caller-identity` succeeds.")
        print("  - Model not enabled in your region -> enable the model in the")
        print("    Bedrock console for the region in your .env (AWS_REGION).")
        print("  - Throttling -> wait a moment and try again.")
        print(f"(error detail: {type(e).__name__}: {e})")
        return


if __name__ == "__main__":
    main()
