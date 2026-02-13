# Databricks notebook source
# MAGIC %md
# MAGIC # Multi-Agent Supervisor Setup
# MAGIC **Enterprise Customer Support Intelligence System**
# MAGIC
# MAGIC This notebook shows how to create a multi-agent AI system using **Databricks AgentBricks**.
# MAGIC The supervisor coordinates multiple specialist agents to answer complex, cross-domain questions.
# MAGIC
# MAGIC ### Architecture
# MAGIC
# MAGIC ```
# MAGIC                    ┌─────────────────────────┐
# MAGIC                    │   CSI Operations         │
# MAGIC                    │   Supervisor             │
# MAGIC                    │   (Orchestrator)         │
# MAGIC                    └────────┬────────────────┘
# MAGIC                             │
# MAGIC              ┌──────────────┼──────────────┐
# MAGIC              │              │              │
# MAGIC   ┌──────────▼──┐  ┌───────▼──────┐  ┌───▼──────────────┐
# MAGIC   │  Ticket      │  │  Review       │  │  UC Functions    │
# MAGIC   │  Analyst     │  │  Analyst      │  │  (MCP Tools)     │
# MAGIC   │  (RAG)       │  │  (RAG)        │  │                  │
# MAGIC   ├──────────────┤  ├──────────────┤  ├──────────────────┤
# MAGIC   │ Vector Search│  │ Vector Search│  │ Customer Health  │
# MAGIC   │ over tickets │  │ over reviews │  │ Support Ops      │
# MAGIC   │              │  │              │  │ Product Analytics│
# MAGIC   │              │  │              │  │ Revenue/Orders   │
# MAGIC   └──────────────┘  └──────────────┘  └──────────────────┘
# MAGIC ```
# MAGIC
# MAGIC ### What the Supervisor Can Do
# MAGIC
# MAGIC | Question Type | Agents Involved | Example |
# MAGIC |---------------|----------------|---------|
# MAGIC | Ticket similarity | Ticket Analyst | "Find tickets similar to this Snowflake sync issue" |
# MAGIC | Product feedback | Review Analyst | "What do customers say about the Predictive Analytics Engine?" |
# MAGIC | Customer risk | UC Functions | "Show me Enterprise customers with high churn risk" |
# MAGIC | **Cross-domain** | **All three** | **"Find frustrated customers with integration issues, check their churn risk, and see what reviews they left"** |
# MAGIC
# MAGIC ### Prerequisites
# MAGIC - **Notebook 00**: Data generated in Unity Catalog
# MAGIC - **Notebook 01**: Vector Search indexes created and ready
# MAGIC - **Notebook 02**: UC functions registered

# COMMAND ----------

# MAGIC %pip install -U --quiet databricks-sdk==0.49.0 "databricks-langchain>=0.4.0" databricks-agents mlflow[databricks]
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run "../00-init/config"

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Part 1: Create the Ticket Analyst (Knowledge Assistant)
# MAGIC
# MAGIC This agent uses RAG (Retrieval-Augmented Generation) over the support tickets
# MAGIC vector search index. It can find semantically similar tickets, identify patterns,
# MAGIC and summarize ticket themes.
# MAGIC
# MAGIC ### Option A: Create via AgentBricks UI (Recommended for first time)
# MAGIC
# MAGIC 1. Navigate to **Databricks Workspace → Agents → Knowledge Assistant**
# MAGIC 2. Configure:
# MAGIC    - **Name**: `csi-ticket-analyst`
# MAGIC    - **Description**: *"Analyzes customer support tickets using semantic search. Finds similar past tickets, identifies patterns across ticket categories, and summarizes ticket themes. Use this agent when questions involve support ticket content, descriptions, or finding related issues."*
# MAGIC 3. Add **Knowledge Source**:
# MAGIC    - **Type**: Vector Search Index
# MAGIC    - **Source**: Select the tickets index from notebook 01 (check `_vector_search_config` table)
# MAGIC    - **Doc URI Column**: `ticket_id`
# MAGIC    - **Text Column**: `description`
# MAGIC 4. Add **Instructions**:
# MAGIC    ```
# MAGIC    You are a support ticket analyst for Dataflow, a B2B SaaS analytics platform.
# MAGIC    When searching for tickets:
# MAGIC    - Always include the ticket_id, customer_id, category, and priority in results
# MAGIC    - Summarize the key issue from each ticket description
# MAGIC    - Look for patterns across similar tickets (common root causes, affected features)
# MAGIC    - Note if tickets are from the same customer (may indicate a systemic issue)
# MAGIC    - Flag any Critical or Escalated tickets prominently
# MAGIC    ```
# MAGIC 5. Click **Create Agent** and wait for deployment
# MAGIC
# MAGIC ### Option B: Create via SDK (Programmatic)

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.agents import create_agent, AgentConfig

w = WorkspaceClient()

# Retrieve the vector search index names from config table
vs_config = spark.sql(f"""
    SELECT * FROM {TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}._vector_search_config
    ORDER BY created_at DESC LIMIT 1
""").collect()[0]

tickets_index = vs_config["tickets_index_name"]
reviews_index = vs_config["reviews_index_name"]

print(f"Tickets Index: {tickets_index}")
print(f"Reviews Index: {reviews_index}")

# COMMAND ----------

# MAGIC %md
# MAGIC #### Create Ticket Analyst Agent

# COMMAND ----------

TICKET_ANALYST_CONFIG = {
    "agent_type": "KNOWLEDGE_ASSISTANT",
    "name": TICKET_ANALYST_AGENT,
    "description": (
        "Analyzes customer support tickets using semantic search. "
        "Finds similar past tickets, identifies patterns across ticket categories, "
        "and summarizes ticket themes. Use this agent when questions involve "
        "support ticket content, descriptions, or finding related issues."
    ),
    "knowledge_sources": [
        {
            "type": "VECTOR_SEARCH_INDEX",
            "vector_search_index_name": tickets_index,
            "doc_uri_column": "ticket_id",
            "text_column": "description",
        }
    ],
    "instructions": """You are a support ticket analyst for Dataflow, a B2B SaaS analytics platform.

When searching for tickets:
- Always include the ticket_id, customer_id, category, and priority in results
- Summarize the key issue from each ticket description concisely
- Look for patterns across similar tickets (common root causes, affected features)
- Note if multiple tickets are from the same customer (may indicate a systemic issue)
- Flag any Critical or Escalated tickets prominently
- When asked about trends, group findings by category and priority
- Provide actionable insights, not just raw data
""",
}

print(f"Ticket Analyst configuration ready: {TICKET_ANALYST_AGENT}")
print("Create this agent via the AgentBricks UI or SDK")

# COMMAND ----------

# MAGIC %md
# MAGIC #### Create Review Analyst Agent (Optional second Knowledge Assistant)
# MAGIC
# MAGIC If you want the supervisor to also search product reviews, create a second
# MAGIC Knowledge Assistant pointing at the reviews vector search index.

# COMMAND ----------

REVIEW_ANALYST_CONFIG = {
    "agent_type": "KNOWLEDGE_ASSISTANT",
    "name": "csi-review-analyst",
    "description": (
        "Analyzes product reviews using semantic search. "
        "Finds reviews matching specific sentiments, product feedback themes, "
        "and customer satisfaction patterns. Use this agent when questions involve "
        "what customers think about specific products or features."
    ),
    "knowledge_sources": [
        {
            "type": "VECTOR_SEARCH_INDEX",
            "vector_search_index_name": reviews_index,
            "doc_uri_column": "review_id",
            "text_column": "review_text",
        }
    ],
    "instructions": """You are a product review analyst for Dataflow, a B2B SaaS analytics platform.

When analyzing reviews:
- Include the product_name, rating, and key quotes from review text
- Identify sentiment themes (praise, complaints, feature requests)
- Compare sentiment across products when relevant
- Highlight reviews from verified purchasers
- Note patterns like "multiple customers mention X"
- Be specific about which features are praised or criticized
""",
}

print(f"Review Analyst configuration ready: csi-review-analyst")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Part 2: Create the Multi-Agent Supervisor
# MAGIC
# MAGIC The supervisor orchestrates the Knowledge Assistants and UC functions to answer
# MAGIC complex, multi-domain questions.
# MAGIC
# MAGIC ### Option A: Create via AgentBricks UI (Recommended)
# MAGIC
# MAGIC 1. Navigate to **Databricks Workspace → Agents → Multi-Agent Supervisor**
# MAGIC 2. Configure:
# MAGIC    - **Name**: `csi-operations-supervisor`
# MAGIC    - **Description**: *"Coordinates customer support intelligence by combining semantic ticket/review analysis with real-time operational data from Unity Catalog functions."*
# MAGIC 3. Add **Sub-Agents**:
# MAGIC    - **Ticket Analyst** (Agent Endpoint): Select `csi-ticket-analyst`
# MAGIC    - **Review Analyst** (Agent Endpoint): Select `csi-review-analyst` (if created)
# MAGIC 4. Add **Unity Catalog Functions** (from notebook 02):
# MAGIC    - `get_customer_health_summary`
# MAGIC    - `get_at_risk_customers`
# MAGIC    - `get_customers_by_industry`
# MAGIC    - `get_customer_engagement_summary`
# MAGIC    - `get_ticket_stats_by_category`
# MAGIC    - `get_escalated_tickets`
# MAGIC    - `get_agent_performance`
# MAGIC    - `get_sla_breach_summary`
# MAGIC    - `get_product_defect_rates`
# MAGIC    - `get_product_revenue`
# MAGIC    - `get_product_review_summary`
# MAGIC    - `get_product_ticket_correlation`
# MAGIC    - `get_revenue_by_plan_tier`
# MAGIC    - `get_overdue_payments`
# MAGIC    - `get_order_trends_by_type`
# MAGIC    - `list_valid_ticket_categories`
# MAGIC    - `list_valid_priorities`
# MAGIC    - `list_valid_industries`
# MAGIC    - `list_valid_plan_tiers`
# MAGIC    - `list_valid_product_categories`
# MAGIC 5. Add **Coordination Instructions** (see below)
# MAGIC 6. Click **Create Agent** and wait for deployment
# MAGIC
# MAGIC ### Option B: Programmatic Configuration

# COMMAND ----------

catalog = TARGET_CATALOG
schema = TARGET_SCHEMA

# List all UC functions to include as tools
uc_functions = [row.routine_name for row in spark.sql(f"""
    SELECT routine_name
    FROM `{catalog}`.information_schema.routines
    WHERE routine_schema = '{schema}'
    ORDER BY routine_name
""").collect()]

print(f"Found {len(uc_functions)} UC functions to register as tools:\n")
for fn in uc_functions:
    print(f"  {catalog}.{schema}.{fn}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Supervisor Coordination Instructions
# MAGIC
# MAGIC These instructions tell the supervisor *how* to route questions and *when* to
# MAGIC combine results from multiple agents.

# COMMAND ----------

SUPERVISOR_INSTRUCTIONS = """
You are the Customer Support Intelligence (CSI) Operations Supervisor for Dataflow,
a B2B SaaS analytics platform. You coordinate multiple specialist agents and data tools
to provide comprehensive answers about customer health, support operations, product quality,
and business metrics.

## Your Specialist Agents

1. **Ticket Analyst**: Semantic search over support tickets. Use when questions mention
   ticket content, similar issues, patterns in complaints, or specific error descriptions.

2. **Review Analyst**: Semantic search over product reviews. Use when questions ask about
   customer opinions, product satisfaction, feature feedback, or sentiment analysis.

3. **UC Functions (Data Tools)**: Structured queries for operational data. Use for:
   - Customer health scores, churn risk, engagement metrics
   - Support SLA compliance, agent performance, escalations
   - Product defect rates, revenue, order trends
   - Payment status, plan tier breakdowns

## Routing Rules

- **Single-domain questions**: Route to the most relevant specialist.
  Example: "Find tickets about Snowflake issues" → Ticket Analyst only.

- **Cross-domain questions**: Break into sub-tasks, route to multiple specialists,
  then synthesize results.
  Example: "Find at-risk customers who filed integration tickets and left negative reviews"
  → 1. UC Functions: get_at_risk_customers
  → 2. Ticket Analyst: search for integration tickets from those customers
  → 3. Review Analyst: search for negative reviews from those customers
  → 4. Synthesize: combine all results into a cohesive answer

- **Always use lookup functions first** when you need valid parameter values
  (e.g., call list_valid_industries before get_customers_by_industry).

## Response Format

- Lead with the key finding or answer
- Support with specific data points (numbers, ticket IDs, customer names)
- End with actionable recommendations when appropriate
- Use tables for structured data comparisons
- Cite specific ticket IDs or review IDs when referencing search results
"""

print("Supervisor instructions configured.")
print(f"Length: {len(SUPERVISOR_INSTRUCTIONS)} characters")

# COMMAND ----------

SUPERVISOR_CONFIG = {
    "agent_type": "MULTI_AGENT_SUPERVISOR",
    "name": SUPERVISOR_AGENT,
    "description": (
        "Coordinates customer support intelligence operations by combining "
        "semantic ticket and review analysis with real-time operational data. "
        "Routes questions to specialist agents and synthesizes cross-domain insights."
    ),
    "sub_agents": [
        {
            "name": "ticket_analyst",
            "agent_endpoint": TICKET_ANALYST_AGENT,
            "description": "Semantic search over support tickets",
        },
        {
            "name": "review_analyst",
            "agent_endpoint": "csi-review-analyst",
            "description": "Semantic search over product reviews",
        },
    ],
    "uc_functions": [f"{catalog}.{schema}.{fn}" for fn in uc_functions],
    "instructions": SUPERVISOR_INSTRUCTIONS,
}

print(f"Supervisor configuration ready: {SUPERVISOR_AGENT}")
print(f"  Sub-agents: {len(SUPERVISOR_CONFIG['sub_agents'])}")
print(f"  UC functions: {len(SUPERVISOR_CONFIG['uc_functions'])}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Part 3: Test the Supervisor
# MAGIC
# MAGIC Run these test queries against the deployed supervisor to verify it routes
# MAGIC correctly and synthesizes multi-domain answers.
# MAGIC
# MAGIC > **Note**: Replace `supervisor_endpoint` below with your actual deployed
# MAGIC > endpoint name from AgentBricks.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 1: Single-domain — Ticket Search (Semantic)
# MAGIC Routes to Ticket Analyst only.

# COMMAND ----------

# After deploying the supervisor via AgentBricks UI, test with:
#
# from databricks.sdk import WorkspaceClient
# w = WorkspaceClient()
#
# response = w.serving_endpoints.query(
#     name=SUPERVISOR_AGENT,
#     messages=[{
#         "role": "user",
#         "content": "Find support tickets where customers are experiencing Snowflake connector sync failures. What are the common error patterns?"
#     }]
# )
# print(response.choices[0].message.content)

print("""
TEST 1: Single-domain Ticket Search
Query: "Find support tickets where customers are experiencing Snowflake
        connector sync failures. What are the common error patterns?"

Expected behavior:
  → Supervisor routes to Ticket Analyst
  → Ticket Analyst searches vector index for "Snowflake connector sync failure"
  → Returns semantically similar tickets with patterns identified
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 2: Single-domain — Structured Data Query
# MAGIC Routes to UC Functions only.

# COMMAND ----------

print("""
TEST 2: Single-domain Structured Data Query
Query: "Show me all Enterprise customers with churn risk above 0.6.
        Include their health scores and MRR."

Expected behavior:
  → Supervisor routes to UC Function: get_at_risk_customers(0.6)
  → Returns structured table of at-risk Enterprise customers
  → May also call get_customer_health_summary for additional context
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 3: Cross-domain — Tickets + Customer Health
# MAGIC Routes to Ticket Analyst AND UC Functions, then synthesizes.

# COMMAND ----------

print("""
TEST 3: Cross-domain — Tickets + Customer Health
Query: "Find customers who have filed Critical priority tickets about
        performance issues in the last month. For each, show their
        churn risk score and health score. Are any of them at risk?"

Expected behavior:
  → Supervisor breaks into sub-tasks:
    1. Ticket Analyst: search for "Critical performance issues"
    2. UC Functions: get_customer_health_summary for affected customer IDs
    3. UC Functions: get_at_risk_customers to cross-reference
  → Synthesizes: "3 customers with Critical performance tickets are also
     flagged as high churn risk. Recommend immediate outreach."
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 4: Cross-domain — Reviews + Product Quality + Tickets
# MAGIC The most complex query — touches all three domains.

# COMMAND ----------

print("""
TEST 4: Full Cross-domain Analysis
Query: "Which products have the worst customer reviews? For those products,
        what are the most common support ticket themes? And what is the
        defect rate? Give me a prioritized action plan."

Expected behavior:
  → Supervisor orchestrates:
    1. Review Analyst: search for negative reviews, identify worst products
    2. UC Functions: get_product_review_summary + get_product_defect_rates
    3. Ticket Analyst: search for tickets related to problematic products
    4. UC Functions: get_product_ticket_correlation for volume data
  → Synthesizes: Prioritized table showing products ranked by combined
     review score, defect rate, and ticket volume with recommendations
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 5: Strategic Business Question
# MAGIC Tests the supervisor's ability to combine multiple data sources into strategic insight.

# COMMAND ----------

print("""
TEST 5: Strategic Business Question
Query: "I'm preparing for a QBR. Give me a complete picture:
        1. Revenue breakdown by plan tier
        2. Top 5 at-risk customers by MRR
        3. Most common support issues this quarter
        4. Products generating the most tickets
        5. Any overdue payments we should follow up on"

Expected behavior:
  → Supervisor makes 5+ parallel tool calls:
    1. get_revenue_by_plan_tier
    2. get_at_risk_customers(0.4)
    3. get_ticket_stats_by_category for all categories
    4. get_product_ticket_correlation
    5. get_overdue_payments
  → Synthesizes into a structured QBR summary with tables and
     actionable recommendations
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Part 4: Deploy with MLflow (Optional)
# MAGIC
# MAGIC For production deployments, register the supervisor as an MLflow model
# MAGIC and serve it via a Model Serving endpoint.

# COMMAND ----------

# import mlflow
#
# # Log the supervisor configuration as an MLflow model
# with mlflow.start_run(run_name="csi-supervisor-v1"):
#     mlflow.log_dict(SUPERVISOR_CONFIG, "supervisor_config.json")
#     mlflow.log_text(SUPERVISOR_INSTRUCTIONS, "supervisor_instructions.txt")
#
#     # Log metrics about the system
#     mlflow.log_metrics({
#         "num_sub_agents": len(SUPERVISOR_CONFIG["sub_agents"]),
#         "num_uc_functions": len(SUPERVISOR_CONFIG["uc_functions"]),
#         "num_knowledge_sources": 2,  # tickets + reviews indexes
#     })
#
#     mlflow.log_params({
#         "embedding_model": EMBEDDING_MODEL,
#         "supervisor_name": SUPERVISOR_AGENT,
#         "catalog": TARGET_CATALOG,
#         "schema": TARGET_SCHEMA,
#     })
#
# print("✅ Supervisor configuration logged to MLflow")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Summary

# COMMAND ----------

print(f"""
{'=' * 70}
  MULTI-AGENT SUPERVISOR SETUP COMPLETE
{'=' * 70}

  Architecture:
  ┌─────────────────────────────────────────────────┐
  │  {SUPERVISOR_AGENT:<47} │
  │  (Multi-Agent Supervisor)                       │
  └──────────┬──────────────┬───────────────────────┘
             │              │
  ┌──────────▼──┐  ┌───────▼──────┐  ┌──────────────┐
  │ Ticket      │  │ Review       │  │ UC Functions  │
  │ Analyst     │  │ Analyst      │  │ ({len(uc_functions)} tools)     │
  │ (RAG)       │  │ (RAG)        │  │              │
  └─────────────┘  └──────────────┘  └──────────────┘

  Knowledge Sources:
    - Tickets Vector Search:  {tickets_index}
    - Reviews Vector Search:  {reviews_index}

  UC Function Tools:
    - Customer Health:     4 functions
    - Support Operations:  4 functions
    - Product Analytics:   4 functions
    - Revenue & Orders:    3 functions
    - Lookups:             5 functions

  Next Steps:
    1. Create agents in AgentBricks UI (or via SDK)
    2. Test with the sample queries above
    3. Set up labeling sessions for human feedback
    4. Iterate on instructions based on quality metrics
""")
