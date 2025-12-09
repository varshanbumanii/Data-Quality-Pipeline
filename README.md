# Workflow Engine – Data Quality Pipeline 

This project implements a **minimal Workflow Engine** using **FastAPI**, designed exactly according to the problem statement provided by **Tredence**.  
The engine supports:

- Creating workflow graphs  
- Running workflows step-by-step  
- Looping logic  
- Conditional branching  
- Registering "nodes" (processing steps)  
- Logging every step of execution  

This implementation demonstrates **Data Quality Pipeline**, where a dataset is iteratively cleaned until anomalies drop below a threshold.

---

# Features

### 1. Define workflows using a graph  
Nodes + edges + start node = entire pipeline.

### 2. Register workflow steps dynamically  
Nodes (functions) are added using a decorator:
```python
@register_node("profile_data")
