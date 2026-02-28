# LangSmith-Like Observability for LangGraph

Lightweight custom observability layer for LangGraph workflows.

This project demonstrates how to build tracing and monitoring similar to LangSmith — from scratch — with full control over execution visibility.

## Features

- Node-level execution tracing
- Latency tracking
- Token usage monitoring
- Input/Output logging
- Structured trace UI (Flask)
- Local database storage
- Excel-based batch execution

## Use Cases

- Debug multi-step agent workflows
- Analyze graph execution behavior
- Add monitoring to production LLM apps
- Avoid vendor lock-in

## Run

pip install -r requirements.txt  
python app.py  

Open in browser: http://localhost:5000

---

Part of the "Build Your Own LangSmith" series.