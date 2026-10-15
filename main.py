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
        print("Install with:  pip install -r requirements.txt")
        print("Then set MODEL_PROVIDER in .env (see .env.example):")
        print("  - ollama  (default, no AWS): run `ollama serve` locally")
        print("  - bedrock: set AWS_REGION + BEDROCK_MODEL_ID and AWS creds")
        print(f"(setup detail: {e})")
        return

    # Step 2: ask the model. Failures here happen at call time. We print a short,
    # friendly hint instead of a long traceback, because a new programmer running
    # this for the first time will usually hit one of these, and a wall of stack
    # frames hides the real cause.
    try:
        print(concierge(question))
    except Exception as e:
        print("The model call failed. Common causes:")
        print("  - Ollama not running -> start it with `ollama serve` and pull the")
        print("    model (`ollama pull llama3.1`); check OPENAI_BASE_URL in .env.")
        print("  - Bedrock: expired AWS credentials -> refresh them (e.g.")
        print("    `aws sso login`); check `aws sts get-caller-identity` succeeds.")
        print("  - Bedrock: model not enabled in your region -> enable it in the")
        print("    Bedrock console for the region in your .env (AWS_REGION).")
        print("  - Throttling -> wait a moment and try again.")
        print(f"(error detail: {type(e).__name__}: {e})")
        return


if __name__ == "__main__":
    main()
