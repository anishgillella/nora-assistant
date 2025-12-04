# Nora - Technical Take-Home Assessment

> **Personal Browsing Memory Prototype**  
> Build a memory layer that turns raw browsing activity into usable insights + simple recommendations

---

## 📋 Overview

This is the technical take-home assessment for the **Founding AI Engineer** position at Nora. You'll build a quick prototype that demonstrates your ability to work with real-world data, LLMs, and retrieval systems.

---

## 🎯 What You'll Build

### Part 1: Shopping Memory Chat

Build a conversational interface that understands your browsing history:

1. **Data Collection**
   - Pull all your Chrome browsing history
   - Revisit those links & scrape the content
   - Extract useful signals (products, intents, preferences)

2. **Chat Interface**
   - Create a chat UI where users can ask questions like:
     - *"What shoes do I like?"*
     - *"What is the price of X?"*
     - *"Summarize my shopping habits."*

### Part 2: Mini Recommender

Build a simple product recommendation system:

1. **Product Index**
   - Scrape ~100 products from Shopify stores (e.g., `https://<store>/products.json`)
   - Build a product index using embeddings/vector approach

2. **Recommendation Chat**
   - Extend your chat interface to support queries like:
     - *"Recommend items based on my browsing."*
     - *"Find alternatives to things I looked at."*

---

## 📦 Deliverables

1. **GitHub Repository**
   - Clean, minimal setup
   - Well-organized code structure
   - Production-ready (or close to it)

2. **Loom Walkthrough** (<10 minutes)
   - Explain your approach
   - Demo the working prototype
   - Walk through key design decisions

3. **README Documentation**
   - Design decisions & tradeoffs
   - Architecture overview
   - What you'd do next with more time
   - Setup/installation instructions

---

## 🔍 What We're Evaluating

### 1. **Data Handling**
- Comfort scraping real-world sites (Playwright, Puppeteer)
- Parsing messy HTML/JSON
- Building simple ingestion pipelines

### 2. **Embeddings & Retrieval**
- Selecting appropriate embedding models
- Using vector stores (FAISS/Chroma/Pinecone)
- Performing similarity search with light ranking/filtering

### 3. **Memory Structuring**
- Converting raw activity into structured signals
- Building summaries, profiles, preferences
- Designing lightweight schemas for long-term personal memory

### 4. **Agentic/RAG Chat Systems**
- Context engineering
- Routing queries
- Calling tools
- Reasoning over mixed data
- Enabling conversational retrieval that feels grounded and useful

### 5. **LLM Fundamentals**
- Understanding RAG vs. long context vs. fine-tuning
- Writing strong prompts
- Mitigating hallucinations
- Optimizing for prompt cache hits
- Managing latency/cost

### 6. **Systems Thinking**
- Clean architecture
- Fast prototyping
- Debugging unpredictable model behavior
- Making smart tradeoffs under ambiguity

---

## 🛠 Expected Tools & Technologies

You are **expected** to use AI coding tools as part of your workflow:
- **Cursor**
- **Claude Code**
- **GitHub Copilot**
- Or similar AI-assisted development tools

This reflects how we work at Nora — we embrace AI tools to move faster and focus on hard problems.

---

## 📚 Recommended Resources

### Agent & Memory Architecture
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [12-Factor Agents](https://github.com/humanlayer/12-factor-agents/tree/main)
- [Anthropic: Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- [Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)

### Shopify API
- Product JSON endpoint: `https://<store>/products.json`
- Example stores to scrape: Any Shopify-powered store

---

## 🌟 About Nora

### Try Nora
- **Website:** [checkwithnora.com](https://checkwithnora.com)
- **Chrome Extension:** [Chrome Web Store](https://chromewebstore.google.com/detail/nora/ekcgdpkgpgohmogglfceiibfgpcppefh)
- **Safari Extension:** [App Store](https://apps.apple.com/us/app/nora-shopping/id6755109857)
- **Mobile App:** [App Store](https://apps.apple.com/us/app/nora-shopping/id6755109857)

### Learn More
- **Demo Day Video:** [Watch on YouTube](https://youtu.be/yULgS3qRWOA?si=blm96podMJSCWgOY)
- **Vision Document:** What is Nora? *(link provided in interview process)*

### Our Mission
> "We believe shopping shouldn't feel like 47 open tabs."

Nora is building the **memory layer for commerce** — helping shoppers make better decisions through intelligent context and personalized recommendations.

---

## 💡 Tips for Success

1. **Show Your Thinking**
   - Document your design decisions
   - Explain tradeoffs you considered
   - Be honest about what you'd improve with more time

2. **Focus on What Matters**
   - A working prototype beats perfect code
   - Demonstrate real understanding over tutorial-level implementation
   - Make smart tradeoffs given the time constraint

3. **Product Sense**
   - Think about the end user experience
   - Consider edge cases
   - Show you understand the problem space

4. **Communication**
   - Clear README documentation
   - Concise but comprehensive Loom walkthrough
   - Code comments where helpful

---

