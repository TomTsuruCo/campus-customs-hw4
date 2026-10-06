"""Validated request and response types shared by the API and shopping agent."""

from pydantic import BaseModel, ConfigDict, Field


class InventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    size: str
    quantity: int = Field(ge=0)


class ProductCard(BaseModel):
    """The safe product summary the agent can recommend to the storefront."""

    model_config = ConfigDict(extra="forbid")

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    image_url: str
    price: float = Field(ge=0)
    inventory: list[InventoryItem]
    total_stock: int = Field(ge=0)


class ProductDetails(BaseModel):
    """Authoritative catalogue facts used for description and price answers."""

    model_config = ConfigDict(extra="forbid")

    product_id: str
    name: str
    description: str
    price: float = Field(ge=0)


class StockLookup(BaseModel):
    """Authoritative size-level inventory result."""

    model_config = ConfigDict(extra="forbid")

    product_id: str
    name: str
    requested_size: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    available: bool | None = None
    inventory: list[InventoryItem]


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class PageContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(max_length=500)
    page_type: str = Field(max_length=40)
    product_id: str | None = Field(default=None, max_length=200)


class CustomerContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int | None = None
    name: str | None = None
    email: str | None = None


class AgentContext(BaseModel):
    """Dependencies supplied to one agent run; never inferred by the model."""

    customer: CustomerContext
    page: PageContext | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    page_context: PageContext | None = None


class ChatReply(BaseModel):
    """Structured agent output rendered by the chat widget."""

    model_config = ConfigDict(extra="forbid")

    reply: str = Field(min_length=1)
    products: list[ProductCard] = Field(default_factory=list, max_length=6)
    follow_up_suggestions: list[str] = Field(default_factory=list, max_length=4)


class ChatHistoryItem(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str
    products: list[ProductCard] = Field(default_factory=list, max_length=6)
    created_at: str
