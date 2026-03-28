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