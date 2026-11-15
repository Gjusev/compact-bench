"""SQL-over-sqlite tasks: deterministic in-memory database per run."""

import sqlite3

from .base import Task

_CUSTOMERS = [
    (1, "Ada", "EU"),
    (2, "Lin", "EU"),
    (3, "Mo", "APAC"),
    (4, "Zoe", "EU"),
]
_ORDERS = [
    # id, customer_id, amount, discount
    (101, 1, 120.0, 5.0),
    (102, 1, 80.5, None),
    (103, 2, 200.0, 10.0),
    (104, 3, 95.25, None),
    (105, 4, 75.0, None),
    (106, 3, 30.0, 0.0),
    (107, 2, 60.0, None),
]


class SqlEnv:
    """In-memory sqlite database. Deterministic: fixed seed data above."""

    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        cur = self.db.cursor()
        cur.execute("CREATE TABLE customers (id INTEGER, name TEXT, region TEXT)")
        cur.execute(
            "CREATE TABLE orders (id INTEGER, customer_id INTEGER, amount REAL, discount REAL)"
        )
        cur.executemany("INSERT INTO customers VALUES (?,?,?)", _CUSTOMERS)
        cur.executemany("INSERT INTO orders VALUES (?,?,?,?)", _ORDERS)
        self.db.commit()

    def close(self):
        self.db.close()

    def execute(self, action: str) -> str:
        if action.startswith("sql:"):
            query = action[len("sql:"):].strip()
            try:
                cur = self.db.execute(query)
            except sqlite3.Error as exc:
                return "SQL ERROR: %s" % exc
            if cur.description is None:
                return "OK (no result set)"
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(20)
            out = [" | ".join(cols)]
            out.extend(" | ".join("" if v is None else str(v) for v in row) for row in rows)
            if len(rows) == 20:
                out.append("... (truncated at 20 rows)")
            return "\n".join(out)
        return "UNKNOWN ACTION: %s" % action[:40]

    def query_scalar(self, query):
        return self.db.execute(query).fetchone()[0]


def _answer_check(expected):
    def check(env, answer):
        norm = (answer or "").strip().lower()
        if norm == str(expected).strip().lower():
            return True, "answer matched"
        return False, "answer %r != expected %r" % (answer, expected)

    return check


def _make(name, prompt, plan, expected):
    return Task(
        name=name,
        category="sql",
        prompt=prompt,
        plan=plan,
        build_env=SqlEnv,
        check=_answer_check(expected),
    )


ALL_SQL_TASKS = [
    _make(
        "sql-total-revenue",
        (
            "DATABASE: shop.sqlite (tables: customers, orders — inspect with SQL).\n"
            "Task: compute the total revenue across all orders (SUM of amount,\n"
            "rounded to 2 decimals). Steps you may take:\n"
            '- "sql: <query>" runs one SQL query and returns the result table.\n'
            '- "finish: <answer>" submits the final answer (just the number).'
        ),
        (
            "sql: SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            "sql: SELECT ROUND(SUM(amount), 2) FROM orders",
            "finish: 660.75",
        ),
        "660.75",
    ),
    _make(
        "sql-top-customer",
        (
            "DATABASE: shop.sqlite (tables: customers, orders).\n"
            "Task: find the NAME of the customer with the highest total order\n"
            "amount. Steps:\n"
            '- "sql: <query>" runs one SQL query.\n'
            '- "finish: <answer>" submits the final answer (just the name).'
        ),
        (
            "sql: SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            "sql: SELECT c.name, SUM(o.amount) AS total FROM orders o"
            " JOIN customers c ON c.id = o.customer_id"
            " GROUP BY c.name ORDER BY total DESC",
            "finish: Lin",
        ),
        "Lin",
    ),
    _make(
        "sql-region-orders",
        (
            "DATABASE: shop.sqlite (tables: customers, orders).\n"
            "Task: count how many orders belong to customers in the EU region\n"
            "(requires a join). Steps:\n"
            '- "sql: <query>" runs one SQL query.\n'
            '- "finish: <answer>" submits the final answer (just the count).'
        ),
        (
            "sql: SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            "sql: SELECT COUNT(*) FROM orders o JOIN customers c ON c.id = o.customer_id"
            " WHERE c.region = 'EU'",
            "finish: 5",
        ),
        "5",
    ),
    _make(
        "sql-null-discount",
        (
            "DATABASE: shop.sqlite (tables: customers, orders; orders.discount\n"
            "may be NULL). Task: count orders whose discount is NULL. Steps:\n"
            '- "sql: <query>" runs one SQL query.\n'
            '- "finish: <answer>" submits the final answer (just the count).'
        ),
        (
            "sql: SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            "sql: SELECT COUNT(*) FROM orders WHERE discount IS NULL",
            "finish: 4",
        ),
        "4",
    ),
]
