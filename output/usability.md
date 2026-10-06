# HW4 Problem 9 - Usability improvements

This problem adds two frontend improvements and two agent/backend improvements. Each improvement is intentionally visible in the running app or affects the data returned by the chat API.

## Frontend improvement 1 - Quick catalogue filters and sorting

### What I added

The Products page will have one-click category filters for All, Hoodies, Crewnecks, T-shirts, and Jackets, plus a sort control for featured order, name, price low-to-high, and price high-to-low.

### Why it helps

A shopper can narrow a large catalogue without having to guess search terms. Sorting helps price-sensitive shoppers compare products quickly and helps the business present the catalogue in a deliberate order.

## Frontend improvement 2 - At-a-glance stock status on product cards

### What I added

Each product card will show whether the item is in stock or sold out, based on the inventory data already returned by FastAPI. The detail page will continue to show size-level quantities.

### Why it helps

Customers can avoid opening unavailable products and can see immediately whether browsing results are actionable. The business avoids creating a poor experience where shoppers only discover stock problems after opening several products.

## Agent/backend improvement 1 - Better-ranked catalogue search

### What I added

The catalogue search tool will normalize the query, recognize common singular/plural wording such as "hoodies" and "hoodie," score exact names and garment types above loose description/tag matches, and return the strongest matches first.

### Why it helps

Questions such as "what hoodies do you have?" produce more relevant results even when the shopper's wording does not exactly match the database text. Better ranking improves answer quality and reduces irrelevant product cards.

## Agent/backend improvement 2 - Canonical product-card safety guard

### What I added

Before a `ChatReply` reaches the frontend, the backend will re-read every returned product ID from the database and replace the model's product card with the canonical catalogue record. Unknown product IDs are removed. If the model returns an invalid product card, the text reply remains available but the unsafe card is not rendered.

### Why it helps

The chatbot can speak naturally, but product names, prices, descriptions, image paths, and inventory shown on the website remain database-backed. This prevents a hallucinated price or product from becoming a clickable customer-facing card.

## Verification checklist

- Test each filter and sort option on the Products page.
- Confirm stock badges match `inventory.quantity` totals.
- Test plural and partial search wording through the chat tool.
- Confirm chat product cards are canonical catalogue records and unknown IDs do not reach the frontend.
