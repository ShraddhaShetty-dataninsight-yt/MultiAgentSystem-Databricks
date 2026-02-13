# Building a Multi-Agent AI System with Databricks AgentBricks Supervisor

## A Step-by-Step Guide Using a Real-World Customer Support Intelligence Use Case

---

Single AI agents are powerful, but they hit a wall when questions span multiple data domains. Ask a RAG chatbot *"Which at-risk customers filed Critical support tickets and also left negative product reviews?"* and it can't answer — it would need to search unstructured ticket text, query structured customer health metrics, AND scan product reviews. Three different data sources, three different retrieval strategies, one question.

That's where **multi-agent systems** come in. Instead of building one monolithic agent that tries to do everything, you build specialized agents and coordinate them with a supervisor.

This guide walks through building an **Enterprise Customer Support Intelligence** system on Databricks using **AgentBricks Supervisor** — from data generation to a fully orchestrated multi-agent deployment.

---

## What We're Building

A B2B SaaS company called **Dataflow** (fictional analytics platform) needs an AI system that can answer questions across four domains simultaneously:

| Domain | Data Type | Agent Type | Example Question |
|--------|-----------|------------|-----------------|
| Support Tickets | Unstructured text (2,000 tickets) | Knowledge Assistant (RAG) | "Find tickets about Snowflake connector failures" |
| Product Reviews | Unstructured text (1,500 reviews) | Knowledge Assistant (RAG) | "What do customers think about our AI features?" |
| Customer Health | Structured metrics (500 customers) | UC Functions (MCP) | "Show at-risk customers with churn score > 0.6" |
| Business Operations | Structured metrics (orders, SLA, products) | UC Functions (MCP) | "Revenue by plan tier, overdue payments" |

The **Multi-Agent Supervisor** sits on top and routes questions to the right specialist — or coordinates multiple specialists for cross-domain queries.

### Architecture

```
                    ┌──────────────────────────────┐
                    │   CSI Operations Supervisor   │
                    │   (AgentBricks Multi-Agent)   │
                    └──────────┬───────────────────┘
                               │  routes & synthesizes
            ┌──────────────────┼──────────────────┐
            │                  │                  │
 ┌──────────▼───────┐  ┌──────▼────────┐  ┌──────▼──────────────┐
 │  Ticket Analyst   │  │ Review Analyst │  │  UC Functions       │
 │  (Knowledge Asst) │  │ (Knowledge    │  │  (20 MCP Tools)     │
 │                   │  │  Assistant)   │  │                     │
 │  Vector Search    │  │ Vector Search │  │  Customer Health    │
 │  over ticket      │  │ over review   │  │  Support Operations │
 │  descriptions     │  │ text          │  │  Product Analytics  │
 │                   │  │               │  │  Revenue & Orders   │
 └───────────────────┘  └───────────────┘  └─────────────────────┘
```

### Why AgentBricks Supervisor?

AgentBricks is Databricks' built-in framework for building agent systems. The Supervisor pattern specifically gives you:

- **Automatic routing** — the supervisor decides which sub-agent(s) to call based on the user's question
- **Result synthesis** — when multiple agents are needed, the supervisor combines their outputs into a single coherent answer
- **Unity Catalog integration** — SQL functions registered in UC are automatically exposed as tools with proper schemas and descriptions
- **Built-in evaluation** — labeling sessions, quality metrics, and human feedback loops out of the box
- **Managed deployment** — no infrastructure to manage, just configure and deploy

---

## Prerequisites

Before starting, ensure you have:

- A Databricks workspace with **Unity Catalog** enabled
- Permission to create **catalogs, schemas, and tables**
- Permission to create **Vector Search endpoints**
- Permission to create **SQL functions** in Unity Catalog
- Access to the **AgentBricks UI** (Workspace > Agents)

Install required packages in your first notebook cell:

```python
%pip install -U --quiet \
    databricks-sdk==0.49.0 \
    "databricks-langchain>=0.4.0" \
    databricks-agents \
    mlflow[databricks] \
    databricks-vectorsearch==0.55 \
    faker
dbutils.library.restartPython()
```

---

## Step 1: Set Up Your Configuration

Every notebook in this project imports from a shared configuration file. This ensures consistency across all steps.

```python
# 00-init/config.py

# Unity Catalog location
TARGET_CATALOG = "workspace"
TARGET_SCHEMA = "customer_support_intelligence"
TARGET_BRONZE_SCHEMA = "customer_support_intelligence_bronze"

# Table names
TICKETS_TABLE = "support_tickets"
CUSTOMERS_TABLE = "customers"
ORDERS_TABLE = "orders"
PRODUCTS_TABLE = "products"
INTERACTIONS_TABLE = "customer_interactions"
FEEDBACK_TABLE = "product_reviews"

# Vector search
EMBEDDING_MODEL = "databricks-gte-large-en"

# Agent names
TICKET_ANALYST_AGENT = "csi-ticket-analyst"
SUPERVISOR_AGENT = "csi-operations-supervisor"
```

**Key design decision**: We use two schemas — a primary schema for source tables and functions, and a bronze schema for vector search cloned tables. This separates concerns and prevents vector search operations from affecting source data.

---

## Step 2: Generate Your Dataset

A multi-agent system is only as good as the data behind it. We generate six interconnected tables with realistic synthetic data.

### The Data Model

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  customers   │────<│   orders     │>────│  products    │
│  (500 rows)  │     │  (3,000)     │     │  (50 rows)   │
└──────┬───────┘     └──────────────┘     └──────┬───────┘
       │                                         │
       │  ┌──────────────────┐    ┌──────────────▼───┐
       ├─<│ support_tickets  │    │ product_reviews  │
       │  │ (2,000 rows)     │    │ (1,500 rows)     │
       │  └──────────────────┘    └──────────────────┘
       │
       │  ┌──────────────────────┐
       └─<│ customer_interactions│
          │ (5,000 rows)         │
          └──────────────────────┘
```

### Why the ticket text matters

The `support_tickets.description` column is the most important field — it's the primary vector search target. We use template-based generation with variable substitution to create realistic, diverse ticket descriptions:

```python
TICKET_TEMPLATES = [
    # Integration issues
    {
        "category": "Integration",
        "subcategory": "Connector Failure",
        "templates": [
            "Our {connector} integration stopped syncing data about {timeframe} ago. "
            "We're seeing error code {error_code} in the logs. This is blocking our "
            "{team} team from accessing {data_type} data. We've already tried "
            "reconnecting and re-authenticating but the issue persists. This is "
            "critical as we have a {event} coming up and need the data flowing.",
            # ... more templates
        ]
    },
    # Performance, Bug, Feature Request, Account, Access, Data, Onboarding
    # ... 8 categories total with 3 templates each
]
```

Each template is filled with randomized but realistic values:

```python
def fill_template(template):
    replacements = {
        "{connector}": random.choice(["Snowflake", "Salesforce", "HubSpot", "BigQuery", ...]),
        "{error_code}": random.choice(["E-4001", "E-5002", "TIMEOUT-001", "AUTH-403", ...]),
        "{team}": random.choice(["analytics", "engineering", "marketing", "sales", ...]),
        # ... 40+ variable types
    }
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result
```

This produces tickets like:

> *"Our Snowflake integration stopped syncing data about 2 days ago. We're seeing error code E-4001 in the logs. This is blocking our analytics team from accessing revenue data. We've already tried reconnecting and re-authenticating but the issue persists. This is critical as we have a board meeting coming up and need the data flowing."*

Product reviews follow the same pattern with positive, mixed, and negative templates.

### Customer health scores are realistic too

Churn risk correlates with plan tier. Health score inversely correlates with churn risk. Lifetime value correlates with plan and tenure. This ensures the structured data tells coherent stories:

```python
# Churn risk correlates with plan tier
base_risk = {
    "Starter": 0.4,
    "Professional": 0.25,
    "Enterprise": 0.12,
    "Enterprise Plus": 0.08
}[plan]
churn_risk = round(min(1.0, max(0.0, base_risk + random.gauss(0, 0.15))), 2)

# Health score inversely correlates
health_score = round(min(100, max(0, (1 - churn_risk) * 100 + random.gauss(0, 10))), 1)
```

Run the data generation notebook:

```python
%run "00-init/generate-data"
```

Output:

```
Tables created in workspace.customer_support_intelligence:

  1. products               50 rows
  2. customers             500 rows
  3. support_tickets     2,000 rows
  4. orders              3,000 rows
  5. customer_interactions 5,000 rows
  6. product_reviews     1,500 rows

Total rows: 12,050
```

---

## Step 3: Create Vector Search Indexes

This is where unstructured text becomes searchable by meaning. We create two Delta Sync indexes — one for ticket descriptions and one for product review text.

### 3a. Prepare Bronze Tables

Vector Search requires **Change Data Feed (CDF)** enabled on the source table. Rather than modifying the originals, we clone them into a bronze schema:

```python
# Clone support tickets
spark.sql(f"""
CREATE OR REPLACE TABLE {tickets_bronze}
CLONE {TICKETS_FULL}
""")

spark.sql(f"""
ALTER TABLE {tickets_bronze}
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")
```

**Why clone?** Two reasons:
1. CDF adds overhead to every write — you don't want that on your operational tables
2. It isolates the vector search pipeline from source data changes

### 3b. Create the Vector Search Endpoint

The endpoint is the compute layer that serves vector search queries. Provisioning takes **15-25 minutes**.

```python
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient(disable_notice=True)

endpoint = vsc.create_endpoint_and_wait(
    name=endpoint_name,
    endpoint_type="STANDARD",
    verbose=True,
    timeout=datetime.timedelta(seconds=3600),
)
```

**Cost note**: In production, you'd use a single endpoint with a fixed name and update indexes rather than creating new ones each run. We use timestamped names here for experimentation.

### 3c. Create Delta Sync Indexes

Each index embeds a specific text column using Databricks' hosted `databricks-gte-large-en` model (1024-dimension embeddings):

```python
# Tickets Index — embeds the full ticket description
tickets_idx = vsc.create_delta_sync_index(
    endpoint_name=endpoint_name,
    index_name=tickets_index_name,
    source_table_name=tickets_bronze,
    pipeline_type="TRIGGERED",
    primary_key="ticket_id",
    embedding_source_column="description",      # <-- the text to embed
    embedding_model_endpoint_name="databricks-gte-large-en",
)

# Reviews Index — embeds the full review text
reviews_idx = vsc.create_delta_sync_index(
    endpoint_name=endpoint_name,
    index_name=reviews_index_name,
    source_table_name=reviews_bronze,
    pipeline_type="TRIGGERED",
    primary_key="review_id",
    embedding_source_column="review_text",      # <-- the text to embed
    embedding_model_endpoint_name="databricks-gte-large-en",
)
```

**Pipeline type `TRIGGERED`** means you control when the index re-syncs. For production with real-time ticket ingestion, switch to `CONTINUOUS`.

### 3d. Test Semantic Search

Once the indexes finish building embeddings (~2 minutes), test with semantic queries:

```sql
SELECT search_score, ticket_id, customer_id, subject, description, category, priority
FROM VECTOR_SEARCH(
    index => 'workspace.csi_bronze.csi_tickets_index_1234567890',
    query_text => 'data pipeline failing causing missing data in executive dashboards',
    num_results => 5
)
ORDER BY search_score DESC
```

This finds tickets about pipeline failures even if they don't contain those exact words. A ticket saying *"Our scheduled sync for PostgreSQL data stopped triggering... We depend on this daily refresh for our Executive Summary dashboard"* would score highly because the **meaning** matches.

### 3e. Save Config for Downstream Notebooks

Store the index names so the supervisor notebook can reference them:

```python
spark.sql(f"""
CREATE OR REPLACE TABLE {TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}._vector_search_config AS
SELECT
    '{endpoint_name}' AS endpoint_name,
    '{tickets_index_name}' AS tickets_index_name,
    '{reviews_index_name}' AS reviews_index_name,
    current_timestamp() AS created_at
""")
```

---

## Step 4: Register Unity Catalog Functions as Agent Tools

This is the **MCP (Model Context Protocol)** layer. Each SQL function becomes a tool that AI agents can call with proper input schemas and descriptions.

### Design Principles for Agent Tools

1. **Clear COMMENT strings** — the agent reads these to decide which tool to use. Be specific about inputs and include examples:

```sql
COMMENT 'Returns customers whose churn risk score is at or above the given
threshold (0.0 to 1.0). Example: 0.5 returns customers with 50%+ churn risk.'
```

2. **JSON Array inputs for multi-value parameters** — agents naturally produce JSON arrays when they need to pass multiple values:

```sql
CREATE OR REPLACE FUNCTION get_customers_by_industry(industries STRING)
...
WHERE array_contains(from_json(industries, 'ARRAY<STRING>'), industry)
```

3. **Grounding/lookup functions** — agents need to discover valid values before calling parameterized tools. Always provide lookup helpers:

```sql
CREATE OR REPLACE FUNCTION list_valid_industries()
RETURNS TABLE(industry STRING)
COMMENT 'Returns all valid customer industries.'
RETURN (SELECT DISTINCT industry FROM customers ORDER BY 1)
```

### The 20 Tools We Register

**Customer Health (4 tools)**:

```sql
-- Returns health metrics for specific customers
CREATE OR REPLACE FUNCTION get_customer_health_summary(customer_ids STRING)
RETURNS TABLE(
    customer_id STRING, company_name STRING, plan_tier STRING,
    health_score DOUBLE, churn_risk_score DOUBLE, nps_score INT,
    lifetime_value DOUBLE, support_tier STRING, csm_assigned STRING
)
COMMENT 'Returns health metrics and account details for specific customers.
Input: JSON Array of customer IDs. Example: \'["CUST-0001", "CUST-0042"]\''
RETURN (
    SELECT customer_id, company_name, plan_tier, health_score,
           churn_risk_score, nps_score, lifetime_value, support_tier, csm_assigned
    FROM customers
    WHERE array_contains(from_json(customer_ids, 'ARRAY<STRING>'), customer_id)
);

-- Identifies customers above a churn risk threshold
CREATE OR REPLACE FUNCTION get_at_risk_customers(min_churn_risk DOUBLE)
...

-- Aggregated metrics by industry
CREATE OR REPLACE FUNCTION get_customers_by_industry(industries STRING)
...

-- Interaction + ticket history per customer
CREATE OR REPLACE FUNCTION get_customer_engagement_summary(customer_ids STRING)
...
```

**Support Operations (4 tools)**:

```sql
-- Ticket stats by category (volume, resolution time, CSAT, % critical)
CREATE OR REPLACE FUNCTION get_ticket_stats_by_category(categories STRING)
...

-- All currently escalated or critical-priority open tickets
CREATE OR REPLACE FUNCTION get_escalated_tickets()
...

-- Support agent rankings by resolution time and CSAT
CREATE OR REPLACE FUNCTION get_agent_performance()
...

-- SLA breach rates by category and priority
CREATE OR REPLACE FUNCTION get_sla_breach_summary(
    max_first_response_min DOUBLE,
    max_resolution_hours DOUBLE
)
...
```

**Product Analytics (4 tools)**:

```sql
-- Defect rates and ratings by product category
CREATE OR REPLACE FUNCTION get_product_defect_rates(categories STRING)
...

-- Revenue and order volume per product
CREATE OR REPLACE FUNCTION get_product_revenue()
...

-- Review stats: avg rating, 5-star %, 1-star %
CREATE OR REPLACE FUNCTION get_product_review_summary(product_ids STRING)
...

-- Which products generate the most support tickets
CREATE OR REPLACE FUNCTION get_product_ticket_correlation()
...
```

**Revenue & Orders (3 tools)** and **Lookup Functions (5 tools)** round out the toolkit.

The key insight: **each function encapsulates a specific business question**. The agent doesn't write SQL — it calls pre-built, tested, governed functions.

---

## Step 5: Create the Knowledge Assistant Sub-Agents

Before building the supervisor, you need to create the specialist agents that it will coordinate.

### Ticket Analyst (Knowledge Assistant)

**In the AgentBricks UI:**

1. Navigate to **Workspace > Agents > Knowledge Assistant**
2. Click **Create Agent**
3. Configure:
   - **Name**: `csi-ticket-analyst`
   - **Description**: *"Analyzes customer support tickets using semantic search. Finds similar past tickets, identifies patterns across ticket categories, and summarizes ticket themes. Use this agent when questions involve support ticket content, descriptions, or finding related issues."*
4. Add **Knowledge Source**:
   - **Type**: Vector Search Index
   - **Source**: Select your tickets index (from Step 3)
   - **Doc URI Column**: `ticket_id`
   - **Text Column**: `description`
5. Add **Instructions**:

```
You are a support ticket analyst for Dataflow, a B2B SaaS analytics platform.

When searching for tickets:
- Always include the ticket_id, customer_id, category, and priority in results
- Summarize the key issue from each ticket description concisely
- Look for patterns across similar tickets (common root causes, affected features)
- Note if multiple tickets are from the same customer (may indicate a systemic issue)
- Flag any Critical or Escalated tickets prominently
- When asked about trends, group findings by category and priority
- Provide actionable insights, not just raw data
```

6. Click **Create Agent** and wait for deployment

### Review Analyst (Knowledge Assistant)

Repeat the same process with:
- **Name**: `csi-review-analyst`
- **Knowledge Source**: Reviews vector search index, `review_id`, `review_text`
- **Instructions** tailored for review analysis (sentiment themes, product comparisons, verified purchaser emphasis)

### Test Both Agents in Playground

Before wiring them into the supervisor, test each independently:

**Ticket Analyst test**:
> *"Find tickets where customers are experiencing data pipeline failures that affect executive reporting."*

**Review Analyst test**:
> *"What are customers saying about the Predictive Analytics Engine? Any common complaints?"*

If both return relevant, well-structured responses, proceed to the supervisor.

---

## Step 6: Create the Multi-Agent Supervisor

This is where it all comes together. The supervisor acts as an orchestrator — it understands the question, decides which specialist(s) to invoke, and synthesizes the results.

### In the AgentBricks UI:

1. Navigate to **Workspace > Agents > Multi-Agent Supervisor**
2. Click **Create Agent**
3. Configure:
   - **Name**: `csi-operations-supervisor`
   - **Description**: *"Coordinates customer support intelligence by combining semantic ticket/review analysis with real-time operational data from Unity Catalog functions."*

4. Add **Sub-Agents**:
   - **Ticket Analyst**: Select `csi-ticket-analyst` endpoint
   - **Review Analyst**: Select `csi-review-analyst` endpoint

5. Add **Unity Catalog Functions** (all 20 from Step 4):
   - `get_customer_health_summary`
   - `get_at_risk_customers`
   - `get_customers_by_industry`
   - `get_customer_engagement_summary`
   - `get_ticket_stats_by_category`
   - `get_escalated_tickets`
   - `get_agent_performance`
   - `get_sla_breach_summary`
   - `get_product_defect_rates`
   - `get_product_revenue`
   - `get_product_review_summary`
   - `get_product_ticket_correlation`
   - `get_revenue_by_plan_tier`
   - `get_overdue_payments`
   - `get_order_trends_by_type`
   - `list_valid_ticket_categories`
   - `list_valid_priorities`
   - `list_valid_industries`
   - `list_valid_plan_tiers`
   - `list_valid_product_categories`

6. Add **Coordination Instructions**:

```
You are the Customer Support Intelligence (CSI) Operations Supervisor for Dataflow,
a B2B SaaS analytics platform. You coordinate multiple specialist agents and data
tools to provide comprehensive answers about customer health, support operations,
product quality, and business metrics.

## Your Specialist Agents

1. **Ticket Analyst**: Semantic search over support tickets. Use when questions
   mention ticket content, similar issues, patterns in complaints, or specific
   error descriptions.

2. **Review Analyst**: Semantic search over product reviews. Use when questions
   ask about customer opinions, product satisfaction, feature feedback, or
   sentiment analysis.

3. **UC Functions (Data Tools)**: Structured queries for operational data. Use for:
   - Customer health scores, churn risk, engagement metrics
   - Support SLA compliance, agent performance, escalations
   - Product defect rates, revenue, order trends
   - Payment status, plan tier breakdowns

## Routing Rules

- **Single-domain questions**: Route to the most relevant specialist.
  Example: "Find tickets about Snowflake issues" -> Ticket Analyst only.

- **Cross-domain questions**: Break into sub-tasks, route to multiple
  specialists, then synthesize results.
  Example: "Find at-risk customers who filed integration tickets and left
  negative reviews"
  -> 1. UC Functions: get_at_risk_customers
  -> 2. Ticket Analyst: search for integration tickets from those customers
  -> 3. Review Analyst: search for negative reviews from those customers
  -> 4. Synthesize: combine all results into a cohesive answer

- **Always use lookup functions first** when you need valid parameter values.

## Response Format

- Lead with the key finding or answer
- Support with specific data points (numbers, ticket IDs, customer names)
- End with actionable recommendations when appropriate
- Use tables for structured data comparisons
- Cite specific ticket IDs or review IDs when referencing search results
```

7. Click **Create Agent** and wait for deployment

---

## Step 7: Test the Supervisor with Increasingly Complex Queries

Start simple. Build up to cross-domain. This validates that routing works correctly at each level.

### Test 1: Single-domain — Semantic Ticket Search

> *"Find support tickets where customers are experiencing Snowflake connector sync failures. What are the common error patterns?"*

**Expected routing**: Supervisor -> Ticket Analyst only

The supervisor should recognize this is a ticket-content question and route it exclusively to the Ticket Analyst, which performs a vector search. No UC functions needed.

### Test 2: Single-domain — Structured Data Query

> *"Show me all Enterprise customers with churn risk above 0.6. Include their health scores and MRR."*

**Expected routing**: Supervisor -> `get_at_risk_customers(0.6)` + possibly `get_customer_health_summary`

Pure structured data question. No vector search needed.

### Test 3: Cross-domain — Tickets + Customer Health

> *"Find customers who filed Critical priority tickets about performance issues. For each, show their churn risk and health score. Are any at risk of churning?"*

**Expected routing**:
1. Ticket Analyst: search for "Critical performance issues"
2. UC Functions: `get_customer_health_summary` for the customer IDs found in tickets
3. Synthesize: correlate ticket severity with churn risk

This is where the supervisor proves its value — it chains the Ticket Analyst's output into the UC function's input.

### Test 4: Triple Cross-domain — Reviews + Products + Tickets

> *"Which products have the worst customer reviews? For those products, what are the most common support ticket themes? What is the defect rate? Give me a prioritized action plan."*

**Expected routing**:
1. Review Analyst: search for negative reviews, identify worst products
2. UC Functions: `get_product_review_summary` + `get_product_defect_rates`
3. Ticket Analyst: search for tickets related to the problematic products
4. UC Functions: `get_product_ticket_correlation` for volume data
5. Synthesize: prioritized table with recommendations

### Test 5: Strategic Business Question (QBR Prep)

> *"Prepare a QBR summary: revenue by plan tier, top 5 at-risk customers by MRR, most common support issues, products generating the most tickets, and overdue payments."*

**Expected routing**: 5+ parallel UC function calls, then synthesis

This tests whether the supervisor can handle multiple independent sub-tasks efficiently.

### Calling the Supervisor Programmatically

After deployment, you can also call the supervisor via the SDK:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

response = w.serving_endpoints.query(
    name="csi-operations-supervisor",
    messages=[{
        "role": "user",
        "content": "Find at-risk customers who filed Critical tickets. "
                   "Show their health scores and what products they use."
    }]
)

print(response.choices[0].message.content)
```

---

## Step 8: Iterate and Improve

### Set Up Labeling Sessions

AgentBricks supports human feedback loops. Create labeling sessions where team members rate supervisor responses on:
- **Correctness** — did it answer the question accurately?
- **Completeness** — did it use all relevant data sources?
- **Routing quality** — did it call the right agents/tools?

### Common Issues and Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| Wrong routing | Supervisor calls UC functions when it should search tickets | Improve agent descriptions — make them more specific about when to use each |
| Missing data | Answer only uses one source when two are needed | Add examples in coordination instructions showing multi-step routing |
| Lookup failures | Agent passes invalid values to parameterized functions | Emphasize "always use lookup functions first" in instructions |
| Slow responses | Cross-domain queries take too long | Reduce the number of UC functions to only essential ones |
| Generic answers | Supervisor paraphrases without specific data | Add "cite specific ticket IDs and data points" to response format instructions |

### Monitor with MLflow

Log your supervisor configuration and track quality metrics over time:

```python
import mlflow

with mlflow.start_run(run_name="csi-supervisor-v1"):
    mlflow.log_dict(SUPERVISOR_CONFIG, "supervisor_config.json")
    mlflow.log_metrics({
        "num_sub_agents": 2,
        "num_uc_functions": 20,
        "num_knowledge_sources": 2,
    })
```

---

## Cleanup

Vector Search endpoints incur costs while running. Delete them when you're done experimenting:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Delete indexes first, then the endpoint
w.vector_search_indexes.delete_index(tickets_index_name)
w.vector_search_indexes.delete_index(reviews_index_name)
w.vector_search_endpoints.delete_endpoint(endpoint_name)
```

---

## Key Takeaways

1. **Specialize, don't generalize** — Each agent does one thing well. The Ticket Analyst only searches tickets. UC functions only query structured data. The supervisor only routes and synthesizes.

2. **Tool descriptions are the routing mechanism** — The supervisor decides which agent to call based on the COMMENT strings and agent descriptions. Invest time in writing clear, specific descriptions.

3. **Grounding functions prevent hallucination** — Lookup functions like `list_valid_industries()` ensure agents pass real values to parameterized tools instead of guessing.

4. **Start with single-domain, build to cross-domain** — Validate each agent independently before composing them. Debug one layer at a time.

5. **Coordination instructions are your control surface** — The supervisor's behavior is primarily controlled by its instructions. When routing goes wrong, fix the instructions first.

6. **Vector Search + UC Functions = full coverage** — Unstructured data (tickets, reviews) through RAG. Structured data (metrics, scores, aggregates) through SQL functions. The supervisor bridges both worlds.

---

## Repository Structure

```
MultiAgentSystem-Databricks/
├── 00-init/
│   ├── config.py              # Shared configuration
│   └── generate-data.py       # Synthetic data (6 tables, 12,050 rows)
├── 01-vector-search/
│   └── setup-vector-search.py # Endpoint + 2 indexes
├── 02-uc-functions/
│   └── register-tools.py      # 20 UC functions (MCP tools)
├── 03-multi-agent/
│   └── supervisor-setup.py    # AgentBricks supervisor + test queries
└── README.md
```

Run the notebooks in order (00 → 01 → 02 → 03) on your Databricks workspace. Each notebook includes inline documentation and can be executed cell-by-cell.
