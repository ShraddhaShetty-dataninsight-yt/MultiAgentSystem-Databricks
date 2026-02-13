# Databricks notebook source
# MAGIC %md
# MAGIC # Register Unity Catalog Agent Tools (MCP Functions)
# MAGIC **Enterprise Customer Support Intelligence System**
# MAGIC
# MAGIC This notebook creates SQL functions in Unity Catalog that serve as **agent tools**
# MAGIC via the Model Context Protocol (MCP). These functions give AI agents structured
# MAGIC access to operational data.
# MAGIC
# MAGIC ### Tool Categories
# MAGIC
# MAGIC | Category | # Tools | Description |
# MAGIC |----------|---------|-------------|
# MAGIC | **Customer Health** | 4 | Health scores, churn risk, customer profiles |
# MAGIC | **Support Operations** | 4 | SLA metrics, ticket stats, agent performance |
# MAGIC | **Product Analytics** | 4 | Defect rates, revenue by product, adoption |
# MAGIC | **Order & Revenue** | 3 | Order trends, MRR analysis, payment status |
# MAGIC | **Lookup/Grounding** | 5 | List valid values for agent input validation |
# MAGIC
# MAGIC ### Prerequisites
# MAGIC - Run `00-init/generate-data` first to create all source tables

# COMMAND ----------

# MAGIC %run "../00-init/config"

# COMMAND ----------

catalog = TARGET_CATALOG
schema = TARGET_SCHEMA

print(f"Registering tools in: {catalog}.{schema}")
print("=" * 60)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Customer Health Tools
# MAGIC These tools help agents assess customer risk, prioritize outreach, and identify
# MAGIC accounts that need attention.

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_customer_health_summary
# MAGIC Returns health score, churn risk, NPS, and plan details for specific customers.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_customer_health_summary(customer_ids STRING)
RETURNS TABLE(
    customer_id STRING,
    company_name STRING,
    plan_tier STRING,
    health_score DOUBLE,
    churn_risk_score DOUBLE,
    nps_score INT,
    lifetime_value DOUBLE,
    support_tier STRING,
    csm_assigned STRING
)
COMMENT 'Returns health metrics and account details for specific customers. Input: JSON Array of customer IDs. Example: \'["CUST-0001", "CUST-0042"]\''
RETURN (
    SELECT
        customer_id,
        company_name,
        plan_tier,
        health_score,
        churn_risk_score,
        nps_score,
        lifetime_value,
        support_tier,
        csm_assigned
    FROM `{catalog}`.`{schema}`.customers
    WHERE array_contains(from_json(customer_ids, 'ARRAY<STRING>'), customer_id)
)
""")
print("✅ get_customer_health_summary")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_at_risk_customers
# MAGIC Identifies customers with churn risk above a threshold — critical for proactive retention.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_at_risk_customers(min_churn_risk DOUBLE)
RETURNS TABLE(
    customer_id STRING,
    company_name STRING,
    plan_tier STRING,
    churn_risk_score DOUBLE,
    health_score DOUBLE,
    monthly_recurring_revenue DOUBLE,
    last_login_date STRING,
    csm_assigned STRING
)
COMMENT 'Returns customers whose churn risk score is at or above the given threshold (0.0 to 1.0). Example: 0.5 returns customers with 50%+ churn risk.'
RETURN (
    SELECT
        customer_id,
        company_name,
        plan_tier,
        churn_risk_score,
        health_score,
        monthly_recurring_revenue,
        last_login_date,
        csm_assigned
    FROM `{catalog}`.`{schema}`.customers
    WHERE churn_risk_score >= min_churn_risk
    ORDER BY churn_risk_score DESC
    LIMIT 25
)
""")
print("✅ get_at_risk_customers")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_customers_by_industry
# MAGIC Segment customers by industry — useful for targeted outreach and pattern analysis.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_customers_by_industry(industries STRING)
RETURNS TABLE(
    industry STRING,
    total_customers BIGINT,
    avg_health_score DOUBLE,
    avg_churn_risk DOUBLE,
    total_mrr DOUBLE,
    avg_nps DOUBLE
)
COMMENT 'Returns aggregated customer metrics by industry. Input: JSON Array. Example: \'["Financial Services", "Healthcare"]\''
RETURN (
    SELECT
        industry,
        COUNT(*) AS total_customers,
        ROUND(AVG(health_score), 1) AS avg_health_score,
        ROUND(AVG(churn_risk_score), 2) AS avg_churn_risk,
        ROUND(SUM(monthly_recurring_revenue), 2) AS total_mrr,
        ROUND(AVG(nps_score), 1) AS avg_nps
    FROM `{catalog}`.`{schema}`.customers
    WHERE array_contains(from_json(industries, 'ARRAY<STRING>'), industry)
    GROUP BY industry
)
""")
print("✅ get_customers_by_industry")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_customer_engagement_summary
# MAGIC Shows interaction patterns — helps agents understand the relationship history before responding.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_customer_engagement_summary(customer_ids STRING)
RETURNS TABLE(
    customer_id STRING,
    total_interactions BIGINT,
    avg_sentiment DOUBLE,
    avg_csat DOUBLE,
    most_common_channel STRING,
    total_support_tickets BIGINT,
    avg_resolution_hours DOUBLE
)
COMMENT 'Returns engagement summary combining interactions and ticket data for specific customers. Input: JSON Array. Example: \'["CUST-0001"]\''
RETURN (
    SELECT
        c.customer_id,
        COALESCE(i.total_interactions, 0) AS total_interactions,
        ROUND(i.avg_sentiment, 2) AS avg_sentiment,
        ROUND(i.avg_csat, 1) AS avg_csat,
        i.most_common_channel,
        COALESCE(t.total_tickets, 0) AS total_support_tickets,
        ROUND(t.avg_resolution_hours, 1) AS avg_resolution_hours
    FROM `{catalog}`.`{schema}`.customers c
    LEFT JOIN (
        SELECT
            customer_id,
            COUNT(*) AS total_interactions,
            AVG(sentiment_score) AS avg_sentiment,
            AVG(csat_score) AS avg_csat,
            MODE(channel) AS most_common_channel
        FROM `{catalog}`.`{schema}`.customer_interactions
        GROUP BY customer_id
    ) i ON c.customer_id = i.customer_id
    LEFT JOIN (
        SELECT
            customer_id,
            COUNT(*) AS total_tickets,
            AVG(resolution_hours) AS avg_resolution_hours
        FROM `{catalog}`.`{schema}`.support_tickets
        GROUP BY customer_id
    ) t ON c.customer_id = t.customer_id
    WHERE array_contains(from_json(customer_ids, 'ARRAY<STRING>'), c.customer_id)
)
""")
print("✅ get_customer_engagement_summary")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Support Operations Tools
# MAGIC These tools give agents visibility into support team performance, SLA compliance,
# MAGIC and ticket trends.

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_ticket_stats_by_category
# MAGIC Aggregate ticket metrics by category — helps identify systemic issues.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_ticket_stats_by_category(categories STRING)
RETURNS TABLE(
    category STRING,
    total_tickets BIGINT,
    open_tickets BIGINT,
    avg_resolution_hours DOUBLE,
    avg_first_response_min DOUBLE,
    avg_satisfaction DOUBLE,
    pct_critical DOUBLE
)
COMMENT 'Returns ticket statistics for specific categories. Input: JSON Array. Example: \'["Integration", "Performance", "Bug"]\''
RETURN (
    SELECT
        category,
        COUNT(*) AS total_tickets,
        SUM(CASE WHEN status IN ('Open', 'In Progress', 'Escalated') THEN 1 ELSE 0 END) AS open_tickets,
        ROUND(AVG(resolution_hours), 1) AS avg_resolution_hours,
        ROUND(AVG(first_response_minutes), 1) AS avg_first_response_min,
        ROUND(AVG(satisfaction_rating), 2) AS avg_satisfaction,
        ROUND(SUM(CASE WHEN priority = 'Critical' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) AS pct_critical
    FROM `{catalog}`.`{schema}`.support_tickets
    WHERE array_contains(from_json(categories, 'ARRAY<STRING>'), category)
    GROUP BY category
)
""")
print("✅ get_ticket_stats_by_category")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_escalated_tickets
# MAGIC Critical for supervisors — shows all currently escalated or high-priority open tickets.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_escalated_tickets()
RETURNS TABLE(
    ticket_id STRING,
    customer_id STRING,
    subject STRING,
    category STRING,
    priority STRING,
    status STRING,
    created_at STRING,
    assigned_agent STRING,
    first_response_minutes DOUBLE,
    num_replies INT
)
COMMENT 'Returns all currently escalated tickets or Critical-priority tickets that are still open.'
RETURN (
    SELECT
        ticket_id,
        customer_id,
        subject,
        category,
        priority,
        status,
        created_at,
        assigned_agent,
        first_response_minutes,
        num_replies
    FROM `{catalog}`.`{schema}`.support_tickets
    WHERE status = 'Escalated'
       OR (priority = 'Critical' AND status IN ('Open', 'In Progress'))
    ORDER BY
        CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 ELSE 3 END,
        created_at ASC
    LIMIT 50
)
""")
print("✅ get_escalated_tickets")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_agent_performance
# MAGIC Ranks support agents by resolution time, CSAT, and ticket volume.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_agent_performance()
RETURNS TABLE(
    assigned_agent STRING,
    total_tickets BIGINT,
    resolved_tickets BIGINT,
    avg_resolution_hours DOUBLE,
    avg_satisfaction DOUBLE,
    avg_first_response_min DOUBLE
)
COMMENT 'Returns performance metrics for all support agents, ranked by resolution time.'
RETURN (
    SELECT
        assigned_agent,
        COUNT(*) AS total_tickets,
        SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_tickets,
        ROUND(AVG(resolution_hours), 1) AS avg_resolution_hours,
        ROUND(AVG(satisfaction_rating), 2) AS avg_satisfaction,
        ROUND(AVG(first_response_minutes), 1) AS avg_first_response_min
    FROM `{catalog}`.`{schema}`.support_tickets
    GROUP BY assigned_agent
    ORDER BY avg_resolution_hours ASC
    LIMIT 25
)
""")
print("✅ get_agent_performance")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_sla_breach_summary
# MAGIC Checks SLA compliance — tickets exceeding response or resolution time thresholds.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_sla_breach_summary(
    max_first_response_min DOUBLE,
    max_resolution_hours DOUBLE
)
RETURNS TABLE(
    category STRING,
    priority STRING,
    breached_response_sla BIGINT,
    breached_resolution_sla BIGINT,
    total_tickets BIGINT,
    breach_rate_pct DOUBLE
)
COMMENT 'Returns SLA breach counts by category and priority. Provide thresholds for first response (minutes) and resolution (hours). Example: 60, 24'
RETURN (
    SELECT
        category,
        priority,
        SUM(CASE WHEN first_response_minutes > max_first_response_min THEN 1 ELSE 0 END) AS breached_response_sla,
        SUM(CASE WHEN resolution_hours > max_resolution_hours THEN 1 ELSE 0 END) AS breached_resolution_sla,
        COUNT(*) AS total_tickets,
        ROUND(
            SUM(CASE WHEN first_response_minutes > max_first_response_min
                       OR resolution_hours > max_resolution_hours THEN 1.0 ELSE 0.0 END)
            / COUNT(*) * 100, 1
        ) AS breach_rate_pct
    FROM `{catalog}`.`{schema}`.support_tickets
    GROUP BY category, priority
    ORDER BY breach_rate_pct DESC
)
""")
print("✅ get_sla_breach_summary")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Product Analytics Tools
# MAGIC Help agents understand product quality, adoption, and customer satisfaction
# MAGIC at the product level.

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_product_defect_rates
# MAGIC Shows defect rates and quality metrics per product — useful for engineering prioritization.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_product_defect_rates(categories STRING)
RETURNS TABLE(
    product_id STRING,
    product_name STRING,
    category STRING,
    defect_rate DOUBLE,
    avg_rating DOUBLE,
    status STRING
)
COMMENT 'Returns defect rates and ratings for products in the given categories. Input: JSON Array. Example: \'["Integration", "AI/ML", "Platform"]\''
RETURN (
    SELECT
        product_id,
        name AS product_name,
        category,
        defect_rate,
        avg_rating,
        status
    FROM `{catalog}`.`{schema}`.products
    WHERE array_contains(from_json(categories, 'ARRAY<STRING>'), category)
    ORDER BY defect_rate DESC
)
""")
print("✅ get_product_defect_rates")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_product_revenue
# MAGIC Revenue and order volume per product — answers "what's our best seller?" type questions.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_product_revenue()
RETURNS TABLE(
    product_id STRING,
    product_name STRING,
    category STRING,
    total_orders BIGINT,
    total_revenue DOUBLE,
    avg_order_value DOUBLE,
    avg_discount_pct DOUBLE
)
COMMENT 'Returns revenue and order metrics per product, ranked by total revenue.'
RETURN (
    SELECT
        o.product_id,
        o.product_name,
        p.category,
        COUNT(*) AS total_orders,
        ROUND(SUM(o.amount), 2) AS total_revenue,
        ROUND(AVG(o.amount), 2) AS avg_order_value,
        ROUND(AVG(o.discount_percent), 1) AS avg_discount_pct
    FROM `{catalog}`.`{schema}`.orders o
    JOIN `{catalog}`.`{schema}`.products p ON o.product_id = p.product_id
    GROUP BY o.product_id, o.product_name, p.category
    ORDER BY total_revenue DESC
)
""")
print("✅ get_product_revenue")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_product_review_summary
# MAGIC Aggregated review stats per product — avg rating, volume, sentiment distribution.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_product_review_summary(product_ids STRING)
RETURNS TABLE(
    product_id STRING,
    product_name STRING,
    total_reviews BIGINT,
    avg_rating DOUBLE,
    five_star_pct DOUBLE,
    one_star_pct DOUBLE,
    verified_pct DOUBLE
)
COMMENT 'Returns review statistics for specific products. Input: JSON Array. Example: \'["PROD-001", "PROD-006"]\''
RETURN (
    SELECT
        product_id,
        product_name,
        COUNT(*) AS total_reviews,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(SUM(CASE WHEN rating = 5 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) AS five_star_pct,
        ROUND(SUM(CASE WHEN rating = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) AS one_star_pct,
        ROUND(SUM(CASE WHEN verified_purchase THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) AS verified_pct
    FROM `{catalog}`.`{schema}`.product_reviews
    GROUP BY product_id, product_name
    HAVING array_contains(from_json(product_ids, 'ARRAY<STRING>'), product_id)
)
""")
print("✅ get_product_review_summary")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_product_ticket_correlation
# MAGIC Which products generate the most support tickets? Correlates tickets with products via customer.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_product_ticket_correlation()
RETURNS TABLE(
    product_name STRING,
    category STRING,
    customers_with_tickets BIGINT,
    total_tickets_from_buyers BIGINT,
    avg_ticket_priority_score DOUBLE
)
COMMENT 'Correlates products with support ticket volume from their customers. Shows which products generate the most support burden.'
RETURN (
    SELECT
        o.product_name,
        p.category,
        COUNT(DISTINCT t.customer_id) AS customers_with_tickets,
        COUNT(t.ticket_id) AS total_tickets_from_buyers,
        ROUND(AVG(CASE t.priority
            WHEN 'Critical' THEN 4
            WHEN 'High' THEN 3
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 1
        END), 2) AS avg_ticket_priority_score
    FROM `{catalog}`.`{schema}`.orders o
    JOIN `{catalog}`.`{schema}`.products p ON o.product_id = p.product_id
    JOIN `{catalog}`.`{schema}`.support_tickets t ON o.customer_id = t.customer_id
    GROUP BY o.product_name, p.category
    ORDER BY total_tickets_from_buyers DESC
    LIMIT 20
)
""")
print("✅ get_product_ticket_correlation")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Order & Revenue Tools

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_revenue_by_plan_tier
# MAGIC Revenue breakdown by plan tier — answers questions about plan mix and ARPU.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_revenue_by_plan_tier()
RETURNS TABLE(
    plan_tier STRING,
    total_customers BIGINT,
    total_mrr DOUBLE,
    avg_mrr DOUBLE,
    avg_health_score DOUBLE,
    avg_churn_risk DOUBLE
)
COMMENT 'Returns revenue and health metrics aggregated by customer plan tier.'
RETURN (
    SELECT
        plan_tier,
        COUNT(*) AS total_customers,
        ROUND(SUM(monthly_recurring_revenue), 2) AS total_mrr,
        ROUND(AVG(monthly_recurring_revenue), 2) AS avg_mrr,
        ROUND(AVG(health_score), 1) AS avg_health_score,
        ROUND(AVG(churn_risk_score), 2) AS avg_churn_risk
    FROM `{catalog}`.`{schema}`.customers
    GROUP BY plan_tier
    ORDER BY total_mrr DESC
)
""")
print("✅ get_revenue_by_plan_tier")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_overdue_payments
# MAGIC Flags overdue orders — important for finance and account management.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_overdue_payments()
RETURNS TABLE(
    order_id STRING,
    customer_id STRING,
    company_name STRING,
    product_name STRING,
    amount DOUBLE,
    order_date STRING,
    payment_status STRING,
    plan_tier STRING
)
COMMENT 'Returns all orders with overdue or pending payment status, enriched with customer details.'
RETURN (
    SELECT
        o.order_id,
        o.customer_id,
        c.company_name,
        o.product_name,
        o.amount,
        o.order_date,
        o.payment_status,
        c.plan_tier
    FROM `{catalog}`.`{schema}`.orders o
    JOIN `{catalog}`.`{schema}`.customers c ON o.customer_id = c.customer_id
    WHERE o.payment_status IN ('Overdue', 'Pending')
    ORDER BY o.amount DESC
    LIMIT 50
)
""")
print("✅ get_overdue_payments")

# COMMAND ----------

# MAGIC %md
# MAGIC ### get_order_trends_by_type
# MAGIC Order type distribution — helps understand growth (new vs renewal vs upgrade).

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.get_order_trends_by_type(order_types STRING)
RETURNS TABLE(
    order_type STRING,
    total_orders BIGINT,
    total_revenue DOUBLE,
    avg_order_value DOUBLE,
    avg_discount_pct DOUBLE
)
COMMENT 'Returns order stats by type. Input: JSON Array. Example: \'["New", "Renewal", "Upgrade", "Add-on"]\''
RETURN (
    SELECT
        order_type,
        COUNT(*) AS total_orders,
        ROUND(SUM(amount), 2) AS total_revenue,
        ROUND(AVG(amount), 2) AS avg_order_value,
        ROUND(AVG(discount_percent), 1) AS avg_discount_pct
    FROM `{catalog}`.`{schema}`.orders
    WHERE array_contains(from_json(order_types, 'ARRAY<STRING>'), order_type)
    GROUP BY order_type
)
""")
print("✅ get_order_trends_by_type")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Lookup / Grounding Functions
# MAGIC These help agents discover valid input values before calling parameterized tools.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.list_valid_ticket_categories()
RETURNS TABLE(category STRING)
COMMENT 'Returns all valid support ticket categories.'
RETURN (SELECT DISTINCT category FROM `{catalog}`.`{schema}`.support_tickets ORDER BY 1)
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.list_valid_priorities()
RETURNS TABLE(priority STRING)
COMMENT 'Returns all valid ticket priority levels.'
RETURN (SELECT DISTINCT priority FROM `{catalog}`.`{schema}`.support_tickets ORDER BY 1)
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.list_valid_industries()
RETURNS TABLE(industry STRING)
COMMENT 'Returns all valid customer industries.'
RETURN (SELECT DISTINCT industry FROM `{catalog}`.`{schema}`.customers ORDER BY 1)
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.list_valid_plan_tiers()
RETURNS TABLE(plan_tier STRING)
COMMENT 'Returns all valid customer plan tiers.'
RETURN (SELECT DISTINCT plan_tier FROM `{catalog}`.`{schema}`.customers ORDER BY 1)
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION `{catalog}`.`{schema}`.list_valid_product_categories()
RETURNS TABLE(category STRING)
COMMENT 'Returns all valid product categories.'
RETURN (SELECT DISTINCT category FROM `{catalog}`.`{schema}`.products ORDER BY 1)
""")

print("✅ All 5 lookup functions registered")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Count all registered functions
result = spark.sql(f"""
    SELECT routine_name
    FROM `{catalog}`.information_schema.routines
    WHERE routine_schema = '{schema}'
    ORDER BY routine_name
""")

functions = [row.routine_name for row in result.collect()]

print("=" * 70)
print("  UNITY CATALOG TOOLS REGISTERED")
print("=" * 70)
print(f"\n  Schema: {catalog}.{schema}")
print(f"  Total functions: {len(functions)}\n")

for fn in functions:
    print(f"    - {catalog}.{schema}.{fn}")

print(f"""
{'=' * 70}

  Next step: Run 03-multi-agent/supervisor-setup
             to create the AgentBricks supervisor with these tools.
""")
