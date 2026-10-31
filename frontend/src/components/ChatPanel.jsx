import {
  Bot,
  CalendarCheck,
  CheckCircle2,
  CircleX,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  User,
  Wrench,
} from "lucide-react";

import {
  useState,
} from "react";

import {
  api,
} from "../services/api";


const starterMessages = [
  {
    role: "assistant",
    text:
      "Hi, I’m StayMate. I can help with rooms, bookings, hotel information, housekeeping, and maintenance requests.",
  },
];


const suggestions = [
  {
    label: "Check room availability",
    message:
      "Do you have a deluxe room from 2026-10-04 to 2026-10-07?",
  },

  {
    label: "Breakfast timings",
    message:
      "What time does breakfast end?",
  },

  {
    label: "Request housekeeping",
    message:
      "Please send two extra towels to my room.",
  },
];


function detectResponseType(text) {
  const value =
    text.toLowerCase();


  // =====================================================
  // SERVICE REQUEST OTP
  // =====================================================

  // Must come before the generic OTP detector.
  if (
    value.includes(
      "verification code"
    )
    &&
    (
      value.includes(
        "service request"
      )
      ||
      value.includes(
        "service-request"
      )
      ||
      value.includes(
        "housekeeping"
      )
      ||
      value.includes(
        "maintenance"
      )
      ||
      value.includes(
        "room service"
      )
      ||
      value.includes(
        "room_service"
      )
    )
    &&
    (
      value.includes(
        "has been sent"
      )
      ||
      value.includes(
        "enter the verification code"
      )
    )
  ) {
    return "service_verification";
  }


  // =====================================================
  // BOOKING / RESERVATION OTP
  // =====================================================

  if (
    value.includes(
      "verification code"
    )
    &&
    (
      value.includes(
        "has been sent"
      )
      ||
      value.includes(
        "code has been sent"
      )
      ||
      value.includes(
        "enter the verification code"
      )
      ||
      value.includes(
        "enter the code"
      )
    )
  ) {
    return "verification";
  }


  // =====================================================
  // BOOKING SUCCESS
  // =====================================================

  if (
    value.includes(
      "booking confirmed"
    )
  ) {
    return "booking";
  }


  // =====================================================
  // CANCELLATION SUCCESS
  // =====================================================

  if (
    value.includes("cancel")
    &&
    (
      value.includes("booking")
      ||
      value.includes("reservation")
    )
    &&
    (
      value.includes("success")
      ||
      value.includes("cancelled")
      ||
      value.includes("canceled")
    )
  ) {
    return "cancelled";
  }


  // =====================================================
  // EXTENSION SUCCESS
  // =====================================================

  if (
    value.includes(
      "booking"
    )
    &&
    (
      value.includes(
        "has been extended"
      )
      ||
      value.includes(
        "extended until"
      )
    )
  ) {
    return "extended";
  }


  // =====================================================
  // SERVICE REQUEST SUCCESS
  // =====================================================

  // Be strict here.
  //
  // Do NOT classify:
  // "Service requests can only be created..."
  //
  // as a successful request.

  if (
    value.includes(
      "service request #"
    )
    &&
    value.includes(
      "was created"
    )
    &&
    value.includes(
      "sent to the hotel staff"
    )
  ) {
    return "service";
  }


  return "normal";
}


function extractBookingId(text) {
  const match =
    text.match(
      /booking\s+(?:id\s*:?\s*)?#?(\d+)/i
    );

  return match
    ? match[1]
    : null;
}


function extractAmount(text) {
  const match =
    text.match(
      /₹\s?([\d,]+)/i
    );

  return match
    ? `₹${match[1]}`
    : null;
}


function extractServiceRequestId(text) {
  const match =
    text.match(
      /service\s+request\s+#(\d+)/i
    );

  return match
    ? match[1]
    : null;
}


function AssistantResponse({
  text,
}) {
  const type =
    detectResponseType(
      text
    );

  const bookingId =
    extractBookingId(
      text
    );

  const amount =
    extractAmount(
      text
    );

  const requestId =
    extractServiceRequestId(
      text
    );


  // =====================================================
  // NORMAL MESSAGE
  // =====================================================

  if (
    type === "normal"
  ) {
    return (
      <div className="bubble">
        {text}
      </div>
    );
  }


  // =====================================================
  // SERVICE REQUEST VERIFICATION
  // =====================================================

  if (
    type === "service_verification"
  ) {
    return (
      <div className="response-card service-response verification-response">

        <div className="response-card-header">

          <div className="response-icon service-icon">
            <ShieldCheck
              size={19}
            />
          </div>

          <div>

            <span className="response-label">
              Hotel Service
            </span>

            <h4>
              Verification Required
            </h4>

          </div>

        </div>


        {
          bookingId && (
            <div className="response-card-details">

              <div>

                <span>
                  Booking ID
                </span>

                <strong>
                  #{bookingId}
                </strong>

              </div>

            </div>
          )
        }


        <p className="response-card-text">
          {text}
        </p>

      </div>
    );
  }


  // =====================================================
  // RESERVATION VERIFICATION
  // =====================================================

  if (
    type === "verification"
  ) {
    return (
      <div className="response-card booking-response verification-response">

        <div className="response-card-header">

          <div className="response-icon booking-icon">

            <ShieldCheck
              size={19}
            />

          </div>


          <div>

            <span className="response-label">
              Reservation Security
            </span>

            <h4>
              Verification Required
            </h4>

          </div>

        </div>


        {
          bookingId && (
            <div className="response-card-details">

              <div>

                <span>
                  Booking ID
                </span>

                <strong>
                  #{bookingId}
                </strong>

              </div>

            </div>
          )
        }


        <p className="response-card-text">
          {text}
        </p>

      </div>
    );
  }


  // =====================================================
  // BOOKING CREATED
  // =====================================================

  if (
    type === "booking"
  ) {
    return (
      <div className="response-card booking-response">

        <div className="response-card-header">

          <div className="response-icon booking-icon">

            <CalendarCheck
              size={19}
            />

          </div>


          <div>

            <span className="response-label">
              Reservation
            </span>

            <h4>
              Booking Confirmed
            </h4>

          </div>


          <CheckCircle2
            size={20}
            className="response-success-icon"
          />

        </div>


        <div className="response-card-details">

          {
            bookingId && (

              <div>

                <span>
                  Booking ID
                </span>

                <strong>
                  #{bookingId}
                </strong>

              </div>

            )
          }


          {
            amount && (

              <div>

                <span>
                  Total
                </span>

                <strong>
                  {amount}
                </strong>

              </div>

            )
          }

        </div>


        <p className="response-card-text">
          {text}
        </p>

      </div>
    );
  }


  // =====================================================
  // BOOKING CANCELLED
  // =====================================================

  if (
    type === "cancelled"
  ) {
    return (
      <div className="response-card cancelled-response">

        <div className="response-card-header">

          <div className="response-icon cancelled-icon">

            <CircleX
              size={19}
            />

          </div>


          <div>

            <span className="response-label">
              Reservation
            </span>

            <h4>
              Booking Cancelled
            </h4>

          </div>


          <CheckCircle2
            size={20}
            className="response-success-icon"
          />

        </div>


        {
          bookingId && (

            <div className="response-card-details">

              <div>

                <span>
                  Booking ID
                </span>

                <strong>
                  #{bookingId}
                </strong>

              </div>

            </div>

          )
        }


        <p className="response-card-text">
          {text}
        </p>

      </div>
    );
  }


  // =====================================================
  // BOOKING EXTENDED
  // =====================================================

  if (
    type === "extended"
  ) {
    return (
      <div className="response-card extended-response">

        <div className="response-card-header">

          <div className="response-icon extended-icon">

            <CalendarCheck
              size={19}
            />

          </div>


          <div>

            <span className="response-label">
              Reservation
            </span>

            <h4>
              Stay Extended
            </h4>

          </div>


          <CheckCircle2
            size={20}
            className="response-success-icon"
          />

        </div>


        <div className="response-card-details">

          {
            bookingId && (

              <div>

                <span>
                  Booking ID
                </span>

                <strong>
                  #{bookingId}
                </strong>

              </div>

            )
          }


          {
            amount && (

              <div>

                <span>
                  Updated Total
                </span>

                <strong>
                  {amount}
                </strong>

              </div>

            )
          }

        </div>


        <p className="response-card-text">
          {text}
        </p>

      </div>
    );
  }


  // =====================================================
  // SERVICE REQUEST CREATED
  // =====================================================

  if (
    type === "service"
  ) {
    return (
      <div className="response-card service-response">

        <div className="response-card-header">

          <div className="response-icon service-icon">

            <Wrench
              size={19}
            />

          </div>


          <div>

            <span className="response-label">
              Hotel Service
            </span>

            <h4>
              Request Created
            </h4>

          </div>


          <CheckCircle2
            size={20}
            className="response-success-icon"
          />

        </div>


        {
          requestId && (

            <div className="response-card-details">

              <div>

                <span>
                  Request ID
                </span>

                <strong>
                  #{requestId}
                </strong>

              </div>

            </div>

          )
        }


        <p className="response-card-text">
          {text}
        </p>

      </div>
    );
  }


  return (
    <div className="bubble">
      {text}
    </div>
  );
}


export default function ChatPanel() {

  const [
    messages,
    setMessages,
  ] = useState(
    starterMessages
  );


  const [
    input,
    setInput,
  ] = useState("");


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    threadId,
    setThreadId,
  ] = useState(
    () =>
      crypto.randomUUID()
  );


  async function sendMessage(
    event
  ) {

    event.preventDefault();


    const text =
      input.trim();


    if (
      !text
      ||
      loading
    ) {
      return;
    }


    setMessages(
      (current) => [
        ...current,

        {
          role: "user",
          text,
        },
      ]
    );


    setInput("");

    setLoading(true);


    try {

      const response =
        await api.chat(
          text,
          threadId
        );


      setMessages(
        (current) => [
          ...current,

          {
            role:
              "assistant",

            text:
              response.answer,
          },
        ]
      );

    } catch (error) {

      setMessages(
        (current) => [
          ...current,

          {
            role:
              "assistant",

            text:
              `I couldn't complete that request: ${error.message}`,
          },
        ]
      );

    } finally {

      setLoading(false);

    }
  }


  function chooseSuggestion(
    suggestion
  ) {

    setInput(
      suggestion.message
    );
  }


  function startNewChat() {

    setMessages(
      starterMessages
    );

    setInput("");

    setLoading(false);

    setThreadId(
      crypto.randomUUID()
    );
  }


  return (

    <section className="panel chat-panel">

      {/* HEADER */}

      <div className="chat-header">

        <div>

          <span className="eyebrow">
            Guest assistant
          </span>

          <h2>
            Front Desk Chat
          </h2>

          <p className="chat-subtitle">
            Ask StayMate to manage your stay or answer hotel questions.
          </p>

        </div>


        <div className="chat-header-actions">

          <span className="status-pill">
            Online
          </span>


          <button
            type="button"
            className="new-chat-button"
            onClick={
              startNewChat
            }
          >

            <Plus
              size={15}
            />

            New Chat

          </button>

        </div>

      </div>


      {/* QUICK ACTIONS */}

      <div className="chat-suggestions">

        {
          suggestions.map(
            (suggestion) => (

              <button
                type="button"
                key={
                  suggestion.label
                }
                onClick={
                  () =>
                    chooseSuggestion(
                      suggestion
                    )
                }
              >

                <Sparkles
                  size={13}
                />

                {
                  suggestion.label
                }

              </button>

            )
          )
        }

      </div>


      {/* MESSAGES */}

      <div className="messages">

        {
          messages.map(
            (
              message,
              index
            ) => (

              <div
                className={
                  `message ${message.role}`
                }
                key={
                  `${message.role}-${index}`
                }
              >

                <div className="avatar">

                  {
                    message.role ===
                    "assistant"
                      ? (
                        <Bot
                          size={18}
                        />
                      )
                      : (
                        <User
                          size={18}
                        />
                      )
                  }

                </div>


                {
                  message.role ===
                  "assistant"
                    ? (

                      <AssistantResponse
                        text={
                          message.text
                        }
                      />

                    )
                    : (

                      <div className="bubble">
                        {
                          message.text
                        }
                      </div>

                    )
                }

              </div>

            )
          )
        }


        {
          loading && (

            <div className="message assistant">

              <div className="avatar">

                <Bot
                  size={18}
                />

              </div>


              <div className="bubble typing">

                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />

              </div>

            </div>

          )
        }

      </div>


      {/* INPUT */}

      <form
        className="chat-form"
        onSubmit={
          sendMessage
        }
      >

        <input
          value={
            input
          }
          onChange={
            (event) =>
              setInput(
                event.target.value
              )
          }
          placeholder="Ask about rooms, bookings, hotel services..."
        />


        <button
          type="submit"
          disabled={
            loading
            ||
            !input.trim()
          }
          aria-label="Send message"
        >

          <Send
            size={18}
          />

        </button>

      </form>

    </section>

  );
}