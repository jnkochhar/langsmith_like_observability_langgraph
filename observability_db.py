import sqlite3
import json

def init_db():
    conn = sqlite3.connect("observability.db")
    cursor = conn.cursor()

    # Runs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        user_query TEXT,
        final_response TEXT,
        start_time TEXT,
        start_timestamp TEXT,
        total_tokens TEXT,
        total_latency REAL,
        errors TEXT
    )
    """)

    # Nodes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS run_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        node TEXT,
        start TEXT,
        latency REAL,
        tokens TEXT,
        input_data TEXT,
        output_data TEXT,
        error TEXT,
        FOREIGN KEY(run_id) REFERENCES runs(run_id)
    )
    """)

    # Index for fast lookup
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_start_time ON runs(start_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON run_nodes(run_id)")

    conn.commit()
    conn.close()

def save_run(run_id, user_query, final_response, start_time, start_timestamp, nodes, total_tokens, total_latency, errors):
    conn = sqlite3.connect("observability.db")
    cursor = conn.cursor()

    # Insert into runs table
    cursor.execute("""
    INSERT INTO runs (run_id, user_query, final_response, start_time, start_timestamp, total_tokens, total_latency, errors)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        user_query,
        final_response,
        start_time,
        start_timestamp,
        json.dumps(total_tokens),
        total_latency,
        json.dumps(errors)
    ))

    # Insert each node
    for node in nodes:
        cursor.execute("""
        INSERT INTO run_nodes
        (run_id, node, start, latency, tokens, input_data, output_data, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            node.get("node"),
            node.get("start"),
            node.get("latency"),
            json.dumps(node.get("tokens")),
            json.dumps(node.get("input")),
            json.dumps(node.get("output")),
            node.get("error")
        ))

    conn.commit()
    conn.close()

def get_run(run_id):
    conn = sqlite3.connect("observability.db")
    cursor = conn.cursor()

    # Get run metadata
    cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
    run_row = cursor.fetchone()

    if not run_row:
        conn.close()
        return None

    run_data = {
        "run_id": run_row[0],
        "user_query": run_row[1],
        "final_response": run_row[2],
        "start_time": run_row[3],
        "start_timestamp": run_row[4],
        "total_tokens": json.loads(run_row[5]),
        "total_latency": run_row[6],
        "errors": json.loads(run_row[7]),
        "nodes": []
    }

    # Get nodes
    cursor.execute("""
    SELECT node, start, latency, tokens, input_data, output_data, error
    FROM run_nodes
    WHERE run_id = ?
    """, (run_id,))

    node_rows = cursor.fetchall()

    for row in node_rows:
        run_data["nodes"].append({
            "node": row[0],
            "start": row[1],
            "latency": row[2],
            "tokens": json.loads(row[3]),
            "input": json.loads(row[4]),
            "output": json.loads(row[5]),
            "error": row[6]
        })

    conn.close()
    return run_data

def list_run_ids():
    conn = sqlite3.connect("observability.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT run_id, user_query, start_time
    FROM runs
    ORDER BY start_timestamp DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows