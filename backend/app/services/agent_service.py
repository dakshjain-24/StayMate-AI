from langchain_core.messages import HumanMessage
from app.agent.graph import receptionist_graph


# GEMINI CONTENT EXTRACTION

def extract_text(content) -> str:

    # Normal text response
    if isinstance(content, str):
        return content

    # Content blocks
    if isinstance(content, list):
        parts = []

        for block in content:

            # Plain string block
            if isinstance(block, str):
                parts.append(block)

            # Structured Gemini block
            elif isinstance(block, dict):

                text = block.get("text")

                if text:
                    parts.append(text)

        return "\n".join(parts).strip()

    # Fallback
    return str(content)



# CHAT SERVICE

def chat_with_receptionist(message: str, thread_id: str, hotel_id: int) -> str:

    # Include active hotel information
    # inside each guest message.
    contextual_message = (
        f"Active hotel_id: {hotel_id}.\n" 
        f"Guest message: {message}"
    )

    result = receptionist_graph.invoke({
            "messages": [HumanMessage(content=contextual_message)]
        },
        config={
            "configurable": {
                "thread_id":thread_id
            }
        },
    )


    final_message = (result["messages"][-1])


    answer = extract_text(final_message.content)


    # Prevent blank chatbot bubbles.
    if not answer.strip():
        return (
            "I couldn't complete that response. "
            "Please try again."
        )

    return answer