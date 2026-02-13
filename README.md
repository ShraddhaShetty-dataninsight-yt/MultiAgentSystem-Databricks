# Multi-Agent System on Databricks using AgentBricks Supervisor

An enterprise-grade **Customer Support Intelligence (CSI)** system built on Databricks using **AgentBricks**, **Vector Search**, and **Unity Catalog Functions (MCP)**. The system coordinates multiple AI agents to provide cross-domain insights across support tickets, product reviews, customer health, and business operations.

## Use Case: Enterprise Customer Support Intelligence

A B2B SaaS company (**Dataflow** — a fictional analytics platform) needs to:

- **Find similar past tickets** when a new issue comes in (semantic search)
- **Analyze product sentiment** across thousands of reviews (semantic search)
- **Monitor customer health** — churn risk, engagement, NPS scores (structured queries)
- **Track support SLAs** — breaches, agent performance, escalations (structured queries)
- **Answer cross-domain questions** like: *"Which at-risk customers filed Critical tickets about performance and also left negative reviews?"*

No single tool can answer that. A **multi-agent supervisor** can.

## Architecture

```
                    ┌──────────────────────────────┐
                    │   CSI Operations Supervisor   │
                    │   (AgentBricks Multi-Agent)   │
                    └──────────┬───────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
 ┌──────────▼───────┐  ┌──────▼────────┐  ┌──────▼──────────────┐
 │  Ticket Analyst   │  │ Review Analyst │  │  UC Functions       │
 │  (Knowledge Asst) │  │ (Knowledge    │  │  (20 MCP Tools)     │
 │                   │  │  Assistant)   │  │                     │
 │  Vector Search    │  │ Vector Search │  │  Customer Health    │
 │  over 2,000       │  │ over 1,500    │  │  Support Operations │
 │  support tickets  │  │ product       │  │  Product Analytics  │
 │                   │  │ reviews       │  │  Revenue & Orders   │
 └───────────────────┘  └───────────────┘  └─────────────────────┘
```

## Dataset

| Table | Rows | Description |
|-------|------|-------------|
| `support_tickets` | 2,000 | Realistic ticket descriptions across 8 categories (Integration, Performance, Bug, Feature Request, Account, Access, Data, Onboarding) |
| `product_reviews` | 1,500 | Written reviews with ratings for 50 products — positive, mixed, and negative |
| `customers` | 500 | B2B customer profiles with health scores, churn risk, NPS, plan tiers |
| `products` | 50 | SaaS product catalog with defect rates, ratings, categories |
| `orders` | 3,000 | Subscription and purchase history with payment status |
| `customer_interactions` | 5,000 | Multi-channel interaction log with sentiment scores |

## Project Structure

```
MultiAgentSystem-Databricks/
├── 00-init/
│   ├── config.py              # Central configuration (catalog, schema, table names)
│   └── generate-data.py       # Synthetic data generation (all 6 tables)
├── 01-vector-search/
│   └── setup-vector-search.py # Vector Search endpoint + 2 indexes (tickets & reviews)
├── 02-uc-functions/
│   └── register-tools.py      # 20 Unity Catalog SQL functions (MCP agent tools)
├── 03-multi-agent/
│   └── supervisor-setup.py    # AgentBricks supervisor configuration + test queries
├── LICENSE
└── README.md
```

## Setup Instructions

### Step 1: Configure

Edit [00-init/config.py](00-init/config.py) with your Databricks catalog and schema names.

### Step 2: Generate Data

Run [00-init/generate-data.py](00-init/generate-data.py) to create all 6 tables in Unity Catalog.

### Step 3: Create Vector Search Indexes

Run [01-vector-search/setup-vector-search.py](01-vector-search/setup-vector-search.py). This creates:
- A Vector Search endpoint (~20 min to provision)
- Tickets index (semantic search over `description` column)
- Reviews index (semantic search over `review_text` column)

### Step 4: Register UC Function Tools

Run [02-uc-functions/register-tools.py](02-uc-functions/register-tools.py) to register 20 SQL functions as MCP agent tools:

**Customer Health** (4 tools):
- `get_customer_health_summary` — Health score, churn risk, NPS for specific customers
- `get_at_risk_customers` — Customers above a churn risk threshold
- `get_customers_by_industry` — Aggregated metrics by industry
- `get_customer_engagement_summary` — Interaction + ticket history per customer

**Support Operations** (4 tools):
- `get_ticket_stats_by_category` — Volume, resolution time, CSAT by category
- `get_escalated_tickets` — All currently escalated/critical open tickets
- `get_agent_performance` — Support agent rankings
- `get_sla_breach_summary` — SLA compliance by category and priority

**Product Analytics** (4 tools):
- `get_product_defect_rates` — Defect rates and ratings by category
- `get_product_revenue` — Revenue and orders per product
- `get_product_review_summary` — Review stats (avg rating, 5-star %, 1-star %)
- `get_product_ticket_correlation` — Which products generate the most tickets

**Revenue & Orders** (3 tools):
- `get_revenue_by_plan_tier` — MRR breakdown by plan
- `get_overdue_payments` — Orders with overdue/pending payment
- `get_order_trends_by_type` — New vs renewal vs upgrade vs add-on

**Lookup/Grounding** (5 tools):
- `list_valid_ticket_categories`, `list_valid_priorities`, `list_valid_industries`, `list_valid_plan_tiers`, `list_valid_product_categories`

### Step 5: Create Multi-Agent Supervisor

Run [03-multi-agent/supervisor-setup.py](03-multi-agent/supervisor-setup.py), then create agents in the AgentBricks UI:

1. **Ticket Analyst** (Knowledge Assistant) — RAG over ticket descriptions
2. **Review Analyst** (Knowledge Assistant) — RAG over product reviews
3. **CSI Supervisor** (Multi-Agent Supervisor) — Orchestrates both agents + 20 UC functions

## Example Queries

**Single-domain (Ticket Search):**
> "Find support tickets where customers are experiencing Snowflake connector sync failures. What are the common error patterns?"

**Single-domain (Structured Data):**
> "Show me all Enterprise customers with churn risk above 0.6."

**Cross-domain (Tickets + Customer Health):**
> "Find customers who filed Critical performance tickets. For each, show their churn risk and health score. Are any of them at risk of churning?"

**Cross-domain (Reviews + Products + Tickets):**
> "Which products have the worst reviews? For those, show me common ticket themes and defect rates. Give me a prioritized action plan."

**Strategic (Full QBR Prep):**
> "Prepare a QBR summary: revenue by plan tier, top 5 at-risk customers by MRR, most common support issues, products generating the most tickets, and any overdue payments."

## Requirements

- Databricks workspace with Unity Catalog enabled
- Access to create Vector Search endpoints
- `databricks-sdk>=0.49.0`
- `databricks-vectorsearch>=0.55`
- `databricks-langchain>=0.4.0`
- `databricks-agents`
- `mlflow[databricks]`
- `faker` (for data generation only)

## License

Apache License 2.0
