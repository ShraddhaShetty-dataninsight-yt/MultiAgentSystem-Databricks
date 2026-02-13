# Databricks notebook source
# MAGIC %md
# MAGIC # Vector Search Setup
# MAGIC **Enterprise Customer Support Intelligence System**
# MAGIC
# MAGIC This notebook creates two vector search indexes for semantic search:
# MAGIC
# MAGIC | Index | Source | Use Case |
# MAGIC |-------|--------|----------|
# MAGIC | **Tickets Index** | `support_tickets.description` | Find similar past tickets, identify patterns |
# MAGIC | **Reviews Index** | `product_reviews.review_text` | Analyze product sentiment, find feedback themes |
# MAGIC
# MAGIC ### How it works
# MAGIC 1. Clone source tables to bronze layer (enables Change Data Feed)
# MAGIC 2. Create a Vector Search endpoint (compute layer)
# MAGIC 3. Create Delta Sync indexes (auto-embeds text using `databricks-gte-large-en`)
# MAGIC 4. Test with semantic queries

# COMMAND ----------

# MAGIC %pip install -U --quiet databricks-sdk==0.49.0 databricks-vectorsearch==0.55
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run "../00-init/config"

# COMMAND ----------

import time
import datetime
from databricks.vector_search.client import VectorSearchClient

# Unique timestamp for this run (prevents name collisions during experimentation)
timestamp = str(int(time.time()))

# Endpoint and index names
endpoint_name = f"{VS_ENDPOINT_NAME_PREFIX}_{timestamp}"
tickets_index_name = f"{TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}.{VS_INDEX_NAME_PREFIX}_{timestamp}"
reviews_index_name = f"{TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}.{REVIEWS_VS_INDEX_NAME_PREFIX}_{timestamp}"

# Cloned table names (bronze layer)
tickets_bronze = f"{TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}.support_tickets_bronze"
reviews_bronze = f"{TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}.product_reviews_bronze"

print(f"Endpoint:      {endpoint_name}")
print(f"Tickets Index: {tickets_index_name}")
print(f"Reviews Index: {reviews_index_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Prepare Bronze Tables
# MAGIC Clone source tables and enable Change Data Feed (required for Delta Sync indexes).

# COMMAND ----------

# Ensure bronze schema exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}")

# Clone support tickets
spark.sql(f"""
CREATE OR REPLACE TABLE {tickets_bronze}
CLONE {TICKETS_FULL}
""")

spark.sql(f"""
ALTER TABLE {tickets_bronze}
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

print(f"✅ Tickets bronze table ready: {tickets_bronze}")

# Clone product reviews
spark.sql(f"""
CREATE OR REPLACE TABLE {reviews_bronze}
CLONE {FEEDBACK_FULL}
""")

spark.sql(f"""
ALTER TABLE {reviews_bronze}
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

print(f"✅ Reviews bronze table ready: {reviews_bronze}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Vector Search Endpoint
# MAGIC
# MAGIC This provisions the compute infrastructure for vector search.
# MAGIC **Takes 15-25 minutes** to provision.

# COMMAND ----------

vsc = VectorSearchClient(disable_notice=True)

print(f"Creating Vector Search endpoint: {endpoint_name}")
print("This takes 15-25 minutes to provision...\n")

try:
    endpoint = vsc.create_endpoint_and_wait(
        name=endpoint_name,
        endpoint_type="STANDARD",
        verbose=True,
        timeout=datetime.timedelta(seconds=3600),
    )
    print(f"\n✅ Endpoint ready: {endpoint_name}")
except Exception as e:
    print(f"\n❌ Error creating endpoint: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create Vector Search Indexes
# MAGIC
# MAGIC ### Tickets Index
# MAGIC - **Primary Key**: `ticket_id`
# MAGIC - **Embedding Source**: `description` (the full ticket text)
# MAGIC - **Model**: `databricks-gte-large-en` (1024-dim embeddings)
# MAGIC - **Pipeline**: `TRIGGERED` (manual sync control)

# COMMAND ----------

# --- Tickets Index ---
try:
    tickets_idx = vsc.create_delta_sync_index(
        endpoint_name=endpoint_name,
        index_name=tickets_index_name,
        source_table_name=tickets_bronze,
        pipeline_type="TRIGGERED",
        primary_key="ticket_id",
        embedding_source_column="description",
        embedding_model_endpoint_name=EMBEDDING_MODEL,
    )
    print(f"✅ Tickets index created: {tickets_index_name}")
except Exception as e:
    print(f"❌ Error creating tickets index: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ### Reviews Index
# MAGIC - **Primary Key**: `review_id`
# MAGIC - **Embedding Source**: `review_text`

# COMMAND ----------

# --- Reviews Index ---
try:
    reviews_idx = vsc.create_delta_sync_index(
        endpoint_name=endpoint_name,
        index_name=reviews_index_name,
        source_table_name=reviews_bronze,
        pipeline_type="TRIGGERED",
        primary_key="review_id",
        embedding_source_column="review_text",
        embedding_model_endpoint_name=EMBEDDING_MODEL,
    )
    print(f"✅ Reviews index created: {reviews_index_name}")
except Exception as e:
    print(f"❌ Error creating reviews index: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Test Semantic Search
# MAGIC Wait for indexes to build embeddings, then run semantic queries.

# COMMAND ----------

print("Waiting 120 seconds for indexes to build embeddings...")
time.sleep(120)
print("✅ Ready to test!")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 1: Find tickets about data pipeline failures affecting executive reporting

# COMMAND ----------

print("Test 1: Tickets about pipeline failures affecting executive reporting\n")

try:
    results1 = spark.sql(f"""
    SELECT
        search_score,
        ticket_id,
        customer_id,
        subject,
        description,
        category,
        priority,
        status
    FROM VECTOR_SEARCH(
        index => '{tickets_index_name}',
        query_text => 'data pipeline failing causing missing data in executive dashboards and board reports',
        num_results => 5
    )
    ORDER BY search_score DESC
    """)
    print("Top 5 semantically similar tickets:")
    display(results1)
except Exception as e:
    print(f"Index still building. Wait a few minutes and re-run this cell.\nError: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 2: Find tickets from customers frustrated with slow performance

# COMMAND ----------

print("Test 2: Frustrated customers experiencing slow performance\n")

try:
    results2 = spark.sql(f"""
    SELECT
        search_score,
        ticket_id,
        customer_id,
        subject,
        description,
        priority,
        satisfaction_rating
    FROM VECTOR_SEARCH(
        index => '{tickets_index_name}',
        query_text => 'frustrated customer dashboard extremely slow timeout performance degradation',
        num_results => 5
    )
    ORDER BY search_score DESC
    """)
    print("Top 5 semantically similar tickets:")
    display(results2)
except Exception as e:
    print(f"Index still building. Wait a few minutes and re-run this cell.\nError: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 3: Find positive product reviews about AI/ML features

# COMMAND ----------

print("Test 3: Positive reviews about AI and predictive analytics\n")

try:
    results3 = spark.sql(f"""
    SELECT
        search_score,
        review_id,
        product_name,
        review_text,
        rating
    FROM VECTOR_SEARCH(
        index => '{reviews_index_name}',
        query_text => 'amazing predictive analytics machine learning AI features transformed our business',
        num_results => 5
    )
    ORDER BY search_score DESC
    """)
    print("Top 5 semantically similar reviews:")
    display(results3)
except Exception as e:
    print(f"Index still building. Wait a few minutes and re-run this cell.\nError: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test 4: Find reviews complaining about integrations

# COMMAND ----------

print("Test 4: Reviews complaining about connector and integration issues\n")

try:
    results4 = spark.sql(f"""
    SELECT
        search_score,
        review_id,
        product_name,
        review_text,
        rating
    FROM VECTOR_SEARCH(
        index => '{reviews_index_name}',
        query_text => 'integration connector broken sync failing data not flowing unreliable',
        num_results => 5
    )
    ORDER BY search_score DESC
    """)
    print("Top 5 semantically similar reviews:")
    display(results4)
except Exception as e:
    print(f"Index still building. Wait a few minutes and re-run this cell.\nError: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Index Names for Downstream Notebooks
# MAGIC Store the names so the supervisor notebook can reference them.

# COMMAND ----------

# Store for use by other notebooks
spark.sql(f"""
CREATE OR REPLACE TABLE {TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}._vector_search_config AS
SELECT
    '{endpoint_name}' AS endpoint_name,
    '{tickets_index_name}' AS tickets_index_name,
    '{reviews_index_name}' AS reviews_index_name,
    current_timestamp() AS created_at
""")

print(f"""
{'=' * 70}
  VECTOR SEARCH SETUP COMPLETE
{'=' * 70}

  Endpoint:      {endpoint_name}
  Tickets Index: {tickets_index_name}
  Reviews Index: {reviews_index_name}

  Config saved to: {TARGET_CATALOG}.{TARGET_BRONZE_SCHEMA}._vector_search_config

  Next step: Run 02-uc-functions/register-tools
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cleanup (Run when done)
# MAGIC Uncomment and run the cell below to delete the endpoint and indexes.

# COMMAND ----------

# # UNCOMMENT TO CLEAN UP
# from databricks.sdk import WorkspaceClient
#
# w = WorkspaceClient()
#
# print("Cleaning up vector search resources...")
#
# # Delete indexes
# for idx_name in [tickets_index_name, reviews_index_name]:
#     try:
#         w.vector_search_indexes.delete_index(idx_name)
#         print(f"  Deleted index: {idx_name}")
#     except Exception as e:
#         print(f"  Could not delete index {idx_name}: {e}")
#
# # Delete endpoint
# try:
#     w.vector_search_endpoints.delete_endpoint(endpoint_name)
#     print(f"  Deleted endpoint: {endpoint_name}")
# except Exception as e:
#     print(f"  Could not delete endpoint: {e}")
#
# print("\n✅ Cleanup complete!")
