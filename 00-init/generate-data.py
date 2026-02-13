# Databricks notebook source
# MAGIC %md
# MAGIC # Generate Synthetic Dataset
# MAGIC **Enterprise Customer Support Intelligence System**
# MAGIC
# MAGIC This notebook generates realistic synthetic data for a B2B SaaS customer support platform.
# MAGIC The dataset simulates a company like Dataflow (fictional analytics SaaS) with:
# MAGIC
# MAGIC | Table | Description | Rows |
# MAGIC |-------|-------------|------|
# MAGIC | `support_tickets` | Customer support tickets with full descriptions | 2,000 |
# MAGIC | `customers` | Customer profiles with health metrics | 500 |
# MAGIC | `orders` | Subscription & purchase history | 3,000 |
# MAGIC | `products` | Product catalog with quality metrics | 50 |
# MAGIC | `customer_interactions` | Multi-channel interaction log | 5,000 |
# MAGIC | `product_reviews` | Written product reviews (for vector search) | 1,500 |

# COMMAND ----------

# MAGIC %pip install faker --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run "./config"

# COMMAND ----------

import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
from pyspark.sql import SparkSession
from pyspark.sql.types import *

fake = Faker()
Faker.seed(42)
random.seed(42)

# ============================================================
# Schema creation
# ============================================================
# Note: The catalog (e.g. "workspace") must already exist.
# We only create the schemas inside it.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}")

print(f"✅ Schemas ready: {TARGET_CATALOG}.{TARGET_SCHEMA}")
print(f"✅ Schemas ready: {TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Products Table
# MAGIC Dataflow's product catalog — analytics modules, integrations, and add-ons.

# COMMAND ----------

PRODUCT_CATALOG = [
    {"product_id": "PROD-001", "name": "Dataflow Analytics Core", "category": "Platform", "price": 299.00, "tier": "Essential"},
    {"product_id": "PROD-002", "name": "Dataflow Analytics Pro", "category": "Platform", "price": 799.00, "tier": "Professional"},
    {"product_id": "PROD-003", "name": "Dataflow Analytics Enterprise", "category": "Platform", "price": 1999.00, "tier": "Enterprise"},
    {"product_id": "PROD-004", "name": "Real-Time Dashboard Module", "category": "Visualization", "price": 149.00, "tier": "Add-on"},
    {"product_id": "PROD-005", "name": "Custom Report Builder", "category": "Visualization", "price": 199.00, "tier": "Add-on"},
    {"product_id": "PROD-006", "name": "Predictive Analytics Engine", "category": "AI/ML", "price": 499.00, "tier": "Premium"},
    {"product_id": "PROD-007", "name": "Anomaly Detection Module", "category": "AI/ML", "price": 349.00, "tier": "Premium"},
    {"product_id": "PROD-008", "name": "Data Pipeline Connector", "category": "Integration", "price": 99.00, "tier": "Add-on"},
    {"product_id": "PROD-009", "name": "Snowflake Integration", "category": "Integration", "price": 149.00, "tier": "Add-on"},
    {"product_id": "PROD-010", "name": "Salesforce Connector", "category": "Integration", "price": 149.00, "tier": "Add-on"},
    {"product_id": "PROD-011", "name": "Slack Alerts Module", "category": "Integration", "price": 49.00, "tier": "Add-on"},
    {"product_id": "PROD-012", "name": "SSO & RBAC Module", "category": "Security", "price": 299.00, "tier": "Enterprise"},
    {"product_id": "PROD-013", "name": "Audit Trail & Compliance", "category": "Security", "price": 199.00, "tier": "Enterprise"},
    {"product_id": "PROD-014", "name": "Data Encryption at Rest", "category": "Security", "price": 249.00, "tier": "Enterprise"},
    {"product_id": "PROD-015", "name": "API Access (Standard)", "category": "Developer", "price": 99.00, "tier": "Professional"},
    {"product_id": "PROD-016", "name": "API Access (Unlimited)", "category": "Developer", "price": 299.00, "tier": "Enterprise"},
    {"product_id": "PROD-017", "name": "Embedded Analytics SDK", "category": "Developer", "price": 599.00, "tier": "Premium"},
    {"product_id": "PROD-018", "name": "White-Label Dashboard", "category": "Developer", "price": 899.00, "tier": "Premium"},
    {"product_id": "PROD-019", "name": "Data Warehouse Optimizer", "category": "Performance", "price": 399.00, "tier": "Premium"},
    {"product_id": "PROD-020", "name": "Query Cache Accelerator", "category": "Performance", "price": 199.00, "tier": "Add-on"},
    {"product_id": "PROD-021", "name": "Mobile Analytics App", "category": "Mobile", "price": 99.00, "tier": "Add-on"},
    {"product_id": "PROD-022", "name": "Scheduled Reports Module", "category": "Automation", "price": 149.00, "tier": "Professional"},
    {"product_id": "PROD-023", "name": "Workflow Automation Engine", "category": "Automation", "price": 349.00, "tier": "Premium"},
    {"product_id": "PROD-024", "name": "Data Quality Monitor", "category": "Governance", "price": 249.00, "tier": "Enterprise"},
    {"product_id": "PROD-025", "name": "Schema Change Tracker", "category": "Governance", "price": 149.00, "tier": "Professional"},
    {"product_id": "PROD-026", "name": "Team Collaboration Hub", "category": "Collaboration", "price": 79.00, "tier": "Essential"},
    {"product_id": "PROD-027", "name": "Annotation & Comments", "category": "Collaboration", "price": 49.00, "tier": "Essential"},
    {"product_id": "PROD-028", "name": "Customer 360 Dashboard", "category": "Visualization", "price": 349.00, "tier": "Premium"},
    {"product_id": "PROD-029", "name": "Revenue Analytics Suite", "category": "Visualization", "price": 449.00, "tier": "Premium"},
    {"product_id": "PROD-030", "name": "Usage Analytics Tracker", "category": "Platform", "price": 99.00, "tier": "Essential"},
    {"product_id": "PROD-031", "name": "Natural Language Query", "category": "AI/ML", "price": 299.00, "tier": "Premium"},
    {"product_id": "PROD-032", "name": "Auto-Insight Generator", "category": "AI/ML", "price": 399.00, "tier": "Premium"},
    {"product_id": "PROD-033", "name": "CSV/Excel Importer", "category": "Integration", "price": 29.00, "tier": "Essential"},
    {"product_id": "PROD-034", "name": "Google BigQuery Connector", "category": "Integration", "price": 149.00, "tier": "Add-on"},
    {"product_id": "PROD-035", "name": "HubSpot Integration", "category": "Integration", "price": 99.00, "tier": "Add-on"},
    {"product_id": "PROD-036", "name": "Jira Integration", "category": "Integration", "price": 79.00, "tier": "Add-on"},
    {"product_id": "PROD-037", "name": "Custom Alerts Engine", "category": "Automation", "price": 199.00, "tier": "Professional"},
    {"product_id": "PROD-038", "name": "ETL Pipeline Builder", "category": "Integration", "price": 499.00, "tier": "Premium"},
    {"product_id": "PROD-039", "name": "Multi-Tenant Management", "category": "Platform", "price": 699.00, "tier": "Enterprise"},
    {"product_id": "PROD-040", "name": "Disaster Recovery Module", "category": "Security", "price": 499.00, "tier": "Enterprise"},
    {"product_id": "PROD-041", "name": "Geo Analytics Module", "category": "Visualization", "price": 249.00, "tier": "Premium"},
    {"product_id": "PROD-042", "name": "Funnel Analysis Tool", "category": "Visualization", "price": 199.00, "tier": "Professional"},
    {"product_id": "PROD-043", "name": "Cohort Analysis Module", "category": "AI/ML", "price": 249.00, "tier": "Premium"},
    {"product_id": "PROD-044", "name": "A/B Test Analytics", "category": "AI/ML", "price": 199.00, "tier": "Professional"},
    {"product_id": "PROD-045", "name": "Data Lineage Tracker", "category": "Governance", "price": 299.00, "tier": "Enterprise"},
    {"product_id": "PROD-046", "name": "PII Detection & Masking", "category": "Security", "price": 349.00, "tier": "Enterprise"},
    {"product_id": "PROD-047", "name": "Budget & Cost Tracker", "category": "Platform", "price": 149.00, "tier": "Professional"},
    {"product_id": "PROD-048", "name": "Webhook Manager", "category": "Developer", "price": 79.00, "tier": "Professional"},
    {"product_id": "PROD-049", "name": "Sandbox Environment", "category": "Developer", "price": 199.00, "tier": "Enterprise"},
    {"product_id": "PROD-050", "name": "Premier Support Package", "category": "Support", "price": 999.00, "tier": "Enterprise"},
]

for p in PRODUCT_CATALOG:
    p["avg_rating"] = round(random.uniform(3.2, 4.9), 1)
    p["defect_rate"] = round(random.uniform(0.001, 0.08), 3)
    p["release_date"] = fake.date_between(start_date="-3y", end_date="today").isoformat()
    p["status"] = random.choice(["GA", "GA", "GA", "GA", "Beta", "Deprecated"])

products_df = spark.createDataFrame(PRODUCT_CATALOG)
products_df.write.mode("overwrite").saveAsTable(PRODUCTS_FULL)
print(f"✅ Products: {products_df.count()} rows → {PRODUCTS_FULL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Customers Table
# MAGIC 500 B2B customers with health scores, plan tiers, and churn risk.

# COMMAND ----------

INDUSTRIES = [
    "Financial Services", "Healthcare", "E-Commerce", "SaaS", "Manufacturing",
    "Logistics", "Education", "Media", "Telecom", "Retail", "Insurance",
    "Real Estate", "Energy", "Government", "Non-Profit"
]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
PLAN_TIERS = ["Starter", "Professional", "Enterprise", "Enterprise Plus"]
COMPANY_SIZES = ["1-50", "51-200", "201-500", "501-1000", "1001-5000", "5000+"]

customers = []
for i in range(500):
    cid = f"CUST-{i+1:04d}"
    signup = fake.date_between(start_date="-4y", end_date="-30d")
    plan = random.choices(PLAN_TIERS, weights=[30, 35, 25, 10])[0]

    # Churn risk correlates with plan tier and usage
    base_risk = {"Starter": 0.4, "Professional": 0.25, "Enterprise": 0.12, "Enterprise Plus": 0.08}[plan]
    churn_risk = round(min(1.0, max(0.0, base_risk + random.gauss(0, 0.15))), 2)

    # Health score inversely correlates with churn risk
    health_score = round(min(100, max(0, (1 - churn_risk) * 100 + random.gauss(0, 10))), 1)

    # Lifetime value correlates with plan and tenure
    tenure_months = (datetime.now().date() - signup).days // 30
    base_ltv = {"Starter": 5000, "Professional": 25000, "Enterprise": 80000, "Enterprise Plus": 200000}[plan]
    ltv = round(base_ltv * (tenure_months / 12) * random.uniform(0.6, 1.4), 2)

    customers.append({
        "customer_id": cid,
        "company_name": fake.company(),
        "industry": random.choice(INDUSTRIES),
        "region": random.choice(REGIONS),
        "company_size": random.choice(COMPANY_SIZES),
        "plan_tier": plan,
        "signup_date": signup.isoformat(),
        "monthly_recurring_revenue": round(random.uniform(200, 15000), 2),
        "lifetime_value": ltv,
        "health_score": health_score,
        "churn_risk_score": churn_risk,
        "nps_score": random.randint(-100, 100),
        "support_tier": random.choice(["Standard", "Priority", "Premier"]),
        "csm_assigned": fake.name(),
        "last_login_date": fake.date_between(start_date="-60d", end_date="today").isoformat(),
        "active_users": random.randint(1, 500),
    })

customers_df = spark.createDataFrame(customers)
customers_df.write.mode("overwrite").saveAsTable(CUSTOMERS_FULL)
print(f"✅ Customers: {customers_df.count()} rows → {CUSTOMERS_FULL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Support Tickets Table
# MAGIC 2,000 realistic support tickets with detailed descriptions — the primary vector search target.

# COMMAND ----------

TICKET_TEMPLATES = [
    # Integration issues
    {
        "category": "Integration",
        "subcategory": "Connector Failure",
        "templates": [
            "Our {connector} integration stopped syncing data about {timeframe} ago. We're seeing error code {error_code} in the logs. This is blocking our {team} team from accessing {data_type} data. We've already tried reconnecting and re-authenticating but the issue persists. This is critical as we have a {event} coming up and need the data flowing.",
            "We recently upgraded to {version} and now the {connector} connector throws a timeout error every time we try to pull {data_type}. The sync was working fine before the upgrade. Our {team} team is completely blocked. We've checked our API keys and they're valid. Can you help us troubleshoot this urgently?",
            "The {connector} integration is showing intermittent failures. About {percent}% of our sync jobs fail with '{error_msg}'. This started after we increased our data volume from {old_vol} to {new_vol} records. Is there a rate limit we're hitting? Our ETL pipeline depends on this.",
        ]
    },
    # Performance issues
    {
        "category": "Performance",
        "subcategory": "Slow Queries",
        "templates": [
            "Dashboard load times have increased from {old_time} seconds to {new_time} seconds over the past {timeframe}. We have about {num_users} concurrent users during peak hours. The slowest queries are on the {dashboard_name} dashboard which joins {num_tables} tables. We're on the {plan} plan — do we need to upgrade?",
            "Our {report_name} report is timing out consistently. It used to run in {old_time} seconds but now takes over {new_time} seconds and often fails entirely. The underlying dataset has grown to {data_size} and we suspect the query optimizer isn't handling the {join_type} joins well. This report goes to our {audience} every {frequency}.",
            "We're experiencing severe latency on the {feature_name} feature. API response times have degraded from {old_time}ms to {new_time}ms. Our users are complaining and we're seeing a {percent}% drop in feature adoption. We've ruled out network issues on our end. Please investigate.",
        ]
    },
    # Bug reports
    {
        "category": "Bug",
        "subcategory": "Data Accuracy",
        "templates": [
            "We've found a discrepancy in the {metric_name} metric. Our {dashboard_name} dashboard shows {value1} but when we query the raw data directly, we get {value2}. The difference is about {percent}% which is significant for our {use_case}. This has been reported by multiple users on our team. We need this resolved before our {event}.",
            "The {feature_name} feature is calculating {metric_name} incorrectly when {condition}. Expected result is {value1} but we're getting {value2}. This affects all customers using the {filter_type} filter. We discovered this while preparing our {report_type} report. Attached screenshots showing the discrepancy.",
            "After the latest update, our {chart_type} charts are showing incorrect {data_type} values. Specifically, when we apply the {filter_name} filter with {condition}, the numbers don't match our source system. We verified our source data is correct. This is affecting our credibility with {stakeholder}.",
        ]
    },
    # Feature requests
    {
        "category": "Feature Request",
        "subcategory": "Enhancement",
        "templates": [
            "We'd love to see {feature_desc} in the {module_name} module. Currently we have to {workaround} which takes our team about {time_spent} per {frequency}. We estimate this feature would save us {savings} annually. Several other teams in our organization have expressed the same need. Are there any plans to build this?",
            "Is it possible to add support for {feature_desc}? We're currently using {competitor} for this specific use case because Dataflow doesn't support it natively. We'd prefer to consolidate our tools. This is a blocker for our {team} team's workflow. Happy to discuss requirements in more detail.",
            "Requesting the ability to {feature_desc}. Our {role} users need this for {use_case}. Right now the only option is to {workaround}, which is error-prone and doesn't scale. We're evaluating whether to renew our {plan} plan and this feature is a key factor in our decision.",
        ]
    },
    # Account & billing
    {
        "category": "Account",
        "subcategory": "Billing",
        "templates": [
            "We were charged {amount} this month but our agreement is for {expected_amount}. Looking at our invoice, it appears the {item_name} was billed at the {wrong_rate} rate instead of our contracted {correct_rate} rate. Please correct this and issue a credit. Our finance team needs this resolved by {deadline}.",
            "We need to add {num_users} additional seats to our {plan} plan. Can you provide a quote? Also, we'd like to understand the pricing for upgrading to {target_plan} as we're considering expanding usage to our {team} team. What are the volume discount tiers?",
            "Our annual renewal is coming up in {timeframe} and we want to discuss our options. We currently have {num_seats} seats on {plan}. We're looking to {change_desc}. Can we schedule a call with our account manager? Also, we have some outstanding credits of {amount} that should be applied.",
        ]
    },
    # Access & authentication
    {
        "category": "Access",
        "subcategory": "Authentication",
        "templates": [
            "Multiple users in our {team} team are unable to log in since {timeframe}. They're getting a '{error_msg}' error after SSO redirect. Our IdP ({idp_name}) logs show the SAML assertion is being sent correctly. This is affecting {num_users} users and blocking their work. We've verified our SSO configuration hasn't changed.",
            "We need to set up SCIM provisioning for our {idp_name} integration. We have {num_users} users that need to be synced. Can you provide the SCIM endpoint and documentation? Also, we need to map our custom attribute '{attribute}' to the {field} field in Dataflow. Our security team requires this for compliance.",
            "A user ({user_email}) is locked out of their account after {num_attempts} failed login attempts. They're a {role} and need access urgently for a {event}. Can you unlock the account? Also, can we configure the lockout policy to be {policy_change}? Our current settings are too aggressive.",
        ]
    },
    # Data issues
    {
        "category": "Data",
        "subcategory": "Pipeline",
        "templates": [
            "Our data pipeline from {source} to Dataflow has been failing for the past {timeframe}. The error log shows '{error_msg}'. We process about {volume} records per {frequency} and the backlog is growing. This is impacting our ability to provide {deliverable} to {stakeholder}. We've already checked our source credentials and they're valid.",
            "We're seeing duplicate records in our {table_name} dataset after running the {pipeline_name} pipeline. Approximately {percent}% of records are duplicated. This started after we enabled {feature}. Our deduplication logic uses {key_field} as the primary key. Can you investigate whether this is a known issue?",
            "The scheduled sync for our {source} data stopped triggering at {time}. The last successful run was {last_run}. No error messages in the logs — it simply doesn't execute. We depend on this daily refresh for our {dashboard_name} dashboard that our {audience} reviews every morning.",
        ]
    },
    # Onboarding & training
    {
        "category": "Onboarding",
        "subcategory": "Training",
        "templates": [
            "We just onboarded {num_users} new team members and they're struggling with the {feature_name} feature. Can you provide training materials or schedule a walkthrough? They come from a {background} background and are familiar with {competitor}. We need them productive within {timeframe}.",
            "We're rolling out Dataflow to our {team} department ({num_users} users). We need help creating a training plan and best-practice documentation tailored to {use_case}. Can we get a dedicated onboarding specialist? We're on the {plan} plan. Our go-live date is {deadline}.",
            "Our team is having trouble understanding how to use {feature_name} effectively for {use_case}. The documentation covers the basics but doesn't address our specific workflow of {workflow_desc}. Can you provide a detailed guide or example for this use case? We tried the generic tutorial but it doesn't apply.",
        ]
    },
]

# Filler values for template variables
CONNECTORS = ["Snowflake", "Salesforce", "HubSpot", "BigQuery", "Jira", "PostgreSQL", "MySQL", "Redshift", "S3", "Azure Blob"]
TEAMS = ["analytics", "engineering", "marketing", "sales", "finance", "operations", "product", "data science", "executive", "customer success"]
DATA_TYPES = ["revenue", "user activity", "conversion", "pipeline", "engagement", "transaction", "behavioral", "performance", "attribution", "funnel"]
EVENTS = ["board meeting", "quarterly review", "product launch", "audit", "investor presentation", "annual planning", "client demo"]
ERROR_CODES = ["E-4001", "E-5002", "E-3090", "E-2045", "E-7801", "E-6033", "TIMEOUT-001", "AUTH-403", "SYNC-500", "RATE-429"]
ERROR_MSGS = ["Connection timed out", "Invalid credentials", "Rate limit exceeded", "Schema mismatch detected", "Partition not found", "Memory allocation failed", "SSL handshake failed", "Token expired", "Permission denied", "Deadlock detected"]
DASHBOARD_NAMES = ["Executive Summary", "Sales Pipeline", "Marketing ROI", "Customer Health", "Revenue Analytics", "Product Usage", "Support Metrics", "Churn Prediction"]
FEATURES = ["predictive analytics", "real-time dashboards", "custom report builder", "anomaly detection", "natural language query", "embedded analytics", "cohort analysis", "funnel analysis"]
METRICS = ["conversion rate", "churn rate", "MRR", "ARPU", "DAU/MAU", "LTV", "CAC", "NPS", "pipeline velocity", "retention rate"]
PLANS = ["Starter", "Professional", "Enterprise", "Enterprise Plus"]
IDPS = ["Okta", "Azure AD", "Google Workspace", "OneLogin", "Ping Identity", "Auth0"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
STATUSES = ["Open", "In Progress", "Pending Customer", "Escalated", "Resolved", "Closed"]
CHANNELS = ["Email", "Chat", "Phone", "Portal", "Slack"]

def fill_template(template):
    """Replace placeholders with realistic values."""
    replacements = {
        "{connector}": random.choice(CONNECTORS),
        "{timeframe}": random.choice(["2 hours", "6 hours", "1 day", "2 days", "a week", "3 days"]),
        "{error_code}": random.choice(ERROR_CODES),
        "{error_msg}": random.choice(ERROR_MSGS),
        "{team}": random.choice(TEAMS),
        "{data_type}": random.choice(DATA_TYPES),
        "{event}": random.choice(EVENTS),
        "{version}": f"v{random.randint(2,4)}.{random.randint(0,9)}.{random.randint(0,20)}",
        "{percent}": str(random.randint(5, 45)),
        "{old_vol}": f"{random.randint(10, 100)}K",
        "{new_vol}": f"{random.randint(200, 900)}K",
        "{old_time}": str(random.randint(1, 5)),
        "{new_time}": str(random.randint(15, 120)),
        "{num_users}": str(random.randint(5, 200)),
        "{dashboard_name}": random.choice(DASHBOARD_NAMES),
        "{num_tables}": str(random.randint(3, 12)),
        "{plan}": random.choice(PLANS),
        "{report_name}": random.choice(["Monthly Revenue", "Churn Analysis", "Pipeline Forecast", "Customer Segmentation", "Product Adoption", "QBR Summary"]),
        "{data_size}": f"{random.randint(1, 50)}M rows",
        "{join_type}": random.choice(["LEFT OUTER", "CROSS", "FULL OUTER", "multi-table"]),
        "{audience}": random.choice(["C-suite", "board", "investors", "department heads", "clients", "VP of Sales"]),
        "{frequency}": random.choice(["Monday morning", "daily", "weekly", "month-end", "quarterly"]),
        "{feature_name}": random.choice(FEATURES),
        "{metric_name}": random.choice(METRICS),
        "{value1}": f"${random.randint(10, 500)}K" if random.random() > 0.5 else f"{random.randint(10, 95)}%",
        "{value2}": f"${random.randint(10, 500)}K" if random.random() > 0.5 else f"{random.randint(10, 95)}%",
        "{use_case}": random.choice(["financial reporting", "investor updates", "customer segmentation", "pricing optimization", "demand forecasting", "operational planning"]),
        "{condition}": random.choice(["date range spans multiple months", "currency is non-USD", "data contains null values", "timezone is non-UTC", "users have multiple roles"]),
        "{filter_type}": random.choice(["date range", "region", "product category", "customer segment", "cohort"]),
        "{filter_name}": random.choice(["date picker", "region selector", "segment filter", "custom dimension"]),
        "{report_type}": random.choice(["quarterly", "annual", "board", "investor", "compliance"]),
        "{chart_type}": random.choice(["bar", "line", "area", "scatter", "waterfall", "funnel"]),
        "{stakeholder}": random.choice(["our CFO", "the board", "investors", "our clients", "the VP of Sales"]),
        "{feature_desc}": random.choice(["custom calculated fields in dashboards", "multi-currency support", "row-level security on shared reports", "automatic PDF export scheduling", "Slack bot for natural language queries", "data lineage visualization", "custom role-based permissions", "API webhook notifications"]),
        "{module_name}": random.choice(["dashboard", "reporting", "analytics", "integration", "security", "automation"]),
        "{workaround}": random.choice(["export to Excel and calculate manually", "use a third-party tool", "write custom SQL queries", "have our engineer build a workaround", "manually update a spreadsheet"]),
        "{time_spent}": random.choice(["3 hours", "5 hours", "a full day", "half a day", "2 days"]),
        "{savings}": f"${random.randint(10, 200)}K",
        "{competitor}": random.choice(["Tableau", "Looker", "Power BI", "Metabase", "Amplitude", "Mixpanel"]),
        "{role}": random.choice(["analyst", "data engineer", "admin", "executive", "product manager", "marketing"]),
        "{amount}": f"${random.randint(1, 50)},{random.randint(100, 999)}.{random.randint(10, 99)}",
        "{expected_amount}": f"${random.randint(1, 30)},{random.randint(100, 999)}.00",
        "{item_name}": random.choice(["API overage", "additional seats", "premium support", "storage tier", "compute credits"]),
        "{wrong_rate}": random.choice(["standard", "list price", "on-demand", "non-discounted"]),
        "{correct_rate}": random.choice(["enterprise contracted", "volume discounted", "negotiated", "promotional"]),
        "{deadline}": fake.date_between(start_date="+1d", end_date="+30d").isoformat(),
        "{num_seats}": str(random.randint(10, 500)),
        "{target_plan}": random.choice(["Professional", "Enterprise", "Enterprise Plus"]),
        "{change_desc}": random.choice(["reduce seats by 20%", "upgrade to Enterprise", "add API access", "consolidate to a single plan", "add premium support"]),
        "{idp_name}": random.choice(IDPS),
        "{num_attempts}": str(random.randint(3, 10)),
        "{user_email}": fake.email(),
        "{attribute}": random.choice(["department", "cost_center", "manager", "employee_id"]),
        "{field}": random.choice(["group", "team", "role", "custom_attribute"]),
        "{policy_change}": random.choice(["10 attempts before lockout", "30-minute lockout instead of 24 hours", "admin-only unlock", "progressive delays"]),
        "{source}": random.choice(["Snowflake", "BigQuery", "S3", "PostgreSQL", "Kafka", "Azure Data Lake"]),
        "{volume}": f"{random.randint(100, 900)}K",
        "{deliverable}": random.choice(["daily KPI reports", "real-time dashboards", "automated alerts", "executive summaries"]),
        "{table_name}": random.choice(["user_events", "transactions", "sessions", "page_views", "conversions"]),
        "{pipeline_name}": random.choice(["daily_sync", "hourly_refresh", "full_load", "incremental_update"]),
        "{feature}": random.choice(["parallel processing", "incremental sync", "schema evolution", "auto-scaling"]),
        "{key_field}": random.choice(["event_id", "transaction_id", "session_id", "user_id + timestamp"]),
        "{time}": random.choice(["6:00 AM UTC", "midnight", "9:00 PM EST", "3:00 AM UTC"]),
        "{last_run}": fake.date_between(start_date="-7d", end_date="-1d").isoformat(),
        "{background}": random.choice(["Excel/spreadsheet", "Tableau", "SQL", "Python", "business analyst"]),
        "{workflow_desc}": random.choice(["pulling data from 3 sources, joining, and building weekly reports", "creating customer segments based on behavioral data", "building real-time marketing attribution models", "monitoring SLA compliance across multiple systems"]),
    }

    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


tickets = []
customer_ids = [c["customer_id"] for c in customers]

for i in range(2000):
    template_group = random.choice(TICKET_TEMPLATES)
    template = random.choice(template_group["templates"])
    description = fill_template(template)

    cid = random.choice(customer_ids)
    created = fake.date_time_between(start_date="-1y", end_date="now")
    priority = random.choices(PRIORITIES, weights=[5, 20, 50, 25])[0]
    status = random.choices(STATUSES, weights=[15, 25, 10, 5, 30, 15])[0]

    resolved_at = None
    resolution_hours = None
    if status in ("Resolved", "Closed"):
        resolution_hours = random.uniform(0.5, 168)  # 30 min to 7 days
        resolved_at = (created + timedelta(hours=resolution_hours)).isoformat()

    subject_prefixes = {
        "Integration": ["Connector failure:", "Sync issue:", "Integration error:"],
        "Performance": ["Slow dashboard:", "Query timeout:", "Performance degradation:"],
        "Bug": ["Data mismatch:", "Incorrect calculation:", "Display error:"],
        "Feature Request": ["Feature request:", "Enhancement needed:", "Requesting:"],
        "Account": ["Billing inquiry:", "Account question:", "Seat adjustment:"],
        "Access": ["Login issue:", "SSO problem:", "Access denied:"],
        "Data": ["Pipeline failure:", "Data sync issue:", "Missing data:"],
        "Onboarding": ["Training request:", "Onboarding help:", "Need guidance:"],
    }
    prefix = random.choice(subject_prefixes.get(template_group["category"], ["Issue:"]))
    subject = f"{prefix} {fake.sentence(nb_words=6)}"

    tickets.append({
        "ticket_id": f"TKT-{i+1:05d}",
        "customer_id": cid,
        "subject": subject,
        "description": description,
        "category": template_group["category"],
        "subcategory": template_group["subcategory"],
        "priority": priority,
        "status": status,
        "channel": random.choice(CHANNELS),
        "assigned_agent": fake.name(),
        "created_at": created.isoformat(),
        "resolved_at": resolved_at,
        "resolution_hours": round(resolution_hours, 2) if resolution_hours else None,
        "satisfaction_rating": random.choice([1, 2, 3, 4, 5, None, None]),
        "first_response_minutes": round(random.uniform(5, 480), 1),
        "num_replies": random.randint(1, 25),
        "tags": ",".join(random.sample(["urgent", "escalated", "enterprise", "regression", "sla-breach", "vip", "renewal-risk", "product-feedback"], k=random.randint(1, 3))),
    })

tickets_df = spark.createDataFrame(tickets)
tickets_df.write.mode("overwrite").saveAsTable(TICKETS_FULL)
print(f"✅ Support Tickets: {tickets_df.count()} rows → {TICKETS_FULL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Orders Table
# MAGIC 3,000 subscription and add-on purchase records.

# COMMAND ----------

product_ids = [p["product_id"] for p in PRODUCT_CATALOG]

orders = []
for i in range(3000):
    cid = random.choice(customer_ids)
    pid = random.choice(product_ids)
    product = next(p for p in PRODUCT_CATALOG if p["product_id"] == pid)
    order_date = fake.date_between(start_date="-2y", end_date="today")

    # Price varies with discounts
    discount = random.choice([0, 0, 0, 0.1, 0.15, 0.2, 0.25])
    amount = round(product["price"] * (1 - discount), 2)

    orders.append({
        "order_id": f"ORD-{i+1:05d}",
        "customer_id": cid,
        "product_id": pid,
        "product_name": product["name"],
        "order_date": order_date.isoformat(),
        "amount": amount,
        "discount_percent": int(discount * 100),
        "order_type": random.choice(["New", "Renewal", "Upgrade", "Add-on"]),
        "payment_status": random.choices(["Paid", "Pending", "Overdue", "Refunded"], weights=[80, 10, 7, 3])[0],
        "contract_term_months": random.choice([1, 12, 12, 12, 24, 36]),
    })

orders_df = spark.createDataFrame(orders)
orders_df.write.mode("overwrite").saveAsTable(ORDERS_FULL)
print(f"✅ Orders: {orders_df.count()} rows → {ORDERS_FULL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Customer Interactions Table
# MAGIC 5,000 multi-channel interaction records with sentiment scores.

# COMMAND ----------

INTERACTION_TYPES = ["Support Call", "Onboarding Session", "QBR Meeting", "Training Webinar",
                     "Feature Demo", "Escalation Call", "Check-in", "Renewal Discussion",
                     "Upsell Conversation", "Bug Report Follow-up"]

interactions = []
for i in range(5000):
    cid = random.choice(customer_ids)
    ts = fake.date_time_between(start_date="-1y", end_date="now")
    channel = random.choice(["Email", "Phone", "Video Call", "Chat", "In-Person", "Slack"])
    interaction_type = random.choice(INTERACTION_TYPES)

    # Sentiment correlates with interaction type
    base_sentiment = {
        "Support Call": 0.3, "Onboarding Session": 0.6, "QBR Meeting": 0.5,
        "Training Webinar": 0.7, "Feature Demo": 0.8, "Escalation Call": 0.1,
        "Check-in": 0.6, "Renewal Discussion": 0.4, "Upsell Conversation": 0.5,
        "Bug Report Follow-up": 0.3
    }

    sentiment = round(min(1.0, max(-1.0, base_sentiment[interaction_type] + random.gauss(0, 0.3))), 2)

    interactions.append({
        "interaction_id": f"INT-{i+1:05d}",
        "customer_id": cid,
        "interaction_type": interaction_type,
        "channel": channel,
        "timestamp": ts.isoformat(),
        "duration_minutes": round(random.uniform(5, 90), 1),
        "sentiment_score": sentiment,
        "csat_score": random.choice([1, 2, 3, 4, 5, None]),
        "resolution_achieved": random.choice([True, True, True, False]),
        "follow_up_required": random.choice([True, False, False]),
        "agent_name": fake.name(),
        "notes_summary": fake.sentence(nb_words=12),
    })

interactions_df = spark.createDataFrame(interactions)
interactions_df.write.mode("overwrite").saveAsTable(INTERACTIONS_FULL)
print(f"✅ Interactions: {interactions_df.count()} rows → {INTERACTIONS_FULL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Product Reviews Table
# MAGIC 1,500 written product reviews — second vector search target for semantic analysis.

# COMMAND ----------

REVIEW_TEMPLATES = [
    # Positive reviews
    "We've been using {product} for {duration} and it's been {positive_adj} for our {team} team. The {feature} is particularly {positive_adj2}. Compared to {competitor}, {product} {advantage}. Our {metric} improved by {percent}% since adopting it. Would highly recommend for teams doing {use_case}.",
    "{product} transformed how our {team} department handles {use_case}. Setup took about {setup_time} and the learning curve was {difficulty}. The best part is {feature} — it saves us {time_saved} every {frequency}. Support has been {support_quality}. {stars}/5 for sure.",
    "After evaluating {competitor} and {competitor2}, we chose {product} and haven't looked back. The {feature} alone justifies the price. Our {num_users} users adopted it within {adoption_time}. The ROI has been {roi_desc}. Minor wish: {minor_complaint}.",

    # Mixed reviews
    "{product} does most things well but has some rough edges. The {feature} works great for {use_case}, but {complaint}. We've submitted {num_tickets} support tickets about this. Support response time is {response_time}. For the price point ({price_opinion}), I expected {expectation}. Rating: {stars}/5.",
    "We've been on {product} for {duration}. Pros: {feature} is {positive_adj}, the {feature2} is useful for {use_case}. Cons: {complaint}, and the {feature3} needs work. It's good for {good_for} but not ideal for {not_ideal_for}. We're on the {plan} plan and considering {action}.",

    # Negative reviews
    "Disappointed with {product}. We signed up expecting {expectation} but instead got {reality}. The {feature} is {negative_adj} — it {complaint}. We've had {num_tickets} unresolved tickets open for {duration2}. Considering switching to {competitor}. Our team of {num_users} is frustrated. {stars}/5.",
    "{product} promised {expectation} but delivered {reality}. The {feature} crashes {frequency} and {complaint}. Support takes {response_time} to respond and the solutions are often {solution_quality}. We're paying {price_opinion} for something that barely works. Looking at alternatives now.",
]

POSITIVE_ADJS = ["transformative", "a game-changer", "incredibly valuable", "a huge time-saver", "exceptional", "rock-solid", "intuitive", "powerful"]
NEGATIVE_ADJS = ["unreliable", "clunky", "frustrating", "buggy", "slow", "confusing", "poorly designed", "inconsistent"]
COMPETITORS = ["Tableau", "Looker", "Power BI", "Metabase", "Amplitude", "Mixpanel", "Mode", "Sisense", "ThoughtSpot", "Domo"]
ADVANTAGES = ["is far more intuitive", "handles scale better", "has better integrations", "offers superior real-time capabilities", "is more cost-effective", "has better documentation"]
COMPLAINTS = ["the export functionality is limited", "performance degrades with large datasets", "the mobile experience needs work", "custom formulas are hard to debug", "the API rate limits are too restrictive", "some visualizations render incorrectly"]

def fill_review_template(template, product):
    competitors = random.sample(COMPETITORS, 2)
    replacements = {
        "{product}": product["name"],
        "{duration}": random.choice(["3 months", "6 months", "a year", "18 months", "2 years"]),
        "{duration2}": random.choice(["2 weeks", "a month", "6 weeks", "2 months"]),
        "{positive_adj}": random.choice(POSITIVE_ADJS),
        "{positive_adj2}": random.choice(POSITIVE_ADJS),
        "{negative_adj}": random.choice(NEGATIVE_ADJS),
        "{team}": random.choice(TEAMS),
        "{feature}": random.choice(FEATURES),
        "{feature2}": random.choice(FEATURES),
        "{feature3}": random.choice(FEATURES),
        "{competitor}": competitors[0],
        "{competitor2}": competitors[1],
        "{advantage}": random.choice(ADVANTAGES),
        "{metric}": random.choice(METRICS),
        "{percent}": str(random.randint(10, 60)),
        "{use_case}": random.choice(["financial reporting", "customer analytics", "marketing attribution", "operational dashboards", "executive reporting", "data exploration"]),
        "{setup_time}": random.choice(["2 hours", "half a day", "a day", "a couple days", "a week"]),
        "{difficulty}": random.choice(["gentle", "moderate", "steep at first but manageable", "surprisingly easy", "a bit steep"]),
        "{time_saved}": random.choice(["5 hours", "10 hours", "a full day", "2 days", "several hours"]),
        "{frequency}": random.choice(["week", "month", "sprint", "quarter"]),
        "{support_quality}": random.choice(["excellent", "responsive", "hit or miss", "slow but helpful", "outstanding"]),
        "{stars}": str(random.randint(1, 5)),
        "{minor_complaint}": random.choice(["I wish the mobile app was more polished", "PDF exports could be better formatted", "would love more chart types", "the learning curve for advanced features is steep"]),
        "{complaint}": random.choice(COMPLAINTS),
        "{num_tickets}": str(random.randint(2, 15)),
        "{response_time}": random.choice(["under an hour", "within 4 hours", "24 hours", "2-3 days", "over a week"]),
        "{price_opinion}": random.choice(["fair", "a bit steep", "very expensive for what you get", "reasonable", "premium pricing"]),
        "{expectation}": random.choice(["enterprise-grade reliability", "Tableau-level visualizations", "real-time analytics", "seamless integrations", "better performance"]),
        "{reality}": random.choice(["frequent downtime", "basic charts", "delayed data refreshes", "constant connector issues", "mediocre performance"]),
        "{num_users}": str(random.randint(5, 100)),
        "{adoption_time}": random.choice(["a week", "two weeks", "a month", "a few days"]),
        "{roi_desc}": random.choice(["incredible — paid for itself in 2 months", "solid — clear improvement in efficiency", "significant — reduced manual work by 60%"]),
        "{plan}": random.choice(PLANS),
        "{action}": random.choice(["upgrading", "downgrading", "not renewing", "expanding to more teams"]),
        "{good_for}": random.choice(["basic reporting", "small teams", "standard dashboards", "simple queries"]),
        "{not_ideal_for}": random.choice(["complex analytics", "real-time data", "large-scale deployments", "custom visualizations"]),
        "{solution_quality}": random.choice(["generic and unhelpful", "copy-pasted from docs", "actually helpful", "partial fixes at best"]),
    }

    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


reviews = []
for i in range(1500):
    product = random.choice(PRODUCT_CATALOG)
    cid = random.choice(customer_ids)
    template = random.choice(REVIEW_TEMPLATES)
    review_text = fill_review_template(template, product)

    # Extract star rating from review if present, else random
    rating = random.randint(1, 5)
    if "5/5" in review_text:
        rating = 5
    elif "4/5" in review_text:
        rating = 4
    elif "3/5" in review_text:
        rating = 3
    elif "2/5" in review_text:
        rating = 2
    elif "1/5" in review_text:
        rating = 1

    reviews.append({
        "review_id": f"REV-{i+1:05d}",
        "customer_id": cid,
        "product_id": product["product_id"],
        "product_name": product["name"],
        "review_text": review_text,
        "rating": rating,
        "review_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
        "verified_purchase": random.choice([True, True, True, False]),
        "helpful_votes": random.randint(0, 50),
    })

reviews_df = spark.createDataFrame(reviews)
reviews_df.write.mode("overwrite").saveAsTable(FEEDBACK_FULL)
print(f"✅ Product Reviews: {reviews_df.count()} rows → {FEEDBACK_FULL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 70)
print("  DATA GENERATION COMPLETE")
print("=" * 70)
print(f"""
Tables created in {TARGET_CATALOG}.{TARGET_SCHEMA}:

  1. {PRODUCTS_FULL:<55} {len(PRODUCT_CATALOG):>6} rows
  2. {CUSTOMERS_FULL:<55} {len(customers):>6} rows
  3. {TICKETS_FULL:<55} {len(tickets):>6} rows
  4. {ORDERS_FULL:<55} {len(orders):>6} rows
  5. {INTERACTIONS_FULL:<55} {len(interactions):>6} rows
  6. {FEEDBACK_FULL:<55} {len(reviews):>6} rows

Total rows: {len(PRODUCT_CATALOG) + len(customers) + len(tickets) + len(orders) + len(interactions) + len(reviews):,}

Next steps:
  → Run 01-vector-search/setup-vector-search to create semantic search indexes
  → Run 02-uc-functions/register-tools to register Unity Catalog agent tools
  → Run 03-multi-agent/supervisor-setup to create the AgentBricks supervisor
""")
