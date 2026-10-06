"""Pydantic AI agent wiring for the Campus Customs shopping assistant."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import AgentContext, ChatReply, CustomerContext, PageContext, ProductCard, ProductDetails, StockLookup
from audit import append_event
from tools import (
    get_product,
    lookup_product_details,
    lookup_product_price,
    lookup_stock,
    search_catalogue,
)


ROOT = Path(__file__).resolve().parent
PROMPT_PATH = ROOT / "prompts" / "prompt.md"


def model() -> OpenAIChatModel:
    """Build the Portkey-compatible OpenAI model only when a chat request arrives."""
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parent / ".env")
    api_key = os.getenv("PORTKEY_API_KEY") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set PORTKEY_API_KEY in the environment before using chat.")
    provider = OpenAIProvider(
        api_key=api_key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
    )
    return OpenAIChatModel(os.getenv("PORTKEY_MODEL", "gpt-5.6-luna"), provider=provider)


MAX_MODEL_REQUESTS = 6
MAX_TOOL_CALLS = 8


def _result_summary(value: object) -> object:
    if value is None:
        return {"match": False}
    if isinstance(value, CustomerContext):
        return {
            "customer_context_returned": True,
            "name_supplied": value.name is not None,
            "email_supplied": value.email is not None,
        }
    if isinstance(value, PageContext):
        return {"page_type": value.page_type, "product_id": value.product_id}
    if isinstance(value, ProductCard):
        return {
            "product_id": value.product_id,
            "name": value.name,
            "price": value.price,
            "total_stock": value.total_stock,
        }
    if isinstance(value, ProductDetails):
        return {"product_id": value.product_id, "name": value.name, "price": value.price}
    if isinstance(value, StockLookup):
        return {
            "product_id": value.product_id,
            "name": value.name,
            "requested_size": value.requested_size,
            "quantity": value.quantity,
            "available": value.available,
            "size_count": len(value.inventory),
        }
    if isinstance(value, list):
        return {"count": len(value), "items": [_result_summary(item) for item in value[:3]]}
    return {"returned": True}


def _audited_tool(run_id: str, name: str, args: dict[str, object], operation):
    try:
        result = operation()
    except Exception as error:
        append_event(
            run_id=run_id,
            event="tool",
            tool_name=name,
            args=args,
            result={"error_type": type(error).__name__},
            stop_reason="tool_error",
        )
        raise
    append_event(
        run_id=run_id,
        event="tool",
        tool_name=name,
        args=args,
        result=_result_summary(result),
        stop_reason="tool_returned",
    )
    return result


def build_agent(run_id: str) -> Agent[AgentContext, ChatReply]:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    agent: Agent[AgentContext, ChatReply] = Agent(
        model(), output_type=ChatReply, system_prompt=prompt, retries=2
    )

    @agent.tool
    def shopper_context(ctx: RunContext[AgentContext]) -> CustomerContext:
        """Return the explicitly supplied customer identity for this chat turn."""
        return _audited_tool(run_id, "shopper_context", {}, lambda: ctx.deps.customer)

    @agent.tool
    def current_page_context(ctx: RunContext[AgentContext]) -> PageContext | None:
        """Return the page and product context supplied by the website."""
        return _audited_tool(run_id, "current_page_context", {}, lambda: ctx.deps.page)

    @agent.tool_plain
    def search_products(query: str, limit: int = 6) -> list[ProductCard]:
        """Search Campus Customs products and current size inventory."""
        return _audited_tool(
            run_id, "search_products", {"query": query, "limit": limit},
            lambda: search_catalogue(query, limit),
        )

    @agent.tool_plain
    def product_details(product_id: str) -> ProductCard | None:
        """Look up one exact product by its catalogue ID."""
        return _audited_tool(
            run_id, "product_details", {"product_id": product_id},
            lambda: get_product(product_id),
        )

    @agent.tool_plain
    def product_description_and_price(identifier: str) -> ProductDetails | None:
        """Look up the catalogue description and official price; never estimate either."""
        return _audited_tool(
            run_id, "product_description_and_price", {"identifier": identifier},
            lambda: lookup_product_details(identifier),
        )

    @agent.tool_plain
    def product_price(identifier: str) -> ProductDetails | None:
        """Look up the official catalogue price for a product; never invent a price."""
        return _audited_tool(
            run_id, "product_price", {"identifier": identifier},
            lambda: lookup_product_price(identifier),
        )

    @agent.tool_plain
    def product_stock(identifier: str, size: str | None = None) -> StockLookup | None:
        """Look up current stock by size; quantity zero means clearly out of stock."""
        return _audited_tool(
            run_id, "product_stock", {"identifier": identifier, "size": size},
            lambda: lookup_stock(identifier, size),
        )

    return agent


async def run_chat(
    message: str,
    history: list[dict[str, str]] | None = None,
    deps: AgentContext | None = None,
) -> ChatReply:
    run_id = uuid.uuid4().hex
    deps = deps or AgentContext(customer=CustomerContext())
    append_event(
        run_id=run_id,
        event="run_started",
        tool_name="agent_run",
        args={
            "message_characters": len(message),
            "history_turns": len(history or []),
            "page_type": deps.page.page_type if deps.page else None,
        },
        result=None,
        stop_reason=None,
    )
    try:
        agent = build_agent(run_id)
        context = ""
        if history:
            context = "\nPrevious conversation (use only as context):\n" + "\n".join(
                f"{item['role']}: {item['content']}" for item in history[-20:]
            )
        result = await agent.run(
            message + context,
            deps=deps,
            usage_limits=UsageLimits(
                request_limit=MAX_MODEL_REQUESTS,
                tool_calls_limit=MAX_TOOL_CALLS,
            ),
        )
        output = result.output
        # The model chooses which IDs to recommend, but the website receives only
        # canonical product data read again from SQLite.
        canonical_products = []
        for product in output.products:
            canonical = get_product(product.product_id)
            if canonical is not None:
                canonical_products.append(canonical)
        reply = output.model_copy(update={"products": canonical_products})
    except Exception as error:
        stop_reason = (
            "usage_limit_exceeded"
            if type(error).__name__ == "UsageLimitExceeded"
            else "agent_error"
        )
        append_event(
            run_id=run_id,
            event="run_stopped",
            tool_name="agent_run",
            args={},
            result={"error_type": type(error).__name__},
            stop_reason=stop_reason,
        )
        raise

    append_event(
        run_id=run_id,
        event="run_stopped",
        tool_name="agent_run",
        args={},
        result={
            "reply_characters": len(reply.reply),
            "product_ids": [product.product_id for product in reply.products],
        },
        stop_reason="final_output",
    )
    return reply
