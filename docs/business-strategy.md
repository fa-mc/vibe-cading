# Vibe-Cading: Business Strategy & Monetization Plan

## 1. Executive Summary
Vibe-Cading is evolving from a hobbyist script repository into an **AI-Driven Parametric CAD Generation Platform**. The core value proposition is enabling users to generate highly customized, manufacturable 3D models (STEP/STL) via natural language or image prompts using an LLM-orchestrated CadQuery backend.

To maximize both wide industry adoption and sustainable revenue, the project will follow an **Open-Core SaaS Model**, supported by a **Credit-Pack Pricing System**, and scaled through **Manufacturing Partnerships**.

## 2. Product & Licensing Architecture

The project will be conceptually split into two tiers to protect intellectual property while encouraging open-source growth:

### Tier 1: The Open Core (`vibe-cading` repository)
* **What it is:** The foundational Python classes, CadQuery generation logic, machinery algorithms, and agent prompts.
* **License:** **AGPLv3**. This aggressively protects the codebase from competitors attempting to wrap the engine in a closed-source SaaS without contributing back.
* **Contributor License Agreement (CLA):** Mandatory for all outside contributors. This ensures the original creator retains 100% copyright ownership, preserving the legal right to sell commercial licenses.
* **Target Audience:** Individual makers, hobbyists, and developers who want to run the generation engine locally for free.

### Tier 2: The B2B Commercial License
* **What it is:** A proprietary license waiver to the AGPLv3.
* **Target Audience:** Industrial B2B customers, robotics firms, or software companies who want to integrate the core `vibe-cading` engine into their internal proprietary or closed-source applications.

### Tier 3: The SaaS Web Platform (`vibe-cading-platform`)
* **What it is:** A closed-source, cloud-hosted web application managing LLM prompting, secure Python execution sandboxing, and CAD rendering.
* **Target Audience:** Non-programmers, product designers, and professionals who want instant CAD generation without local setup.
* **IP Policy:** Users retain 100% copyright over the *output* (the generated STEP/STL files) to remove adoption friction for commercial users.

## 3. Revenue & Pricing Model

To align variable compute costs (LLM tokens + OCCT geometric rendering) with revenue, the SaaS platform will utilize a **Hybrid Credit-Pack System** rather than a pure Pay-As-You-Go (PAYG) or pure Subscription model.

* **Credit Packs:** Users purchase blocks of compute upfront (e.g., "$10 for 100 Generation Credits").
    * *Advantage:* Bypasses high fixed payment processing fees (e.g., Stripe's $0.30 per transaction), secures upfront cash flow, and removes the "taxi-meter" psychological barrier that discourages users from iterating on their designs.
* **The "Pro" Safety Net (Optional Subscription):** A monthly tier (e.g., $20/mo) that grants a large recurring bucket of credits, priority rendering queue access, and private workspaces (ensuring B2B users' inputs are not used for future model training).

## 4. Strategic Partnerships & Distribution

Scaling relies on embedding the generation engine into existing manufacturing and 3D printing ecosystems.

### Partner Play A: Manufacturing Affiliates (PCBWay, JLCPCB, Xometry)
* **Integration:** Embed an "Instant Quote & Order" button directly in the Vibe-Cading Web UI upon successful model generation.
* **Monetization:** Capture a 5–10% affiliate commission on the manufacturing cost. This subsidizes server costs and provides a seamless user experience.
* **Expansion:** Long-term goal is to offer a white-labeled API directly to these manufacturers so they can embed "Generate Custom Bracket" tools natively on their storefronts.

### Partner Play B: 3D Printer Ecosystems (Bambu Lab, Prusa)
* **The Value Prop:** Parametric, AI-generated CAD is the missing link in modern slicers.
* **Integration:** Upload highly customizable script variants to repositories like MakerWorld or Printables to build organic traction. Use this community momentum to pitch direct API integration to slicer software teams (e.g., Bambu Studio, PrusaSlicer), allowing users to tweak CAD parameters directly within the slicing environment.

## 5. Key Technical & Operational Risks
* **Security & Sandboxing:** Executing LLM-generated Python code presents extreme security risks. The backend requires robust, ephemeral microVMs (e.g., Firecracker) to isolate the CadQuery execution environment and prevent server compromise.
* **LLM Reliability:** LLMs frequently write syntactically invalid Python or mathematically impossible Boolean operations. The system must include a self-correcting CI/CD loop that catches CadQuery stack traces and regenerates the prompt automatically before returning the result to the user.

## 6. Go-To-Market Roadmap & Prioritization

To manage engineering resources and minimize time-to-revenue, the rollout will heavily prioritize the B2C/Prosumer Web UI over the Public B2B API.

### Why Prioritize the Web UI First?
1. **The Ultimate Sales Demo:** B2B partners (Bambu Lab, PCBWay) will require proof that the engine reliably creates manufacturable geometry. A high-traction Web UI validates market demand and technical stability simultaneously.
2. **Immediate Cash Flow:** The Web UI allows immediate monetization via Credit Packs (minutes to revenue), whereas B2B API sales require lengthy legal, technical, and SLA negotiations (months to revenue).
3. **Internal Dogfooding:** The Web UI requires an internal backend API. Building the UI forces the engineering team to solve edge cases, timeouts, and sandboxing securely *before* exposing those endpoints to external paying developers.

### Phase 1: The SaaS Web UI (Proof of Traction & Cash Flow)
* **Goal:** Launch the interface, capture early adopters, and stress-test the LLM generation loop.
* **Core Deliverables:**
  * Clean, prompt-driven web frontend.
  * Integration of the Credit-Pack payment system (Stripe).
  * Implementation of basic "Order via PCBWay" affiliate links on the download page.

### Phase 2: The Headless B2B API (Strategic Scaling)
* **Goal:** Secure high-value, recurring enterprise contracts.
* **Core Deliverables:**
  * Polish the internal backend endpoints into a documented, public-facing REST/GraphQL API.
  * Add developer portals for API key management and usage tracking.
  * Pitch integration to slicer companies (Bambu Studio) and manufacturing aggregators to embed natively in their software.

## 7. Repository & Infrastructure Architecture

To execute this strategy without triggering licensing conflicts or security breaches, the codebase will be strictly divided into a **Two-Repository Architecture**. By keeping the open-source engine separated from the proprietary SaaS platform, we protect our IP while maintaining community goodwill.

### Repository 1: The Engine (Public)
* **Name:** `vibe-cading`
* **Visibility:** Public
* **License:** AGPLv3 (with CLA for external contributions)
* **Contents:**
  * Fundamental CadQuery logic, parametric math, and component classes (gears, hinges, adapters).
  * Unit tests validating geometry generation.
  * Core agent prompting templates.
* **Exclusions:** No web code, no HTTP handling, no billing logic, no LLM provider API keys.

### Repository 2: The Platform (Private)
* **Name:** `vibe-cading-platform`
* **Visibility:** Private
* **License:** Proprietary / Closed-Source
* **Contents (Monorepo):**
  * **Frontend (Web UI):** React/Vue interface for user authentication, prompt input, and 3D preview.
  * **Backend (API):** FastAPI/Django service handling database models (Users, Credit Balances), Stripe webhooks, and LLM API orchestration.
  * **Execution Workers:** Secure microVM/Docker configurations for the execution sandbox.
* **How they connect:** A user triggers a generation request via the Platform. The Platform's backend creates an isolated sandbox, dynamically installs the public `vibe-cading` Open Core via pip (`pip install git+https://...`), injects the LLM-generated script locally, extracts the STEP file, and immediately destroys the sandbox.