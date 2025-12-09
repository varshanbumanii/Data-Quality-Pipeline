from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Callable
import uuid
import math

# ============================================================
#  REGISTRY FOR NODES (WORKFLOW STEPS)
# ============================================================

NODE_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register_node(name: str):
    """
    Decorator to register a node function by name.
    """

    def wrapper(func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        NODE_REGISTRY[name] = func
        return func

    return wrapper


# ============================================================
#  Pydantic MODELS
# ============================================================

class GraphCreateRequest(BaseModel):
    name: str
    nodes: List[str]
    edges: Dict[str, Optional[str]]
    start_node: str


class GraphCreateResponse(BaseModel):
    graph_id: str


class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any] = {}


class ExecutionLogEntry(BaseModel):
    step: int
    node: str
    state_snapshot: Dict[str, Any]


class GraphRunResponse(BaseModel):
    run_id: str
    final_state: Dict[str, Any]
    log: List[ExecutionLogEntry]


class RunState(BaseModel):
    run_id: str
    graph_id: str
    current_node: Optional[str]
    state: Dict[str, Any]
    log: List[ExecutionLogEntry] = []


def generate_id() -> str:
    return uuid.uuid4().hex


# ============================================================
#  GRAPH + EXECUTOR
# ============================================================

class Graph:
    """
    Minimal representation of a workflow graph.
    """

    def __init__(
        self,
        graph_id: str,
        name: str,
        nodes: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]],
        edges: Dict[str, Optional[str]],
        start_node: str,
    ):
        self.graph_id = graph_id
        self.name = name
        self.nodes = nodes
        self.edges = edges
        self.start_node = start_node

    @classmethod
    def from_definition(
        cls,
        graph_id: str,
        name: str,
        node_names: List[str],
        edges: Dict[str, Optional[str]],
        start_node: str,
    ) -> "Graph":
        nodes: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

        for node_name in node_names:
            if node_name not in NODE_REGISTRY:
                raise ValueError(f"Node '{node_name}' is not registered.")
            nodes[node_name] = NODE_REGISTRY[node_name]

        if start_node not in nodes:
            raise ValueError(f"Start node '{start_node}' is not part of the graph nodes.")

        return cls(
            graph_id=graph_id,
            name=name,
            nodes=nodes,
            edges=edges,
            start_node=start_node,
        )


class GraphExecutor:
    """
    Runs a graph step-by-step.
    """

    def __init__(self, graph: Graph, max_steps: int = 100):
        self.graph = graph
        self.max_steps = max_steps

    def run(self, initial_state: Dict[str, Any]) -> RunState:
        state = dict(initial_state)
        current_node: Optional[str] = self.graph.start_node
        log: List[ExecutionLogEntry] = []
        step = 0

        run = RunState(
            run_id="",
            graph_id=self.graph.graph_id,
            current_node=current_node,
            state=state,
            log=[],
        )

        while current_node is not None and step < self.max_steps:
            step += 1
            node_func = self.graph.nodes[current_node]

            new_state = node_func(state)
            if new_state is not None:
                state = new_state

            # log snapshot
            log.append(
                ExecutionLogEntry(
                    step=step,
                    node=current_node,
                    state_snapshot=dict(state),
                )
            )

            if state.get("stop"):
                break

            next_node = state.pop("next_node", None)
            if next_node:
                current_node = next_node
            else:
                current_node = self.graph.edges.get(current_node)

        run.current_node = current_node
        run.state = state
        run.log = log
        return run


# ============================================================
#  DATA QUALITY NODES (WORKFLOW OPTION C)
# ============================================================

@register_node("profile_data")
def profile_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Profiles the dataset:
    - counts missing
    - computes numeric stats (min, max, mean)
    - counts non-numeric values
    """
    data = state.get("data", [])
    profile = {
        "row_count": len(data),
        "missing_count": 0,
        "numeric_count": 0,
        "non_numeric_count": 0,
        "min": None,
        "max": None,
        "mean": None,
    }

    numeric_values: List[float] = []

    for value in data:
        if value is None:
            profile["missing_count"] += 1
        else:
            try:
                num = float(value)
                numeric_values.append(num)
                profile["numeric_count"] += 1
            except Exception:
                profile["non_numeric_count"] += 1

    if numeric_values:
        profile["min"] = min(numeric_values)
        profile["max"] = max(numeric_values)
        profile["mean"] = sum(numeric_values) / len(numeric_values)

    state["profile"] = profile
    return state


@register_node("identify_anomalies")
def identify_anomalies(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple anomaly rules:
    - missing values
    - non-numeric values
    - outliers beyond mean ± 2 * std
    """
    data = state.get("data", [])
    profile = state.get("profile", {})
    anomalies: List[tuple] = []

    mean = profile.get("mean")
    numeric_values: List[float] = []

    for value in data:
        if value is None:
            continue
        try:
            numeric_values.append(float(value))
        except Exception:
            continue

    if len(numeric_values) > 1:
        variance = sum((x - mean) ** 2 for x in numeric_values) / len(numeric_values)
        std = math.sqrt(variance)
    else:
        std = 0.0

    for idx, value in enumerate(data):
        if value is None:
            anomalies.append((idx, "missing_value"))
        else:
            try:
                num = float(value)
                if std > 0 and abs(num - mean) > 2 * std:
                    anomalies.append((idx, "outlier"))
            except Exception:
                anomalies.append((idx, "non_numeric"))

    state["anomalies"] = anomalies
    state["anomaly_count"] = len(anomalies)
    return state


@register_node("generate_rules")
def generate_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates cleaning rules from the profile.
    """
    profile = state["profile"]
    rules = {
        "missing_value_rule": "replace_with_mean",
        "non_numeric_rule": "replace_with_mean",
        "outlier_rule": "cap_with_minmax",
        "mean": profile.get("mean"),
        "min": profile.get("min"),
        "max": profile.get("max"),
    }
    state["rules"] = rules
    return state


@register_node("apply_rules")
def apply_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies rules to clean the dataset.
    """
    data = state.get("data", [])
    rules = state.get("rules", {})
    cleaned: List[float] = []

    mean_val = rules.get("mean")
    min_val = rules.get("min")
    max_val = rules.get("max")

    for value in data:
        if value is None:
            cleaned.append(mean_val)
            continue

        try:
            num = float(value)
        except Exception:
            cleaned.append(mean_val)
            continue

        if min_val is not None and num < min_val:
            num = min_val
        if max_val is not None and num > max_val:
            num = max_val

        cleaned.append(num)

    state["data"] = cleaned
    return state


@register_node("check_stop_condition")
def check_stop_condition(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stop when anomaly_count <= threshold, else loop.
    """
    threshold = state.get("threshold", 1)
    anomaly_count = state.get("anomaly_count", 0)

    if anomaly_count <= threshold:
        state["stop"] = True
    else:
        state["next_node"] = "profile_data"

    return state


# ============================================================
#  FASTAPI APP + IN-MEMORY STORAGE
# ============================================================

app = FastAPI(
    title="Minimal Workflow Engine",
    description="Tredence assignment - Data Quality Workflow",
    version="0.1.0",
)

GRAPHS: Dict[str, Graph] = {}
RUNS: Dict[str, RunState] = {}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/graph/create", response_model=GraphCreateResponse)
def create_graph(payload: GraphCreateRequest):
    graph_id = generate_id()
    graph = Graph.from_definition(
        graph_id=graph_id,
        name=payload.name,
        node_names=payload.nodes,
        edges=payload.edges,
        start_node=payload.start_node,
    )
    GRAPHS[graph_id] = graph
    return GraphCreateResponse(graph_id=graph_id)


@app.post("/graph/run", response_model=GraphRunResponse)
def run_graph(payload: GraphRunRequest):
    if payload.graph_id not in GRAPHS:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = GRAPHS[payload.graph_id]
    executor = GraphExecutor(graph)
    run_state = executor.run(initial_state=payload.initial_state)

    run_id = generate_id()
    run_state.run_id = run_id
    RUNS[run_id] = run_state

    return GraphRunResponse(
        run_id=run_id,
        final_state=run_state.state,
        log=run_state.log,
    )


@app.get("/graph/state/{run_id}", response_model=RunState)
def get_run_state(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    return RUNS[run_id]
