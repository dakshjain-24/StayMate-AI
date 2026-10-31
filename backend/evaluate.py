import json
import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai.chat_models import GoogleRateLimitError

from app.agent.graph import (
    IntentDecision,
    availability_model,
    booking_model,
    faq_model,
    router_model,
    service_model,
)
from app.db.session import SessionLocal
from app.services.rag_service import search_knowledge


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evaluation" / "cases.json"

MODEL_DELAY = 4.5
RATE_LIMIT_WAIT = 45


ROUTER_PROMPT = (
    "Classify the guest's latest request into exactly one hotel workflow. "
    "If the guest asks whether a room or room type is available for "
    "certain dates, always classify it as availability."
)


TOOL_SYSTEM_PROMPT = """
You are StayMate, an AI hotel receptionist.

Use the appropriate hotel tool whenever the guest request requires
hotel data or an action.

Never invent availability, policies, booking information,
or service request results.
"""


def safe_invoke(model, messages):
    """
    Invoke Gemini while respecting free-tier rate limits.

    If Gemini returns a rate-limit error, wait and retry.
    """

    while True:
        try:
            response = model.invoke(messages)

            # Prevent bursting through the free-tier request limit.
            time.sleep(MODEL_DELAY)

            return response

        except GoogleRateLimitError:
            print(
                f"\nRate limit reached. "
                f"Waiting {RATE_LIMIT_WAIT} seconds before retrying..."
            )

            time.sleep(RATE_LIMIT_WAIT)


def percentage(
    correct: int,
    total: int,
) -> float:
    if total == 0:
        return 0.0

    return correct / total * 100


def average(
    values: list[float],
) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


# =========================================================
# INTENT ROUTING EVALUATION
# =========================================================

def evaluate_intents(
    cases: list[dict],
) -> tuple[int, int, list[float]]:

    correct = 0
    latencies = []

    for index, case in enumerate(
        cases,
        start=1,
    ):

        print(
            f"\nIntent case {index}/{len(cases)}"
        )

        start = time.perf_counter()

        decision: IntentDecision = safe_invoke(
            router_model,
            [
                SystemMessage(
                    content=ROUTER_PROMPT
                ),
                HumanMessage(
                    content=case["query"]
                ),
            ],
        )

        elapsed = (
            time.perf_counter()
            - start
        )

        latencies.append(elapsed)

        passed = (
            decision.intent
            == case["expected"]
        )

        correct += int(passed)

        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{case['query']}"
        )

        print(
            f"       expected={case['expected']} "
            f"actual={decision.intent} "
            f"latency={elapsed:.2f}s"
        )

    return (
        correct,
        len(cases),
        latencies,
    )


# =========================================================
# RAG RETRIEVAL EVALUATION
# =========================================================

def evaluate_rag(
    cases: list[dict],
) -> tuple[int, int, list[float]]:

    correct = 0
    latencies = []

    with SessionLocal() as db:

        for index, case in enumerate(
            cases,
            start=1,
        ):

            print(
                f"\nRAG case {index}/{len(cases)}"
            )

            start = time.perf_counter()

            results = search_knowledge(
                db,
                case["query"],
                hotel_id=1,
                limit=3,
            )

            elapsed = (
                time.perf_counter()
                - start
            )

            latencies.append(elapsed)

            retrieved_sources = {
                row.source
                for row in results
            }

            # Supports:
            #
            # "expected_source": "hotel_faq.md"
            #
            # OR:
            #
            # "expected_sources": [
            #     "hotel_faq.md",
            #     "room_service.md"
            # ]

            if "expected_sources" in case:
                expected_sources = (
                    case["expected_sources"]
                )

            else:
                expected_sources = [
                    case["expected_source"]
                ]

            expected_sources = [
                source
                for source in expected_sources
                if source
            ]

            # Pass if at least one valid expected source
            # appears in the top-3 retrieval results.
            passed = bool(
                set(expected_sources)
                & retrieved_sources
            )

            correct += int(passed)

            print(
                f"[{'PASS' if passed else 'FAIL'}] "
                f"{case['query']}"
            )

            print(
                f"       expected="
                f"{expected_sources}"
            )

            print(
                f"       retrieved="
                f"{sorted(retrieved_sources)}"
            )

            print(
                f"       latency="
                f"{elapsed:.2f}s"
            )

    return (
        correct,
        len(cases),
        latencies,
    )


# =========================================================
# TOOL ROUTING EVALUATION
# =========================================================

def get_model_for_workflow(
    workflow: str,
):
    if workflow == "availability":
        return availability_model

    if workflow == "booking":
        return booking_model

    if workflow == "service":
        return service_model

    if workflow == "faq":
        return faq_model

    raise ValueError(
        f"Unknown workflow: {workflow}"
    )


def evaluate_tools(
    cases: list[dict],
) -> tuple[int, int, list[float]]:

    correct = 0
    latencies = []

    for index, case in enumerate(
        cases,
        start=1,
    ):

        print(
            f"\nTool case {index}/{len(cases)}"
        )

        model = get_model_for_workflow(
            case["workflow"]
        )

        start = time.perf_counter()

        response = safe_invoke(
            model,
            [
                SystemMessage(
                    content=TOOL_SYSTEM_PROMPT
                ),
                HumanMessage(
                    content=case["query"]
                ),
            ],
        )

        elapsed = (
            time.perf_counter()
            - start
        )

        latencies.append(elapsed)

        tool_calls = getattr(
            response,
            "tool_calls",
            [],
        )

        selected_tools = [
            call.get("name")
            for call in tool_calls
        ]

        passed = (
            case["expected_tool"]
            in selected_tools
        )

        correct += int(passed)

        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{case['query']}"
        )

        print(
            f"       expected="
            f"{case['expected_tool']}"
        )

        print(
            f"       selected="
            f"{selected_tools}"
        )

        print(
            f"       latency="
            f"{elapsed:.2f}s"
        )

    return (
        correct,
        len(cases),
        latencies,
    )


# =========================================================
# SUMMARY HELPERS
# =========================================================

def print_section_result(
    name: str,
    correct: int,
    total: int,
    latencies: list[float],
):

    print(
        f"{name}: "
        f"{correct}/{total} "
        f"({percentage(correct, total):.1f}%)"
    )

    print(
        f"{name} average latency: "
        f"{average(latencies):.2f}s"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    cases = json.loads(
        CASES_PATH.read_text(
            encoding="utf-8"
        )
    )

    print()
    print("=" * 60)
    print("STAYMATE AI EVALUATION")
    print("=" * 60)

    # -----------------------------------------------------
    # Intent routing
    # -----------------------------------------------------

    print("\n1. INTENT ROUTING")

    (
        intent_correct,
        intent_total,
        intent_latency,
    ) = evaluate_intents(
        cases["intent_cases"]
    )

    # -----------------------------------------------------
    # RAG retrieval
    # -----------------------------------------------------

    print("\n2. RAG SOURCE HIT RATE @3")

    (
        rag_correct,
        rag_total,
        rag_latency,
    ) = evaluate_rag(
        cases["rag_cases"]
    )

    # -----------------------------------------------------
    # First-step tool routing
    # -----------------------------------------------------

    print("\n3. FIRST-STEP TOOL ROUTING")

    (
        tool_correct,
        tool_total,
        tool_latency,
    ) = evaluate_tools(
        cases["tool_cases"]
    )

    # -----------------------------------------------------
    # Overall metrics
    # -----------------------------------------------------

    total_correct = (
        intent_correct
        + rag_correct
        + tool_correct
    )

    total_cases = (
        intent_total
        + rag_total
        + tool_total
    )

    all_latencies = (
        intent_latency
        + rag_latency
        + tool_latency
    )

    # -----------------------------------------------------
    # Final summary
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print_section_result(
        "Intent routing accuracy",
        intent_correct,
        intent_total,
        intent_latency,
    )

    print()

    print_section_result(
        "RAG source hit rate @3",
        rag_correct,
        rag_total,
        rag_latency,
    )

    print()

    print_section_result(
        "First-step Tool-selection accuracy",
        tool_correct,
        tool_total,
        tool_latency,
    )

    print()

    print(
        f"Overall evaluation score: "
        f"{total_correct}/{total_cases} "
        f"({percentage(total_correct, total_cases):.1f}%)"
    )

    print(
        f"Overall average latency: "
        f"{average(all_latencies):.2f}s"
    )

    print(
        f"Total evaluated cases: "
        f"{total_cases}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()