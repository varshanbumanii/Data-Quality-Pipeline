# Minimal Workflow Engine – Data Quality Pipeline  
**Author:** Varsha Anbumani  

---

## 📌 Overview

This project implements a **Minimal Workflow Engine** using **FastAPI**.

The engine allows users to:

- Define workflows using a directed graph  
- Register processing nodes dynamically  
- Execute workflows step-by-step  
- Perform conditional branching and looping  
- Maintain detailed execution logs  
- Process data in a clean, modular way  

The implemented sample workflow demonstrates **Data Quality Pipeline**, which repeatedly cleans a dataset until anomalies fall below a threshold.

---

## Key Features

### **1. Graph-Based Workflow Execution**
Define workflows using:
- `nodes[]` → list of step names  
- `edges{}` → mapping of node → next node  
- `start_node` → where execution begins  

### **2. Dynamic Node Registry**
Nodes are registered with a decorator:
```python
@register_node("profile_data")
```
This ensures modular, plug-and-play workflow steps.

### **3. Logging for Every Step**
Each execution step logs:
- Node executed  
- Step number  
- Full state snapshot  

### **4. Looping and Conditional Routing**
Nodes can redirect execution:
```python
state["next_node"] = "profile_data"
```
Or end execution:
```python
state["stop"] = True
```

### **5. Clean Code in a Single File**
Entire engine, nodes, and API all inside `main.py` for simplicity.

---

## Data Quality Pipeline  

This workflow processes and cleans a dataset by executing the following steps:

```
profile_data
→ identify_anomalies
→ generate_rules
→ apply_rules
→ check_stop_condition
↺ (loops until anomalies <= threshold)
```

### ✔ What the pipeline does:
- Profiles dataset (missing, numeric, types, min/max/mean)  
- Identifies anomalies:
  - missing values  
  - non-numeric values  
  - outliers (mean ± 2*std)  
- Generates cleaning rules  
- Applies rules (replace, cap, clean)  
- Loops until data is acceptable  

---

## 🏗 Architecture Diagram

```
          +------------------------+
          |   POST /graph/create   |
          +-----------+------------+
                      |
                      v
       +------------------------------+
       |   Graph stored in memory     |
       +------------------------------+
                      |
                      v
          +------------------------+
          |    POST /graph/run     |
          +-----------+------------+
                      |
          (Executor loads workflow)
                      |
                      v
             ┌───────────────────────┐
             │  Execute next node    │
             │  Update state         │
             │  Log snapshot         │
             │  Branch/Loop/Stop     │
             └───────────────────────┘
                      |
                      v
          +----------------------------+
          |   Return final state & log |
          +----------------------------+
```

---

## Installation

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install fastapi uvicorn pydantic
```

### 2️⃣ Run the Server
```bash
python -m uvicorn main:app --reload
```

Open Swagger UI 
http://127.0.0.1:8000/docs

---

## 🧩 API Endpoints

### **GET /health**
Check if server is running.

### **POST /graph/create**
Creates a workflow graph.

#### Example Request:
```json
{
  "name": "data_quality_pipeline",
  "nodes": [
    "profile_data",
    "identify_anomalies",
    "generate_rules",
    "apply_rules",
    "check_stop_condition"
  ],
  "edges": {
    "profile_data": "identify_anomalies",
    "identify_anomalies": "generate_rules",
    "generate_rules": "apply_rules",
    "apply_rules": "check_stop_condition",
    "check_stop_condition": null
  },
  "start_node": "profile_data"
}
```

#### Example Response:
```json
{
  "graph_id": "c3f81bdca9f54c28873549bfa665c75a"
}
```

---

### **POST /graph/run**
Executes the workflow graph.

#### Example Request:
```json
{
  "graph_id": "PUT_GRAPH_ID_HERE",
  "initial_state": {
    "data": [5, 7, 1000, null, "abc", 6, 8, 7],
    "threshold": 1
  }
}
```

#### Example Response (Truncated):
```json
{
  "run_id": "example123",
  "final_state": {
    "data": [5, 7, 8, 7, 7, 6, 8, 7],
    "anomaly_count": 0,
    "stop": true
  },
  "log": [
    { "step": 1, "node": "profile_data", ... },
    { "step": 2, "node": "identify_anomalies", ... }
  ]
}
```

---

###  **GET /graph/state/{run_id}**
Retrieve results of a previous run.

---

## 🔧 Additional Examples

### Example: Mixed strings & numbers
```json
{
  "graph_id": "<id>",
  "initial_state": {
    "data": ["12", 5, "x", null, 9.5],
    "threshold": 0
  }
}
```

### Example: Extreme outliers
```json
{
  "graph_id": "<id>",
  "initial_state": {
    "data": [1, 2, 99999, -5000, 3, null],
    "threshold": 1
  }
}
```

---

## Why This Solution Stands Out

✔ Fully modular architecture  
✔ Clean and well-documented code  
✔ Clear extensibility  
✔ Excellent logging & observability  
✔ Implements real data profiling & cleaning logic  
✔ Easy to test and demo  

---

## Future Improvements (Optional)

- Add a visual workflow editor  
- Persist workflows in DB (Redis, PostgreSQL)  
- Add parallel node execution  
- Implement advanced anomaly detection  
- Build a front-end dashboard  
- Add authentication & user profiles  

---

## Author

**Varsha Anbumani**   
2025  

---

 _Feel free to explore, test, and extend the workflow engine!_

