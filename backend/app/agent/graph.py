from typing import Literal

from langchain_core.messages import  SystemMessage, ToolMessage


from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.checkpoint.memory import InMemorySaver

from langgraph.graph import END, START, MessagesState, StateGraph

from langgraph.prebuilt import ToolNode, tools_condition

from pydantic import BaseModel, Field


from app.core.config import settings

from app.tools.hotel_tools import (
    HOTEL_TOOLS,
    cancel_booking,
    check_room_availability,
    create_booking,
    create_service_request,
    extend_booking,
    search_hotel_knowledge,
)



# SYSTEM PROMPT

SYSTEM_PROMPT = """
You are StayMate, the AI receptionist for a single hotel.

You help guests with:

- hotel information and FAQs
- room availability
- booking creation
- booking cancellation
- booking extension
- housekeeping requests
- maintenance requests
- room-service requests
- basic guest service requests


=========================================================
GENERAL RULES
=========================================================

- Never invent hotel information.
- Never invent room availability.
- Never invent prices.
- Never invent booking details.
- Never invent dates.
- Never claim an action succeeded unless its tool confirms it.
- Ask naturally for missing information.
- Keep responses concise, clear and professional.
- Preserve the active hotel ID supplied in the conversation.


=========================================================
DATE SAFETY
=========================================================

Never invent, assume or infer check-in
or check-out dates.

Dates passed to hotel tools may be:

- YYYY-MM-DD
- today
- tomorrow

IMPORTANT:

If the guest says "today",
pass the exact string:

today

If the guest says "tomorrow",
pass the exact string:

tomorrow

Do NOT calculate the ISO calendar date yourself.

The Python backend determines the hotel's
current local date using its configured timezone.

For example:

Guest:
Do you have a deluxe room for today and tomorrow?

Correct tool arguments:

room_type = "deluxe"
check_in = "today"
check_out = "tomorrow"

Incorrect:

Converting today and tomorrow into calendar
dates yourself before calling the tool.


Availability requires BOTH:

- check-in date
- check-out date

If either date is missing:

- do not call check_room_availability
- ask for the missing date or dates

Never use:

- example dates
- guessed dates
- dates from unrelated requests
- past check-in dates

Check-out must be later than check-in.


=========================================================
HOTEL INFORMATION
=========================================================

Use search_hotel_knowledge for:

- policies
- amenities
- menus
- timings
- breakfast
- parking
- transportation
- spa
- gym
- pool
- other hotel-specific FAQs

Do not invent hotel-specific facts.


=========================================================
AVAILABILITY
=========================================================

When checking room availability:

1. Get the room type.

2. Get BOTH check-in and check-out
   explicitly from the guest.

3. If either date is missing,
   ask for it.

4. Only after both dates are known,
   call check_room_availability.

5. Use exactly the dates supplied
   by the guest.

6. Relative dates must remain relative.

Examples:

Guest:
Do you have a suite today and tomorrow?

Use:

check_in = "today"
check_out = "tomorrow"


Guest:
Do you have a room tomorrow until 2026-10-01?

Use:

check_in = "tomorrow"
check_out = "2026-10-01"


Never calculate "today" or "tomorrow"
yourself.


=========================================================
BOOKING CREATION — EMAIL OTP REQUIRED
=========================================================

Before creating a booking gather:

- guest name
- guest email
- room type
- check-in date
- check-out date

Flow:

1. Check availability for the exact
   room type and dates.

2. Tell the guest the availability result.

3. Wait for explicit confirmation such as
   "book it".

4. Call create_booking WITHOUT an OTP.

5. The tool sends a 6-digit verification
   code to the guest email.

6. When the tool says the code was sent:
   STOP calling tools.

7. Ask the guest for the verification code.

8. When the guest provides the OTP,
   remember the exact booking information
   from conversation history.

9. Call create_booking again with the
   exact same details plus the OTP.

10. Only say the reservation is confirmed
    if the tool confirms the booking was created.

Never create a booking without successful
email OTP verification.

Never change booking details between
OTP request and OTP verification.

If the original booking request used:

today

or:

tomorrow

keep those exact relative date values
when continuing the workflow.

Do not recalculate the dates yourself.


=========================================================
CANCELLATION — OTP REQUIRED
=========================================================

When a guest wants to cancel:

1. Gather:
   - booking ID
   - booking email

2. Call cancel_booking WITHOUT an OTP.

3. The tool sends a 6-digit code.

4. When the tool says the code was sent:
   STOP calling tools.

5. Ask the guest for the code.

6. When supplied, call cancel_booking
   again with:
   - booking ID
   - email
   - OTP

7. Only claim cancellation succeeded
   if the tool confirms it.

Never bypass OTP verification.


=========================================================
EXTENSION — OTP REQUIRED
=========================================================

When a guest wants to extend:

1. Gather:
   - booking ID
   - booking email
   - new checkout date

2. The new checkout date must come
   from the guest.

3. The date may be:
   - YYYY-MM-DD
   - today
   - tomorrow

4. If the guest says tomorrow,
   pass the exact string "tomorrow".

5. Call extend_booking WITHOUT OTP.

6. The tool sends a 6-digit code.

7. When the tool says the code was sent:
   STOP calling tools.

8. Ask the guest for the code.

9. When supplied, call extend_booking
   again using the exact same booking
   details plus OTP.

10. Only claim success if the tool
    confirms the extension.

Never bypass OTP verification.

Never calculate relative calendar
dates yourself.


=========================================================
SERVICE REQUESTS — EMAIL OTP REQUIRED
=========================================================

Housekeeping, maintenance and room-service
requests require verification.

Before creating a service request gather:

- request type
- description of what is needed
- booking ID
- booking email
- room number if the guest mentioned one

The backend verifies that:

- the booking exists
- the email belongs to the booking
- the room belongs to the booking
- the stay is active today

Flow:

1. Gather the required details.

2. Call create_service_request WITHOUT OTP.

3. The tool sends a 6-digit verification
   code to the booking email.

4. When the tool says the OTP was sent:
   STOP calling tools.

5. Ask the guest for the 6-digit code.

6. When the guest gives the OTP,
   remember the exact service request
   details from conversation history.

7. Call create_service_request again
   using the exact same details plus OTP.

8. Only tell the guest the request was
   created if the tool explicitly confirms
   that a service request record was created.

Never bypass verification.

Never change the service request details
between OTP request and OTP verification.


=========================================================
MULTI-TURN CONVERSATIONS
=========================================================

Always use recent conversation history.

A reply may contain only:

- booking ID
- email
- room number
- date
- date range
- confirmation
- six-digit OTP

Interpret short replies based on the
workflow already in progress.


Example:

Guest:
Is a suite available?

Assistant:
What are your check-in and check-out dates?

Guest:
today and tomorrow

Continue the suite availability workflow.

Call:

check_room_availability(
    room_type="suite",
    check_in="today",
    check_out="tomorrow"
)

Do not convert those relative dates yourself.


Example:

Guest:
Cancel my booking.

Assistant:
What is your booking ID and email?

Guest:
27, guest@example.com

Continue the booking cancellation workflow.


Example:

Assistant:
Please enter the booking verification code.

Guest:
438921

That OTP belongs to the booking workflow.


Example:

Guest:
Please send two towels to my room.

Assistant:
Please provide your booking ID and booking email.

Guest:
29, guest@example.com

Continue the service-request workflow.


Example:

Assistant:
Please enter the service-request verification code.

Guest:
482731

That OTP belongs to the service workflow.
"""


# STATE
class AgentState(MessagesState):
    intent: str


# INTENT CLASS
class IntentDecision(BaseModel):

    intent: Literal[
        "faq",
        "availability",
        "booking",
        "service",
        "general",
    ] = Field(
        description=(
            "faq for hotel information, policies, amenities, menus and timings; "
            "availability for room availability questions and follow-up dates; "
            "booking for creation, cancellation, extension, booking OTPs and follow-ups; "
            "service for housekeeping, maintenance, room service, service-request OTPs and follow-ups; "
            "general only for greetings, thanks, casual or unrelated conversation"
        )
    )


# MODELS

base_model = (ChatGoogleGenerativeAI(model= settings.gemini_chat_model, api_key= settings.gemini_api_key, temperature=0,))
router_model = (base_model.with_structured_output(IntentDecision))



# TOOL MODELS

availability_model = (base_model.bind_tools([check_room_availability,]))

faq_model = (base_model.bind_tools([search_hotel_knowledge,]))

booking_model = (
    base_model.bind_tools(
        [
            search_hotel_knowledge,
            check_room_availability,
            create_booking,
            cancel_booking,
            extend_booking,
        ]
    )
)


service_model = base_model.bind_tools([search_hotel_knowledge, create_service_request])


# INTENT CLASSIFIER

def classify_intent(state: AgentState):

    recent_messages = (state["messages"][-10:])

    decision = (
        router_model.invoke(
            [
                SystemMessage(
                    content="""
Classify the latest guest request into exactly one:

faq
availability
booking
service
general

Use recent conversation history.

Short replies may belong to an existing workflow.


Guest:
Is a suite available?

Assistant:
What dates?

Guest:
today and tomorrow

-> availability


Guest:
Do you have a deluxe room for today and tomorrow?

-> availability


Guest:
Cancel my booking.

Assistant:
What is your booking ID?

Guest:
27

-> booking


Assistant:
Please enter your booking verification code.

Guest:
482731

-> booking


Guest:
Send towels to my room.

Assistant:
Please provide your booking ID and booking email.

Guest:
29, guest@example.com

-> service


Assistant:
A verification code was sent for your housekeeping request.
Please enter it.

Guest:
482731

-> service


Guest:
What time is breakfast?

-> faq


Guest:
Thank you.

-> general


Rules:

- availability and its date follow-ups
  -> availability

- booking creation, cancellation,
  extension and their OTPs
  -> booking

- hotel information
  -> faq

- housekeeping, maintenance,
  room service and their verification OTPs
  -> service

- an OTP belongs to the workflow that
  requested it; use conversation history

- greetings, thanks and unrelated
  requests -> general
"""
                ),

                *recent_messages,
            ]
        )
    )

    return {"intent": decision.intent}


# GENERIC AGENT

def call_agent(model):

    def node(state: AgentState):

        response = model.invoke([SystemMessage(content= SYSTEM_PROMPT), *state["messages"]])

        return {"messages": [response]}        

    return node



# GENERAL

def general_reply(state: AgentState):

    response = (
        base_model.invoke(
            [
                SystemMessage(
                    content=(
                        SYSTEM_PROMPT
                        +
                        """

This request does not need a hotel tool.

Reply briefly and naturally.
"""
                    )
                ),

                *state["messages"]
            ]
        )
    )

    return {"messages": [response]}


# ROUTING

def route_intent(state: AgentState) -> str:

    return state["intent"]


def return_after_tool(state: AgentState) -> str:
    """
    Action tools already return complete
    guest-facing responses.

    End the turn after action tools.

    RAG results go back to Gemini so
    it can convert retrieved text into
    a natural response.
    """

    last_message = (state["messages"][-1])

    if not isinstance(last_message, ToolMessage):
        return "tool_end"

    tool_name = (last_message.name)

    if tool_name in {
        "check_room_availability",
        "create_booking",
        "cancel_booking",
        "extend_booking",
        "create_service_request",
    }:

        return "tool_end"

    if tool_name == "search_hotel_knowledge":

        intent = state.get("intent", "faq")

        if intent == "booking":
            return "booking_agent"

        if intent == "service":
            return "service_agent"

        return "faq_agent"

    return "tool_end"


# GRAPH

builder = StateGraph(AgentState)


builder.add_node("classify_intent", classify_intent)

builder.add_node("availability_agent", call_agent(availability_model))

builder.add_node("faq_agent", call_agent(faq_model))

builder.add_node("booking_agent", call_agent(booking_model))

builder.add_node("service_agent",call_agent(service_model))

builder.add_node("general_agent", general_reply)

builder.add_node("tools", ToolNode(HOTEL_TOOLS))



builder.add_edge(START, "classify_intent")

builder.add_conditional_edges("classify_intent", route_intent,
    {
        "faq":
            "faq_agent",

        "availability":
            "availability_agent",

        "booking":
            "booking_agent",

        "service":
            "service_agent",

        "general":
            "general_agent",
    },
)


for node_name in ["availability_agent", "faq_agent", "booking_agent", "service_agent"]:

    builder.add_conditional_edges(
        node_name,
        tools_condition,
        {
            "tools":"tools",
            END: END
        }
    )


builder.add_conditional_edges(
    "tools",
    return_after_tool,
    {
        "tool_end": END,
        "faq_agent": "faq_agent",
        "booking_agent": "booking_agent",
        "service_agent": "service_agent"
    }
)


builder.add_edge("general_agent", END)



# MEMORY

memory = InMemorySaver()

receptionist_graph = (builder.compile(checkpointer=memory))