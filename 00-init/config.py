# Databricks notebook source
# MAGIC %md
# MAGIC # Configuration
# MAGIC **Enterprise Customer Support Intelligence System**
# MAGIC
# MAGIC Central configuration for all notebooks. Update these values to match your Databricks environment.

# COMMAND ----------

# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

# Unity Catalog location for all tables and functions
TARGET_CATALOG = "workspace"
TARGET_SCHEMA = "customer_support_intelligence"
TARGET_VOLUME = "raw_data"

# Bronze layer schema (for vector search cloned tables)
TARGET_BRONZE_SCHEMA = "customer_support_intelligence_bronze"

# Table names
TICKETS_TABLE = "support_tickets"
CUSTOMERS_TABLE = "customers"
ORDERS_TABLE = "orders"
PRODUCTS_TABLE = "products"
INTERACTIONS_TABLE = "customer_interactions"
FEEDBACK_TABLE = "product_reviews"

# Vector search configuration
VS_ENDPOINT_NAME_PREFIX = "csi_tickets_endpoint"
VS_INDEX_NAME_PREFIX = "csi_tickets_index"
REVIEWS_VS_INDEX_NAME_PREFIX = "csi_reviews_index"

# Embedding model (Databricks-hosted)
EMBEDDING_MODEL = "databricks-gte-large-en"

# Agent names (for AgentBricks)
TICKET_ANALYST_AGENT = "csi-ticket-analyst"
SUPERVISOR_AGENT = "csi-operations-supervisor"

# ============================================================
# DERIVED PATHS (do not edit)
# ============================================================
TICKETS_FULL = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{TICKETS_TABLE}"
CUSTOMERS_FULL = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{CUSTOMERS_TABLE}"
ORDERS_FULL = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{ORDERS_TABLE}"
PRODUCTS_FULL = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{PRODUCTS_TABLE}"
INTERACTIONS_FULL = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{INTERACTIONS_TABLE}"
FEEDBACK_FULL = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{FEEDBACK_TABLE}"

print("✅ Configuration loaded successfully")
print(f"   Catalog:  {TARGET_CATALOG}")
print(f"   Schema:   {TARGET_SCHEMA}")
print(f"   Bronze:   {TARGET_BRONZE_SCHEMA}")
