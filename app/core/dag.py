"""DAG Execution, Complexity Classifier, and Dependency Models for Inference."""

import re
from enum import Enum

from pydantic import BaseModel, Field


class TaskComplexity(str, Enum):
    SIMPLE = "simple"       # Easy: Single primary model per agent
    COMPLEX = "complex"     # Moderate/Complex: 2-3 models per agent in parallel
    STRATEGIC = "strategic" # Strategic/Deep: Full DAG with multi-model parallel debate


class DAGNode(BaseModel):
    """Represents an agent execution stage in the Directed Acyclic Graph."""
    node_id: str
    agent_id: str
    agent_role: str
    dependencies: list[str] = Field(default_factory=list, description="IDs of nodes that must finish before this node runs")
    stage_name: str = "analysis"
    complexity: TaskComplexity = TaskComplexity.SIMPLE


class ExecutionDAG(BaseModel):
    """Directed Acyclic Graph defining parallel execution stages for multi-agent workflows."""
    nodes: dict[str, DAGNode] = Field(default_factory=dict)
    layers: list[list[str]] = Field(default_factory=list, description="Topologically sorted execution layers for parallel asyncio.gather")

    def add_node(self, node: DAGNode) -> None:
        self.nodes[node.node_id] = node

    def build_layers(self) -> list[list[str]]:
        """
        Builds parallel execution layers using topological sort.
        All nodes in layer N have all their dependencies satisfied by layers 0..N-1.
        """
        in_degree: dict[str, int] = {nid: len(n.dependencies) for nid, n in self.nodes.items()}
        layers: list[list[str]] = []
        visited: set[str] = set()

        while len(visited) < len(self.nodes):
            current_layer = [
                nid for nid, deg in in_degree.items()
                if deg == 0 and nid not in visited
            ]
            if not current_layer:
                # Cycle or unresolved dependency safeguard: release all unvisited
                current_layer = [nid for nid in self.nodes.keys() if nid not in visited]

            layers.append(current_layer)
            for nid in current_layer:
                visited.add(nid)
                # Reduce in-degree for dependent nodes
                for other_id, other_node in self.nodes.items():
                    if nid in other_node.dependencies:
                        in_degree[other_id] = max(0, in_degree[other_id] - 1)

        self.layers = layers
        return layers


def classify_task_complexity(question: str, requested_mode: str = "auto") -> TaskComplexity:
    """
    Classifies an incoming query into SIMPLE, COMPLEX, or STRATEGIC complexity.
    - SIMPLE: Basic lookup, concise code query, direct factual question, or fast mode.
    - STRATEGIC: Multi-system architectural trade-offs, security threat modeling, high-stakes decisions.
    - COMPLEX: Refactoring, debugging tricky errors, comparing components, deep analysis.
    """
    if requested_mode == "fast":
        return TaskComplexity.SIMPLE
    if requested_mode in ["debate", "strategic"]:
        return TaskComplexity.STRATEGIC

    q_lower = question.lower()
    strategic_keywords = [
        "architecture", "architectural", "system design", "trade-off", "tradeoff",
        "vs", "versus", "threat model", "vulnerability", "microservice", "monolith",
        "roadmap", "governance", "distributed system", "failover", "consensus"
    ]
    complex_keywords = [
        "implement", "refactor", "debug", "deadlock", "race condition", "optimize",
        "benchmark", "sql query", "verify claims", "pipeline", "security analysis",
        "traceback", "exception", "async", "schema"
    ]

    if any(re.search(rf"\b{re.escape(kw)}\b", q_lower) for kw in strategic_keywords):
        return TaskComplexity.STRATEGIC
    if any(re.search(rf"\b{re.escape(kw)}\b", q_lower) for kw in complex_keywords):
        return TaskComplexity.COMPLEX

    # Short simple queries default to SIMPLE
    if len(question.split()) < 12:
        return TaskComplexity.SIMPLE

    return TaskComplexity.COMPLEX
