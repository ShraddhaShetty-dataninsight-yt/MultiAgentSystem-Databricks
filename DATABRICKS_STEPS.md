# How to Execute This in Databricks — Step by Step

This is the hands-on execution guide. Every click, every cell, every UI screen — in order.

---

## Before You Start: What You Need

- [ ] Databricks workspace with **Unity Catalog** enabled
- [ ] A running **cluster** (DBR 14.3 LTS or higher recommended)
- [ ] Permissions: `CREATE CATALOG`, `CREATE SCHEMA`, `CREATE TABLE`, `CREATE FUNCTION`
- [ ] Permission to create **Vector Search endpoints** (workspace admin or granted access)
- [ ] Access to **AgentBricks** (Workspace sidebar > Agents)

**Estimated total time**: ~60-90 minutes (most of it is waiting for Vector Search endpoint provisioning)

---

## PHASE 1: Import the Notebooks into Databricks

### Step 1.1 — Push to Git (or upload directly)

**Option A: Git Repo (recommended)**

```bash
cd /Users/shraddhashetty/MultiAgentsSystem/MultiAgentSystem-Databricks
git add -A
git commit -m "Add multi-agent system notebooks"
git push origin main
```

Then in Databricks:
1. Click **Workspace** in the left sidebar
2. Navigate to your user folder: `Workspace > Users > your_email`
3. Click the **kebab menu (...)** > **Create** > **Git folder**
4. Paste your repo URL, select branch `main`, click **Create Git folder**
5. The four folders (`00-init`, `01-vector-search`, `02-uc-functions`, `03-multi-agent`) appear as Databricks notebooks

**Option B: Manual upload**

1. Click **Workspace** > your user folder
2. Click **...** > **Import**
3. Upload each `.py` file — Databricks auto-detects the `# Databricks notebook source` header and imports them as notebooks
4. Maintain the folder structure: `00-init/`, `01-vector-search/`, `02-uc-functions/`, `03-multi-agent/`

### Step 1.2 — Verify folder structure in Databricks

Your workspace should look like:

```
Workspace/
└── Users/
    └── your_email/
        └── MultiAgentSystem-Databricks/
            ├── 00-init/
            │   ├── config
            │   └── generate-data
            ├── 01-vector-search/
            │   └── setup-vector-search
            ├── 02-uc-functions/
            │   └── register-tools
            └── 03-multi-agent/
                └── supervisor-setup
```

---

## PHASE 2: Configure and Generate Data

### Step 2.1 — Edit Configuration

1. Open `00-init/config` notebook
2. Update these values if needed:

```python
TARGET_CATALOG = "workspace"           # <-- your catalog name
TARGET_SCHEMA = "customer_support_intelligence"
TARGET_BRONZE_SCHEMA = "customer_support_intelligence_bronze"
```

> **How to find your catalog name**: Click **Catalog** in the left sidebar. The catalogs are listed at the top. Use `workspace` (default) or any catalog you have write access to.

3. **Run the cell** (Shift+Enter or click the play button) — should print:

```
✅ Configuration loaded successfully
   Catalog:  workspace
   Schema:   customer_support_intelligence
   Bronze:   customer_support_intelligence_bronze
```

### Step 2.2 — Attach a Cluster

1. In the top-right of the notebook, click **Connect** (or the cluster dropdown)
2. Select a running cluster (or start one)
3. Wait for it to show **Connected**

> **Cluster requirements**: Any cluster with DBR 14.3+ LTS works. Single-node is fine for data generation. You do NOT need a GPU cluster.

### Step 2.3 — Generate the Dataset

1. Open `00-init/generate-data` notebook
2. Attach the same cluster
3. Click **Run All** (top menu) or run cells one by one:

| Cell | What happens | Expected output |
|------|-------------|-----------------|
| Cell 1 (`%pip install faker`) | Installs faker library | Packages installed, Python restarts |
| Cell 2 (`%run "./config"`) | Loads configuration | `✅ Configuration loaded successfully` |
| Cell 3 (imports + schema creation) | Creates UC schemas | `✅ Schemas ready: ...` |
| Cell 4 (Products) | Creates 50 products | `✅ Products: 50 rows` |
| Cell 5 (Customers) | Creates 500 customers | `✅ Customers: 500 rows` |
| Cell 6 (Support Tickets) | Creates 2,000 tickets | `✅ Support Tickets: 2000 rows` |
| Cell 7 (Orders) | Creates 3,000 orders | `✅ Orders: 3000 rows` |
| Cell 8 (Interactions) | Creates 5,000 interactions | `✅ Interactions: 5000 rows` |
| Cell 9 (Reviews) | Creates 1,500 reviews | `✅ Product Reviews: 1500 rows` |
| Cell 10 (Summary) | Prints summary | Total rows: 12,050 |

**Runtime**: ~2-3 minutes total.

### Step 2.4 — Verify Data in Catalog Explorer

1. Click **Catalog** in the left sidebar
2. Navigate to: `workspace` > `customer_support_intelligence`
3. You should see 6 tables:

```
customer_support_intelligence/
├── support_tickets      (2,000 rows)
├── customers            (500 rows)
├── orders               (3,000 rows)
├── products             (50 rows)
├── customer_interactions (5,000 rows)
└── product_reviews      (1,500 rows)
```

4. Click any table > **Sample Data** tab to preview the data

---

## PHASE 3: Create Vector Search Indexes

This phase creates the semantic search infrastructure. The endpoint takes ~20 minutes to provision.

### Step 3.1 — Open and Run the Vector Search Notebook

1. Open `01-vector-search/setup-vector-search`
2. Attach your cluster
3. Run Cell 1 (`%pip install`) — installs `databricks-sdk` and `databricks-vectorsearch`
4. Run Cell 2 (`%run "../00-init/config"`) — loads config
5. Run Cell 3 — prints endpoint and index names:

```
Endpoint:      csi_tickets_endpoint_1739456789
Tickets Index: workspace.customer_support_intelligence_bronze.csi_tickets_index_1739456789
Reviews Index: workspace.customer_support_intelligence_bronze.csi_reviews_index_1739456789
```

> **Save these names** — you'll need the index names when creating the Knowledge Assistants.

### Step 3.2 — Clone Tables to Bronze Layer

Run Cell 4 (Prepare Bronze Tables):

```
✅ Tickets bronze table ready: workspace.customer_support_intelligence_bronze.support_tickets_bronze
✅ Reviews bronze table ready: workspace.customer_support_intelligence_bronze.product_reviews_bronze
```

### Step 3.3 — Create the Vector Search Endpoint

Run Cell 5. This is the long wait:

```
Creating Vector Search endpoint: csi_tickets_endpoint_1739456789
This takes 15-25 minutes to provision...
```

**What to do while waiting**:
- The cell output shows provisioning progress
- You can check status in the UI: **Compute** (left sidebar) > **Vector Search** tab
- The endpoint will show status: `PROVISIONING` → `ONLINE`

> **Do NOT cancel this cell.** If it times out, the endpoint is still provisioning. Check the Vector Search tab to see its status.

### Step 3.4 — Create the Two Indexes

Run Cell 6 (Tickets Index):
```
✅ Tickets index created: workspace...csi_tickets_index_1739456789
```

Run Cell 7 (Reviews Index):
```
✅ Reviews index created: workspace...csi_reviews_index_1739456789
```

### Step 3.5 — Wait for Embeddings to Build

Run Cell 8 — waits 120 seconds for indexes to build embeddings.

> **If tests fail after this wait**, the index is still building. Wait 2-3 more minutes and re-run the test cells. You can check index status:
>
> **Compute** > **Vector Search** > click your endpoint > you'll see both indexes with status `ONLINE` or `PROVISIONING`

### Step 3.6 — Test Semantic Search

Run Cells 9-12 (Tests 1-4). Each should display a table of results. For example:

**Test 1 output** should show 5 tickets about pipeline failures, even if the exact words "pipeline" or "executive" aren't in every result — that's semantic search working.

**Test 3 output** should show 5 reviews with high relevance scores about AI/ML features.

### Step 3.7 — Save Config

Run the final cell — saves index names to a config table for the supervisor notebook:

```
Config saved to: workspace.customer_support_intelligence_bronze._vector_search_config
```

### Step 3.8 — Verify in Vector Search UI

1. Go to **Compute** (left sidebar) > **Vector Search** tab
2. You should see your endpoint (`csi_tickets_endpoint_...`) with status **ONLINE**
3. Click the endpoint — it shows both indexes:
   - `csi_tickets_index_...` — Status: ONLINE
   - `csi_reviews_index_...` — Status: ONLINE

---

## PHASE 4: Register Unity Catalog Functions (MCP Tools)

### Step 4.1 — Run the Register Tools Notebook

1. Open `02-uc-functions/register-tools`
2. Attach your cluster
3. Click **Run All**

Each cell registers one SQL function. You'll see 20 checkmarks:

```
✅ get_customer_health_summary
✅ get_at_risk_customers
✅ get_customers_by_industry
✅ get_customer_engagement_summary
✅ get_ticket_stats_by_category
✅ get_escalated_tickets
✅ get_agent_performance
✅ get_sla_breach_summary
✅ get_product_defect_rates
✅ get_product_revenue
✅ get_product_review_summary
✅ get_product_ticket_correlation
✅ get_revenue_by_plan_tier
✅ get_overdue_payments
✅ get_order_trends_by_type
✅ All 5 lookup functions registered
```

**Runtime**: ~1-2 minutes.

### Step 4.2 — Verify Functions in Catalog Explorer

1. Go to **Catalog** > `workspace` > `customer_support_intelligence`
2. Click the **Functions** tab (next to Tables)
3. You should see all 20 functions listed
4. Click any function to see its signature, COMMENT, and parameters

### Step 4.3 — Quick Test a Function (Optional)

In a SQL editor or notebook cell, test a function:

```sql
SELECT * FROM workspace.customer_support_intelligence.get_at_risk_customers(0.6)
```

Should return a table of customers with churn risk >= 0.6.

```sql
SELECT * FROM workspace.customer_support_intelligence.list_valid_industries()
```

Should return all distinct industry values.

---

## PHASE 5: Create Agents in AgentBricks UI

This is the final phase — creating the actual AI agents. You do this in the Databricks UI, not in notebooks.

### Step 5.1 — Create the Ticket Analyst (Knowledge Assistant)

1. Click **Agents** in the left sidebar (or navigate to: Workspace > Agents)

   > If you don't see "Agents" in the sidebar, your workspace may need AgentBricks enabled. Contact your workspace admin.

2. Click **Create Agent**

3. Select **Knowledge Assistant**

4. Fill in the **Basic Configuration**:

   | Field | Value |
   |-------|-------|
   | **Name** | `csi-ticket-analyst` |
   | **Description** | `Analyzes customer support tickets using semantic search. Finds similar past tickets, identifies patterns across ticket categories, and summarizes ticket themes. Use this agent when questions involve support ticket content, descriptions, or finding related issues.` |

5. Click **Add Knowledge Source**:

   | Field | Value |
   |-------|-------|
   | **Type** | Vector Search Index |
   | **Vector Search Index** | Select your tickets index: `workspace.customer_support_intelligence_bronze.csi_tickets_index_TIMESTAMP` |
   | **Doc URI Column** | `ticket_id` |
   | **Text Column** | `description` |

   > **How to find the index name**: Go to **Compute** > **Vector Search** > click your endpoint > copy the tickets index name. Or run this SQL: `SELECT tickets_index_name FROM workspace.customer_support_intelligence_bronze._vector_search_config`

6. Scroll down to **Instructions** and paste:

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

7. Click **Create Agent**

8. Wait for the agent to deploy (1-3 minutes)

### Step 5.2 — Test the Ticket Analyst in Playground

After creation, you land on the agent's **Playground** page.

Type this test query:

```
Find tickets where customers are experiencing Snowflake connector sync failures. What are the common error patterns?
```

**Expected result**: The agent returns several tickets about connector failures, summarizes the error patterns (timeout errors, authentication issues, rate limits), and groups them by category.

Try another:

```
Show me Critical tickets about performance degradation that are still open.
```

If results look good, move on.

### Step 5.3 — Create the Review Analyst (Knowledge Assistant)

1. Go back to **Agents** > **Create Agent** > **Knowledge Assistant**

2. Configure:

   | Field | Value |
   |-------|-------|
   | **Name** | `csi-review-analyst` |
   | **Description** | `Analyzes product reviews using semantic search. Finds reviews matching specific sentiments, product feedback themes, and customer satisfaction patterns. Use this agent when questions involve what customers think about specific products or features.` |

3. Add Knowledge Source:

   | Field | Value |
   |-------|-------|
   | **Type** | Vector Search Index |
   | **Vector Search Index** | Select your reviews index: `workspace.customer_support_intelligence_bronze.csi_reviews_index_TIMESTAMP` |
   | **Doc URI Column** | `review_id` |
   | **Text Column** | `review_text` |

4. Instructions:

   ```
   You are a product review analyst for Dataflow, a B2B SaaS analytics platform.

   When analyzing reviews:
   - Include the product_name, rating, and key quotes from review text
   - Identify sentiment themes (praise, complaints, feature requests)
   - Compare sentiment across products when relevant
   - Highlight reviews from verified purchasers
   - Note patterns like "multiple customers mention X"
   - Be specific about which features are praised or criticized
   ```

5. Click **Create Agent** and wait for deployment

### Step 5.4 — Test the Review Analyst in Playground

```
What are customers saying about the Predictive Analytics Engine? Any common complaints?
```

```
Find positive reviews about integration connectors. What do happy customers value most?
```

---

### Step 5.5 — Create the Multi-Agent Supervisor

1. Go to **Agents** > **Create Agent** > **Multi-Agent Supervisor**

2. Basic configuration:

   | Field | Value |
   |-------|-------|
   | **Name** | `csi-operations-supervisor` |
   | **Description** | `Coordinates customer support intelligence by combining semantic ticket/review analysis with real-time operational data from Unity Catalog functions.` |

3. **Add Sub-Agents** — click **Add Agent** twice:

   | Sub-Agent | Endpoint |
   |-----------|----------|
   | Ticket Analyst | Select `csi-ticket-analyst` from dropdown |
   | Review Analyst | Select `csi-review-analyst` from dropdown |

4. **Add Unity Catalog Functions** — click **Add Function** and search for each:

   Search in `workspace.customer_support_intelligence` and add ALL 20 functions:

   **Customer Health:**
   - `get_customer_health_summary`
   - `get_at_risk_customers`
   - `get_customers_by_industry`
   - `get_customer_engagement_summary`

   **Support Operations:**
   - `get_ticket_stats_by_category`
   - `get_escalated_tickets`
   - `get_agent_performance`
   - `get_sla_breach_summary`

   **Product Analytics:**
   - `get_product_defect_rates`
   - `get_product_revenue`
   - `get_product_review_summary`
   - `get_product_ticket_correlation`

   **Revenue & Orders:**
   - `get_revenue_by_plan_tier`
   - `get_overdue_payments`
   - `get_order_trends_by_type`

   **Lookup/Grounding:**
   - `list_valid_ticket_categories`
   - `list_valid_priorities`
   - `list_valid_industries`
   - `list_valid_plan_tiers`
   - `list_valid_product_categories`

   > **Tip**: Type `get_` in the search box to quickly find the operational functions. Then type `list_` for the lookup functions.

5. **Add Coordination Instructions** — paste this in the Instructions field:

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

   - **Always use lookup functions first** when you need valid parameter values
     (e.g., call list_valid_industries before get_customers_by_industry).

   ## Response Format

   - Lead with the key finding or answer
   - Support with specific data points (numbers, ticket IDs, customer names)
   - End with actionable recommendations when appropriate
   - Use tables for structured data comparisons
   - Cite specific ticket IDs or review IDs when referencing search results
   ```

6. Click **Create Agent**

7. Wait for deployment (2-5 minutes)

---

## PHASE 6: Test the Multi-Agent Supervisor

You're now on the supervisor's **Playground** page. Run these 5 tests in order — each one is harder than the last.

### Test 1: Single-domain — Ticket Search

```
Find support tickets where customers are experiencing Snowflake connector sync failures. What are the common error patterns?
```

**Watch for**: Supervisor routes ONLY to Ticket Analyst. No UC functions called.

### Test 2: Single-domain — Structured Data

```
Show me all customers with churn risk above 0.6. Include their health scores and MRR.
```

**Watch for**: Supervisor routes ONLY to `get_at_risk_customers`. No vector search called.

### Test 3: Cross-domain — Tickets + Customer Health

```
Find customers who filed Critical priority tickets about performance issues. For each, show their churn risk and health score. Are any of them at risk of churning?
```

**Watch for**: Supervisor calls Ticket Analyst first, then feeds customer IDs into `get_customer_health_summary`. Synthesizes both into a combined answer.

### Test 4: Triple Cross-domain — Reviews + Products + Tickets

```
Which products have the worst customer reviews? For those products, what are the most common support ticket themes? And what is the defect rate? Give me a prioritized action plan.
```

**Watch for**: All three agents used — Review Analyst, Ticket Analyst, AND UC functions (`get_product_review_summary`, `get_product_defect_rates`, `get_product_ticket_correlation`).

### Test 5: Strategic QBR Prep

```
I'm preparing for a QBR. Give me a complete picture: revenue breakdown by plan tier, top 5 at-risk customers by MRR, most common support issues, products generating the most tickets, and any overdue payments.
```

**Watch for**: 5+ parallel UC function calls synthesized into a structured QBR summary.

---

## PHASE 7: Call the Supervisor Programmatically (Optional)

After the supervisor is deployed, you can call it from any notebook or application:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

response = w.serving_endpoints.query(
    name="csi-operations-supervisor",
    messages=[{
        "role": "user",
        "content": "Find at-risk customers who filed Critical tickets. Show their health scores and what products they use."
    }]
)

print(response.choices[0].message.content)
```

Or using the REST API from any language:

```bash
curl -X POST "https://<your-workspace>.databricks.com/serving-endpoints/csi-operations-supervisor/invocations" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Show me the top 5 at-risk customers"}]
  }'
```

---

## PHASE 8: Cleanup (When Done)

Vector Search endpoints incur costs while running. Clean up when you're done experimenting.

### Option A: Clean Up from Notebook

1. Open `01-vector-search/setup-vector-search`
2. Scroll to the bottom **Cleanup** cell
3. Uncomment the code and run it

### Option B: Clean Up from UI

1. **Compute** > **Vector Search** > click your endpoint
2. Delete each index (click the kebab menu > Delete)
3. Delete the endpoint itself

### Option C: Clean Up from SQL

```sql
-- Drop the schemas (cascading deletes tables and functions)
DROP SCHEMA IF EXISTS workspace.customer_support_intelligence CASCADE;
DROP SCHEMA IF EXISTS workspace.customer_support_intelligence_bronze CASCADE;
```

### Delete Agents

1. **Agents** > click each agent > **Settings** > **Delete Agent**
2. Delete in order: Supervisor first, then the two Knowledge Assistants

---

## Quick Reference: Execution Order

| Step | Notebook / UI | Time | What You Get |
|------|--------------|------|-------------|
| 1 | Import notebooks to Databricks | 5 min | Notebooks in workspace |
| 2 | Run `00-init/config` | 10 sec | Configuration loaded |
| 3 | Run `00-init/generate-data` | 2-3 min | 6 tables, 12,050 rows |
| 4 | Run `01-vector-search/setup-vector-search` | **20-30 min** | VS endpoint + 2 indexes |
| 5 | Run `02-uc-functions/register-tools` | 1-2 min | 20 UC functions |
| 6 | AgentBricks UI: Create Ticket Analyst | 3-5 min | Knowledge Assistant live |
| 7 | AgentBricks UI: Create Review Analyst | 3-5 min | Knowledge Assistant live |
| 8 | AgentBricks UI: Create Supervisor | 5-10 min | Multi-Agent Supervisor live |
| 9 | Playground: Test 5 queries | 10 min | System validated |

**Total**: ~60-90 minutes (most is Vector Search provisioning)

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `CatalogNotFoundException` | Catalog doesn't exist | Change `TARGET_CATALOG` in config to a catalog you have access to |
| `PermissionDenied` on schema creation | Insufficient privileges | Ask workspace admin for `CREATE SCHEMA` on the catalog |
| Vector Search endpoint stuck in `PROVISIONING` | Normal — takes 15-25 min | Wait. Check **Compute** > **Vector Search** for real-time status |
| `VECTOR_SEARCH` SQL function returns error | Index still building embeddings | Wait 2-3 min and retry. Index status must be `ONLINE` |
| Functions not visible in AgentBricks | Wrong catalog/schema | When adding functions, search the full path: `workspace.customer_support_intelligence.get_...` |
| Supervisor doesn't route to sub-agents | Agent endpoints not deployed | Verify both Knowledge Assistants show status `READY` in the Agents page |
| "No vector search endpoints found" | Endpoint was deleted or name mismatch | Re-run the vector search notebook to create a new endpoint |
| Cluster detached during `%pip install` | Auto-termination kicked in | Increase cluster auto-termination timeout to 60+ minutes |
