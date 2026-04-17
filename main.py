from core.pipeline import create_session, process_turn


conversation_session = create_session()


def process_message(message: str, session: dict | None = None, response_delay_seconds: int = 18):
    active_session = session if session is not None else conversation_session
    return process_turn(
        message=message,
        session=active_session,
        response_delay_seconds=response_delay_seconds,
    )


def run_cli():
    print("=== Hermes Honeypot CLI ===\n")

    while True:
        message = input("Scammer: ").strip()
        if not message:
            continue

        result = process_message(message)

        print("\nDetection:", result["detection"]["verdict"])
        print("Confidence:", result["detection"]["combined_score"])
        print("State:", result["state"])
        print("Session Score:", result["score"])
        print("Risk:", f"{result['risk_level']} ({result['risk_score']})")
        print("Time Wasted:", result["time_wasted_human"])

        if result["reasons"]:
            print("Escalation Reasons:", ", ".join(result["reasons"]))

        print("AI:", result["response"])
        print("Extracted:", result["extraction"])
        print("-" * 50)


if __name__ == "__main__":
    run_cli()
