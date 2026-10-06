# AI Prompt Log - HW 4

**Assignment:** Campus Customs customer website with an AI shopping chatbot

The project will use the catalogue in `data.zip`, which contains product image files and a product table/database. The planned stack is React + Vite + TypeScript for the frontend, Python FastAPI for the backend, and Pydantic AI for the chatbot brain. Portkey will be used for the model API connection.

## Problem 1 - Define the customer website and chatbot foundation

### Problem

Create the initial plan and implementation foundation for a real customer-facing Campus Customs website. The website should use the Yale Bulldog Blue/Campus Customs site as a reference for the visual direction, product-shopping experience, and relevant store information, while using the supplied catalogue as the source of truth for products. The first step should establish the project structure and architecture before adding more advanced chatbot behavior.

### Initial prompt typed

> We are starting HW4. Build a real customer website for Campus Customs with a shopping chatbot. Use React with Vite and TypeScript for the frontend, Python FastAPI for the backend, and Pydantic AI as the brain for the chatbot. Use Portkey for the model API connection. The catalogue is in `data.zip` in this HW4 folder and it has product image files plus a table/database with the product information. Inspect the zip and understand its structure before making assumptions about the data.
>
> Use https://yalebulldogblue.com/ as a reference for the style and for useful Campus Customs/Yale merchandise information. Make the site feel like a polished customer shopping site, with a clear Yale/Campus Customs visual identity, product browsing, product images, product details, and a chatbot that helps customers find products. Keep the frontend and backend separated cleanly. The chatbot must answer from the supplied catalogue and should not invent product names, prices, availability, sizes, colors, shipping information, or store policies. If the catalogue does not contain an answer, the chatbot should say that it does not know and direct the customer to the appropriate next step.
>
> For this first problem, focus on inspecting the supplied files, proposing the architecture, and creating the minimum runnable project foundation. Include the initial routes/components on the frontend, the FastAPI endpoints, the Pydantic models, the catalogue access approach, the Pydantic AI agent boundary, environment-variable handling for Portkey, and instructions for running the project locally. Do not add checkout, payment processing, account creation, or other external actions yet. Keep the code easy to extend because we will work through one problem at a time.

### Follow-up prompt

> Now proceed with the foundation you proposed. First unpack or read the supplied catalogue in a safe, reproducible way and document the actual files and fields you found. Then create the React/Vite/TypeScript frontend and the Python/FastAPI backend in the HW4 folder. Add a small, polished Campus Customs storefront page with catalogue-backed product cards and a chatbot panel placeholder or first working chat flow. Add typed request and response models, basic input validation, useful error messages, and a clear separation between catalogue lookup and the Pydantic AI agent. Read the Portkey API key only from an environment variable and do not hard-code or expose secrets in frontend code. Add a README with setup and run instructions. Stop after the foundation is working so we can review it before moving to the next problem.

## Problem 2 - Catalogue browsing and product search

_To be added after Problem 1 is reviewed._

## Problem 3 - Chatbot shopping assistance

_To be added after Problem 2 is reviewed._

## Problem 4 - Website polish, testing, and deployment readiness

_To be added after Problem 3 is reviewed._

## Problem 3/13 - Scaffold the storefront and catalogue-backed product pages

### Problem

Create the first customer-facing Campus Customs website foundation: a React + Vite + TypeScript frontend, a navigation bar for the main pages, original Home and About Us content inspired by the Yale Bulldog Blue reference, catalogue-backed product browsing, individual product pages, and a floating chatbot UI stub. Add a simple FastAPI backend that serves the products and the actual catalogue images. The chatbot does not need to call an agent yet.

### Prompt typed

> Now we need to scaffold a react + vite + typescript front end for campus customs. we need a navigation bar at the top that links the main pages Home, Products, About Us, Log in, Create account.
>
> From the yale bulldog website we need to take the info from Home and About us and write it in our own voice so they are not the exactly identical and have a different style and vibe to them.
>
> For the product page we need to show the images from the actual catalogue and use the image paths in the data base with basic info about the product such as name, price, and a brief description.
>
> Make each product open a single item page (large image on one side, full product text on the other with the description, price, sizes per stock when we have them) clicking a card on the products should take the shopper there.
>
> Then we add a chat interface in the bottom right of the website which could be a floating panel or any other cool feature. It does not need to talk to an agent yet, a stub that will call the backend later should be enough at this stage for problem 3.
>
> We will need to already have a simple FastAPI app in the backend/main.py to serve products and images and it will grow into an agent backend in problem 5.

### Implementation follow-up

> Use the extracted `data/campus_customs.db` and `data/products/` files as the source of truth. Keep the frontend and backend in separate `frontend/` and `backend/` folders, add local run instructions, and make the API return parsed product fields plus inventory by size. Keep authentication and chatbot actions as placeholders for later problems. Validate image paths so the media endpoint cannot escape the catalogue media directory.

## Problem 4/13 - Add account authentication and password recovery

### Problem

Build a normal create-account and login flow. New accounts need first name, last name, email address, password, and password confirmation. Existing users should be able to log in with email and password. Add a forgot-password flow that sends a short-lived PIN and allows the customer to create a new password. New users must be saved in the existing `users` table, and passwords must be protected so neither a human database reader nor an AI connected to the application can retrieve the original password.

### Prompt typed

> Now to problem 4 please build a normal create-account / login flow: Create account, first name, last name, email address, password, confirm password, forgot your password? function that can send you a pin to re-create the password. Log in with email and password.
>
> New accounts go into the users table, make sure to store passwords securely so hackers both human or AI will not access them.
>
> The seed database already has a test user you can use while building:
> Email: test@campuscustoms.yale.edu
> Password: password
>
> Confirm you can log in as that user and that a brand new account you create also works. Update output/harness.md with how authentication works (what you store for a user and how passwords are protected).

### Implementation follow-up

> Preserve compatibility with the seeded password hash, hash all new and reset passwords with a strong salted password-hashing method, and never return password hashes from the API. Add expiring single-use reset PIN records and avoid revealing whether an email address has an account. In local development the PIN may be exposed for testing because no email provider is configured yet, but do not expose it in production. Test the seed login, new-account registration and login, authenticated user lookup, and password reset flow.

## Problem 5/13 - Connect the Pydantic AI shopping chatbot

### Problem

Build the Campus Customs shop chatbot as a Pydantic AI agent behind FastAPI and plug it into the frontend chat widget. Keep the agent organized into the same four files used for HW3: `backend/prompts/prompt.md` for the system prompt, `backend/agent.py` for agent wiring, `backend/tools.py` for callable catalogue tools, and `backend/models.py` for Pydantic/Pydantic AI structured types. `backend/main.py` should expose the chat route and remain the file run by uvicorn from the backend folder.

### Prompt typed

> Now we need to build the shop chatbot as a pydanticAI agent behind fastAPI plugged into the front end chat widget. Put the API app in backend/main.py that is the file you run with uvicorn.
>
> Keep the agent as these four files next to it (same idea as HW 3): `backend/prompts/prompt.md` - system prompt (grow this same file later), `backend/agent.py` - agent entry/wiring, `backend/tools.py` - tools the agent can call, `backend/models.py` - pydantic/pydantic AI structured types.
>
> In main.py expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for products/auth). You will need the AI model API key for the agent.
>
> Put Campus Customs voice and safety basics into prompts/prompt.md (you will expand tools and safety later). Start or update in models.py for chat replies / product cards as needed.
>
> In output/harness.md note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). Make sure the backend runs from the backend/ folder like this: `uvicorn main:app --reload --port 8000`.
>
> Also explain what each backend file means: prompts, agent, tools, and models.

## Problem 6/13 - Ground product facts in the database

### Problem

Give the shopping agent database tools that look up real product descriptions, prices, and size-level stock from `campus_customs.db`. The agent must use the database rather than inventing prices or quantities, and it must clearly state when a requested size is out of stock. Expand the system prompt and document the tools and result fields in the harness.

### Prompt typed

> Now we need to give the agent tools that look up real info from campus_customs.db: product description, price, and the stock amount by size when the customer asks for it.
>
> The agent must use the database. It should not invent prices or quantities. If a size is out of stock the agent must state so clearly.
>
> Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update types in models.py.
>
> In output/harness.md list each tool and explain which model fields you chose for lookup results and why.

## Problem 7/13 - Update the website with chat search results

### Problem

When a customer asks about a category, the agent should search the catalogue and return structured product matches. The frontend should dynamically render those matches as product cards with real images, names, prices, and short information. Those cards must preserve the existing single-product detail-page behavior from Problem 3.

### Prompt typed

> Great let's proceed to problem 7. We will create chat search that updates the page.
>
> When a customer asks about a type of item, for example, what hoodies do you have? the agent should search the catalogue and the website should dynamically show relevant items as product cards, with image, name, price, and short info.
>
> This is an API contract - the agent returns structured product matches and then the front end renders them on the website.
>
> After the dynamic product cards are loaded by the new feature, make sure the same single item page behaviour you built in problem 3 still works: each product card including the ones the chat just put on the page should still open that detail view, with large image and full info.
>
> Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.

## Problem 8/13 - Add customer memory and page context

### Problem

Persist chat history for logged-in shoppers and reload it when they return. Guests can still chat without persistence. The agent should receive the authenticated shopper's explicit name and email through dependencies or an equivalent clear pattern. The frontend should also send enough page context—especially the current product ID—so references such as "do you have this in pink?" can be resolved against the product page the shopper is viewing.

### Prompt typed

> Great let's proceed to problem 8. Customer memory. When a shopper is logged in we want to save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) and put that in agent deps or an equivalent clear pattern and/or tools the agent can call.
>
> Also pass enough page context that if someone is on a product page and asks do you have this in pink the agent knows which item they mean. You can put code into agent context.
>
> Guests can still chat but history only needs to persist for logged in users.
>
> Document in output/harness.md how user chat history is stored, what customer fields the agent sees and how page context is passed.

## Problem 9/13 - Add usability improvements

### Problem

Choose and implement two frontend usability improvements and two agent/backend usability improvements. Frontend improvements should make the site easier to use or better looking. Agent/backend improvements should improve accuracy, safety, speed, or cost. Document what each improvement adds and why it helps a Campus Customs shopper or the business in `output/usability.md`, then make sure the features appear in the running app.

### Prompt typed

> Great let's move to usability improvements in problem 9.
>
> We want to choose and implement improvements: two front end usability improvements and two agent/backend usability improvements. Front end improvements are things that make the site look better and make it easier to use. Agent/backend improvements are things that make the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper.
>
> Write output/usability.md before or as you build. For each improvement say what you added and why it helps a Campus Customs shopper or the business. Then make sure all improvements actually show up in the running app. Graders will read the write-up and look for the features.

## Problem 10/13 - Style the Campus Customs storefront

### Problem

Make the website feel like a polished Campus Customs storefront with Yale colors, a large Yale logo on the left, a bulldog mark on the right, tasteful motion, strong typography hierarchy, and an inviting chat and product-card experience. Document the concrete design changes and why they should help customers stay engaged and shop.

### Prompt typed

> No for problem 10. We need to style the website. I want it to look cool like a real Campus Customs storefront, with Yale colors, and the big logo of Yale on the left. and the bulldog to the right, I want some moving stuff, and a nice hierarchy with a nice font, and a nice feel for the chat and product display.
>
> The nicer the more points we get. Write output/design.md about what you changed and why it should help customers stick around and buy. keep it clear, concrete and brief.

## Problem 11/13 - Test the storefront and document app checks

### Problem

Test the running Campus Customs website and create a double-clickable HTML report at `output/app_check.html`. Include a screenshot and a short caption for each required check: database-backed price and inventory from chat, product cards appearing after a category question, and one visible Problem 9 usability feature. Store the screenshots in `output/app_check_images/` and reference them using relative paths.

### Prompt typed

> Problem 11 is 2 before the last and it is as follows (so I suppose you were already needed to get the website running).
>
> Site testing app check.
>
> Test the live site and document it in `output/app_check.html` (a page you can double-click open). Include a clear screenshot and short captions for:
> 1. Chat checking the inventory level of an item (honest stock/price from the DB).
> 2. The dynamic search result card appearing after a category question (e.g., hoodies).
> 3. One of the usability features you added in Problem 9.
>
> Make the HTML easy to grade, with a heading for each check, a screenshot, and one or two sentences describing what the screenshot shows. Put the screenshot image files in `output/app_check_images/` and link them from `app_check.html` with relative paths, for example `app_check_images/inventory.png`.

## Problem 12/13 - Complete the audit trail, safety rules, and system harness

### Problem

Keep an append-only `output/audit_trail.json` of agent-loop activity, including the time, tool name, short arguments and result, and stop reason. Do not wipe it between runs. Add safety rules to `backend/prompts/prompt.md`, and finish `output/harness.md` so it clearly explains the system, including model fields and why they were chosen, tools and abilities, safety rules, loop limits, result caps, models, and how to run the frontend and backend.

### Prompt typed

> We need to finish the audit trail, safety, and finish the harness.
>
> Keep an append-only `output/audit_trail.json` of agent loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs.
>
> Also think of some safety rules to give the agent and put them in `prompts/prompt.md`.
>
> Finish `output/harness.md` so it is clear how the system works:
> - Model fields in `models.py` and why you chose them.
> - Tools and abilities.
> - Safety rules.
> - Specs (loop limits, result caps, models, and how to run the frontend and backend).
