"""Catalogue tools available to the Campus Customs shopping agent."""

from __future__ import annotations

import json
import re
import sqlite3
from functools import lru_cache
from pathlib import Path

from models import InventoryItem, ProductCard, ProductDetails, StockLookup


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "campus_customs.db"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _list(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _product(row: sqlite3.Row, connection: sqlite3.Connection) -> ProductCard:
    inventory = [
        InventoryItem(size=item["size"], quantity=item["quantity"])
        for item in connection.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
            (row["product_id"],),
        ).fetchall()
    ]
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=_list(row["colors"]),
        image_url=f"/media/products_white/{Path(row['image_file_path']).name}",
        price=row["price"],
        inventory=inventory,
        total_stock=sum(item.quantity for item in inventory),
    )


@lru_cache(maxsize=1)
def _catalogue_index() -> tuple[dict[str, object], ...]:
    """Cache stable catalogue text for fast ranking; inventory stays live."""
    connection = _connection()
    try:
        rows = connection.execute("SELECT * FROM catalogue").fetchall()
        indexed: list[dict[str, object]] = []
        for row in rows:
            indexed.append({
                key: row[key] for key in row.keys()
            })
        return tuple(indexed)
    finally:
        connection.close()


def _query_variants(token: str) -> set[str]:
    variants = {token}
    if token.endswith("ies") and len(token) > 4:
        variants.add(token[:-3] + "y")
        variants.add(token[:-1])
    elif token.endswith("s") and len(token) > 3:
        variants.add(token[:-1])
    return variants


def search_catalogue(query: str, limit: int = 6) -> list[ProductCard]:
    """Search official product data with normalized, relevance-ranked matching."""
    query = query.strip().lower()
    tokens = re.findall(r"[a-z0-9]+", query)
    if not tokens:
        return []
    variants = [sorted(_query_variants(token)) for token in tokens]
    ranked: list[tuple[int, dict[str, object]]] = []
    phrase = " ".join(tokens)
    for row in _catalogue_index():
        name = str(row["name"]).lower()
        garment = str(row["garment_type"]).lower()
        description = str(row["description"]).lower()
        colors = str(row["colors"]).lower()
        tags = str(row["search_tags"]).lower()
        searchable = " ".join([name, garment, description, colors, tags])
        score = 0
        matched = 0
        for options in variants:
            if any(option in searchable for option in options):
                matched += 1
                if any(option in name for option in options): score += 25
                elif any(option in garment for option in options): score += 18
                elif any(option in tags for option in options): score += 10
                else: score += 4
        if matched == 0:
            continue
        if phrase in name: score += 50
        if matched == len(tokens): score += 20
        ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], str(item[1]["name"])))
    selected = [row for _, row in ranked[: min(max(limit, 1), 6)]]
    connection = _connection()
    try:
        return [_product(row, connection) for row in selected]
    finally:
        connection.close()


def get_product(product_id: str) -> ProductCard | None:
    """Get one exact catalogue product, including its current size inventory."""
    connection = _connection()
    try:
        row = connection.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        return _product(row, connection) if row else None
    finally:
        connection.close()


def _find_product(connection: sqlite3.Connection, identifier: str) -> sqlite3.Row | None:
    """Resolve an exact ID/name first, then a single unambiguous partial match."""
    identifier = identifier.strip()
    row = connection.execute(
        "SELECT * FROM catalogue WHERE product_id = ? OR lower(name) = lower(?)",
        (identifier, identifier),
    ).fetchone()
    if row:
        return row
    matches = connection.execute(
        "SELECT * FROM catalogue WHERE name LIKE ? ORDER BY name LIMIT 2",
        (f"%{identifier}%",),
    ).fetchall()
    return matches[0] if len(matches) == 1 else None


def lookup_product_details(identifier: str) -> ProductDetails | None:
    """Look up the official description and price for one catalogue product."""
    connection = _connection()
    try:
        row = _find_product(connection, identifier)
        if not row:
            return None
        return ProductDetails(
            product_id=row["product_id"],
            name=row["name"],
            description=row["description"],
            price=row["price"],
        )
    finally:
        connection.close()


def lookup_product_price(identifier: str) -> ProductDetails | None:
    """Look up the official current price for one catalogue product."""
    return lookup_product_details(identifier)


def lookup_stock(identifier: str, size: str | None = None) -> StockLookup | None:
    """Look up current stock for every size or one requested size."""
    connection = _connection()
    try:
        row = _find_product(connection, identifier)
        if not row:
            return None
        inventory = [
            InventoryItem(size=item["size"], quantity=item["quantity"])
            for item in connection.execute(
                "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
                (row["product_id"],),
            ).fetchall()
        ]
        if size is None:
            return StockLookup(product_id=row["product_id"], name=row["name"], inventory=inventory)
        requested = size.strip().upper()
        match = next((item for item in inventory if item.size.upper() == requested), None)
        return StockLookup(
            product_id=row["product_id"], name=row["name"], requested_size=size,
            quantity=match.quantity if match else 0,
            available=bool(match and match.quantity > 0), inventory=inventory,
        )
    finally:
        connection.close()
