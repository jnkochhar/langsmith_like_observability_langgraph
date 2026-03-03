from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from langchain.messages import HumanMessage

# Assume graph is already compiled in another file
from langgraph_graph import graph, collector
from observability_db import init_db, save_run, get_run, list_run_ids

init_db()

app = Flask(__name__)

@app.route("/batchrun", methods=["POST"])
def batch_run():

    user_input = request.form.get("message")
    print(user_input)

    collector.reset()

    # Run graph
    result = graph.invoke(
        {"messages": [HumanMessage(content=user_input)]}
    )

    trace_json = collector.build()

    # attach user query
    trace_json["user_query"] = user_input
    trace_json["final_response"] = result["messages"][-1].content

    # Save to DB
    save_run(**trace_json)

    return jsonify(trace_json)

@app.route("/", methods=["GET", "POST"])
def index():

    # -------------------------
    # POST → Create new run
    # -------------------------
    if request.method == "POST":

        user_input = request.form.get("message")
        print(user_input)

        collector.reset()

        # Run graph
        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]}
        )

        trace_json = collector.build()

        # attach user query
        trace_json["user_query"] = user_input
        trace_json["final_response"] = result["messages"][-1].content

        # Save to DB
        save_run(**trace_json)

        # Get run_id from saved trace
        new_run_id = trace_json["run_id"]

        # 🔥 IMPORTANT: Redirect to GET with run_id
        return redirect(url_for("index", run_id=new_run_id))


    # -------------------------
    # GET → Load existing run
    # -------------------------
    run_id = request.args.get("run_id")

    trace_json = None

    if run_id:
        trace_json = get_run(run_id)

    return render_template(
        "index_db.html",
        runs=list_run_ids(),
        trace=trace_json,
        selected_run_id=run_id
    )


if __name__ == "__main__":
    app.run(debug=True)