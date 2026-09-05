import pytest
from app.retrieval.sql_agent import sql_agent
from app.database.sql_store import sql_store
import pandas as pd

def test_sql_validator_rejects_mutations():
    forbidden_queries = [
        "DROP TABLE users;",
        "DELETE FROM orders WHERE id = 1;",
        "UPDATE sales SET revenue = 0;",
        "INSERT INTO products VALUES (1, 'hack');",
        "ALTER TABLE customers ADD COLUMN secret TEXT;",
        "TRUNCATE TABLE logs;",
        "ATTACH DATABASE 'hack.db' AS hack;",
        "PRAGMA table_info(sales);"
    ]
    for q in forbidden_queries:
        is_valid, sanitized, msg = sql_agent.validate_sql(q)
        assert not is_valid, f"Expected {q} to be rejected, but passed with: {msg}"

def test_sql_validator_allows_and_limits_select():
    valid_query = "SELECT region, SUM(revenue) FROM sales GROUP BY region"
    is_valid, sanitized, msg = sql_agent.validate_sql(valid_query)
    assert is_valid
    assert "LIMIT 100" in sanitized

def test_sql_store_load_and_read_only_execution(tmp_path):
    # Create sample dataframe
    df = pd.DataFrame({
        "order_id": [101, 102, 103],
        "customer": ["Acme Corp", "Beta Inc", "Gamma LLC"],
        "revenue": [1500.50, 2300.00, 450.00],
        "country": ["Germany", "France", "Germany"]
    })

    table_name, cols = sql_store.load_dataframe(df, "test_orders", add_row_id=True)
    assert "row_id" in cols
    assert "revenue" in cols

    # Read-only query execution
    query = f"SELECT country, SUM(revenue) as total_rev FROM {table_name} GROUP BY country ORDER BY total_rev DESC"
    is_valid, safe_sql, _ = sql_agent.validate_sql(query)
    assert is_valid

    rows, columns = sql_store.execute_read_only(safe_sql)
    assert len(rows) == 2
    assert rows[0]["country"] == "France"
    assert rows[0]["total_rev"] == 2300.00
    assert rows[1]["country"] == "Germany"
    assert rows[1]["total_rev"] == 1950.50
