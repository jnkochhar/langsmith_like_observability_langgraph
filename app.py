from flask import Flask, render_template, request
from datetime import datetime
from langchain.messages import HumanMessage

# Assume graph is already compiled in another file
from langgraph_graph import graph, collector

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    trace_json = None
    final_response = None

    if request.method == "POST":
        user_input = request.form.get("message")

        collector.reset()

        # Run graph
        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]}
        )

        trace_json = collector.build()

        final_response = result["messages"][-1].content

    return render_template(
        "index.html",
        trace=trace_json,
        final_response=final_response
    )


if __name__ == "__main__":
    app.run(debug=True)