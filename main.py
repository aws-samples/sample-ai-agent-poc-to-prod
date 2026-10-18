"""Conference Schedule Concierge (Strands) -- thin CLI entry point.

A single agent answers attendee questions about a (fictional) conference by
READING a governed semantic layer at runtime instead of carrying the schedule's
structure in its prompt. This file just builds the agent and asks it a question.

Run:
    python main.py "What AI talks are on Tuesday, and which rooms?"

Add --prototype to run the OTHER version instead -- the hardcoded-prompt
anti-pattern this project exists to fix (see agent.py's PROTOTYPE_SYSTEM_PROMPT).
Use it to see the before/after live:
    python main.py --prototype "..."   # hardcoded facts, no data lookup
    # now edit data/*.csv (e.g. move the AI track to a different room)
    python main.py --prototype "..."   # SAME prompt, SAME question -> now wrong
    python main.py "..."               # semantic-layer version -> stays correct
"""
import sys


def main():
    args = sys.argv[1:]
    prototype = "--prototype" in args
    args = [a for a in args if a != "--prototype"]
    question = " ".join(args) or \
        "What AI talks are on Tuesday, who is speaking, and in which room?"

    print(f"[mode: {'prototype (hardcoded prompt, no tools)' if prototype else 'semantic layer'}]")

    # Step 1: build the agent. Failures here are setup problems — the SDK is not
    # installed, or the model/config is missing.
    try:
        from agent import build_agent
        concierge = build_agent(prototype=prototype)
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
        # Strands already streams the agent's output to stdout as it generates,
        # so printing the return value here would print the same answer twice.
        concierge(question)
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
