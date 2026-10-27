"""LLM access: Amazon Bedrock if configured, otherwise a local mock so demos never break."""
import os

from dotenv import load_dotenv

load_dotenv()

PROMPT = (
    "You are a helpful assistant. Answer the question using ONLY the context below. "
    "If sources conflict, trust [DB] over [DOCS] over [MEMORY]. "
    "If the answer is not in the context, say you don't know.\n\n"
    "CONTEXT:\n{context}\n\nQUESTION: {question}\nANSWER:"
)


def _mock_llm(question: str, context: str) -> str:
    if not context.strip():
        return "I don't have any relevant information for that question."
    return ("[MOCK LLM - Bedrock not enabled] Based on the retrieved context:\n"
            f"{context}\n(Set USE_BEDROCK=true in .env to get a real generated answer.)")


def generate_answer(question: str, context: str) -> tuple[str, str]:
    """Returns (answer, which_llm_was_used)."""
    if os.getenv("USE_BEDROCK", "false").lower() != "true":
        return _mock_llm(question, context), "mock"
    try:
        from langchain_aws import ChatBedrockConverse

        model = ChatBedrockConverse(
            model=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            temperature=0.2,
            max_tokens=500,
        )
        reply = model.invoke(PROMPT.format(context=context, question=question))
        return reply.content if isinstance(reply.content, str) else str(reply.content), "bedrock"
    except Exception as e:  # missing credentials, no model access, no internet...
        print(f"[llm] Bedrock failed ({type(e).__name__}: {e}) -> using mock LLM")
        return _mock_llm(question, context), "mock (bedrock failed)"
