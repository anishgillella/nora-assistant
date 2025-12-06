# Nora: Over-Delivery Features

> Innovative AI and UX features that elevate Nora beyond a standard shopping assistant.

---

## 🧠 AI Intelligence Layer

### 1. Contextual Memory Understanding

**Current State:** Stores "user viewed Nike shoes"  
**Enhancement:** Understand the *why* behind browsing behavior

| Signal | Inferred Context |
|--------|-----------------|
| Running shoes + fitness tracker searches | Training for a marathon |
| Frequently filters by price, abandons high-priced items | Budget-conscious |
| Searching categories they don't normally browse | Gift shopping |

**Implementation Approach:**
- Aggregate browsing patterns over time windows (7/30/90 days)
- Use LLM to infer user intent from pattern clusters
- Store context as embeddings for semantic matching

---

### 2. Proactive Nudges

**Problem:** Current AI waits for user to ask questions  
**Solution:** Surface insights automatically

**Types of Nudges:**
- **Price Drop Alert:** *"That jacket you looked at 3 times is now 30% off"*
- **Decision Fatigue:** *"You've been researching headphones for 2 weeks. Ready to decide?"*
- **Cross-Category:** *"Based on your running shoe research, you might want insoles too"*

**Implementation Approach:**
- Background job monitors price changes against browsing history
- Engagement scoring: views × time × recency = priority
- Webhook or push notification system for alerts

---

### 3. Multi-Turn Reasoning

**Current:** User asks → AI responds → context forgotten  
**Enhanced:** AI remembers the entire shopping journey

**Example:**
> *"Last week you said you wanted something under $100. This $95 option just became available."*

**Implementation Approach:**
- Store conversation summaries as embeddings
- Include user-stated preferences in RAG context
- Preference extraction: budget, size, color, brand preferences

---

## 🎯 UX Differentiators

### 4. "Why This?" Transparency

Every product recommendation displays reasoning chips explaining *why* it was recommended.

**Example Chips:**
```
✓ Brand you've bought before
✓ Your size in stock  
✓ 23% below your typical spend
✓ Similar to cart abandonment from last month
```

**Implementation Approach:**
- LLM structured output: `{reason_codes: ["brand_match", "price_fit", "size_available"]}`
- Chip UI component renders based on reason codes
- Max 3-4 chips per product to avoid clutter

---

### 5. Visual Browsing Timeline

Replace text-heavy history with an **interactive visual timeline**.

**Features:**
- Scrub through shopping journey with product thumbnails
- Pattern insights: "You always browse shoes on Fridays"
- Auto-cluster similar items together
- Filter by category, date range, or brand

**Implementation Approach:**
- Timeline component with horizontal scroll
- Group products by similarity score (embedding distance)
- Visualization library: D3.js or Recharts

---

### 6. Decision Helper Mode

When users are stuck between options, activate comparison mode.

**Features:**
- Side-by-side comparison tables (auto-generated from specs)
- Pros/cons lists based on reviews + product data
- Social proof: *"People like you chose Option A 73% of the time"*

**Implementation Approach:**
- Detect comparison intent: "should I get X or Y?"
- Scrape/extract specs from product pages
- LLM generates comparison narrative

---

## 💡 Smart Optimizations

### 7. Semantic Deduplication

**Problem:** 5 variants of same shoe clutter results  
**Solution:** Group and rank intelligently

**Example:**
> *"Nike Air Max 90 - 4 colorways available"* (shows best match)

**Implementation Approach:**
- Cluster products by embedding similarity (threshold: 0.85)
- Select representative using: availability × match_score × price
- Expandable UI to show variants on demand

---

### 8. Purchase Probability Scoring

Rank products by likelihood to convert, showing high-probability items first.

**Scoring Signals:**
| Signal | Weight |
|--------|--------|
| Visit frequency | 25% |
| Time on page | 20% |
| Similar user purchases | 25% |
| Price vs. typical spend | 15% |
| Cart/wishlist adds | 15% |

**Implementation Approach:**
- Calculate score at retrieval time
- Store engagement metrics per product
- Sort by probability before displaying

---

### 9. Cross-Session Context

Know when to restart vs continue a conversation.

**Scenarios:**
| Condition | Behavior |
|-----------|----------|
| Same session, same category | Continue naturally |
| New session, same category | *"Welcome back! Still looking for running shoes?"* |
| New session, different category | Fresh start |
| Long gap (7+ days) | *"It's been a while! What are you shopping for today?"* |

**Implementation Approach:**
- Track session timestamps and category per conversation
- Session gap thresholds trigger different greeting templates
- LLM system prompt adjusted based on context continuity

---

## 🚀 Priority Implementation

### Tier 1: High Impact, Low Effort
| Feature | Time | Impact |
|---------|------|--------|
| "Why This?" transparency chips | 2-3 hours | ⭐⭐⭐⭐⭐ |
| Semantic deduplication | 1-2 hours | ⭐⭐⭐⭐ |
| Cross-session greetings | 1 hour | ⭐⭐⭐ |

### Tier 2: Medium Effort
| Feature | Time | Impact |
|---------|------|--------|
| Decision helper mode | 4-5 hours | ⭐⭐⭐⭐ |
| Purchase probability scoring | 3-4 hours | ⭐⭐⭐⭐ |
| Contextual memory understanding | 4-5 hours | ⭐⭐⭐⭐⭐ |

### Tier 3: High Effort, Showcase Features
| Feature | Time | Impact |
|---------|------|--------|
| Visual browsing timeline | 6-8 hours | ⭐⭐⭐⭐⭐ |
| Proactive nudges | 6-8 hours | ⭐⭐⭐⭐⭐ |
| Multi-turn reasoning | 4-6 hours | ⭐⭐⭐⭐ |

---

## 🏆 Assessment Value

What these features demonstrate to evaluators:

| Feature | Demonstrates |
|---------|-------------|
| "Why This?" transparency | Explainable AI, user trust |
| Proactive nudges | Product thinking, user-centric design |
| Visual timeline | UX innovation, technical depth |
| Decision helper | Complex multi-step reasoning |
| Semantic deduplication | Clean data handling, attention to detail |

---

## Next Steps

1. Implement Tier 1 features (3-5 hours)
2. Document implementation decisions
3. Record demo showcasing new features
4. Update README with feature highlights
