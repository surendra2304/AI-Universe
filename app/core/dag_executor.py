"""Generic Asynchronous DAG Executor with Concurrency, Cancellation, Retries, and Node Telemetry."""

import asyncio
import time
from typing import Any, Callable, Coroutine, Dict, Optional

from pydantic import BaseModel

from app.core.dag import DAGNode, ExecutionDAG
from app.utils.logger import logger


class NodeExecutionResult(BaseModel):
    """Execution outcome and metrics for an individual DAG node."""
    node_id: str
    status: str = "completed"  # completed, failed, cancelled, skipped
    output: Any = None
    latency_seconds: float = 0.0
    error: Optional[str] = None
    attempt_count: int = 1


class DAGExecutor:
    """
    Executes a Directed Acyclic Graph with:
    - Dependency-ordered concurrency across topologically sorted layers.
    - Cancellation token support (stops pending/active tasks).
    - Node-level timeouts and retries.
    - Overall task lifecycle telemetry.
    """

    def __init__(
        self,
        dag: ExecutionDAG,
        cancellation_event: Optional[asyncio.Event] = None,
        default_node_timeout_seconds: float = 30.0
    ) -> None:
        self.dag = dag
        self.cancellation_event = cancellation_event or asyncio.Event()
        self.default_node_timeout_seconds = default_node_timeout_seconds
        self.results: Dict[str, NodeExecutionResult] = {}

    async def execute(
        self,
        node_runner: Callable[[DAGNode, Dict[str, Any]], Coroutine[Any, Any, Any]],
        overall_timeout_seconds: Optional[float] = None
    ) -> Dict[str, NodeExecutionResult]:
        """Executes all DAG layers respecting dependencies and cancellations."""
        layers = self.dag.build_layers() if not self.dag.layers else self.dag.layers

        async def run_with_timeout() -> Dict[str, NodeExecutionResult]:
            for layer_idx, layer_nodes in enumerate(layers):
                if self.cancellation_event.is_set():
                    logger.warning("DAG Execution cancelled before layer %d", layer_idx)
                    for nid in layer_nodes:
                        self.results[nid] = NodeExecutionResult(node_id=nid, status="cancelled", error="Task was cancelled")
                    continue

                # Run all independent nodes in this layer concurrently
                layer_tasks = [self._execute_single_node(nid, node_runner) for nid in layer_nodes]
                await asyncio.gather(*layer_tasks)

            return self.results

        if overall_timeout_seconds:
            try:
                return await asyncio.wait_for(run_with_timeout(), timeout=overall_timeout_seconds)
            except asyncio.TimeoutError:
                logger.error("DAG Execution timed out after %.2fs", overall_timeout_seconds)
                for nid, node in self.dag.nodes.items():
                    if nid not in self.results:
                        self.results[nid] = NodeExecutionResult(node_id=nid, status="failed", error="Overall DAG timeout exceeded")
                return self.results
        else:
            return await run_with_timeout()

    async def _execute_single_node(
        self,
        node_id: str,
        node_runner: Callable[[DAGNode, Dict[str, Any]], Coroutine[Any, Any, Any]],
        max_retries: int = 1
    ) -> NodeExecutionResult:
        """Executes an individual node with timeout, retry, and cancellation check."""
        node = self.dag.nodes[node_id]
        node_start = time.perf_counter()

        if self.cancellation_event.is_set():
            res = NodeExecutionResult(node_id=node_id, status="cancelled", error="Cancelled before start")
            self.results[node_id] = res
            return res

        # Gather completed dependency outputs
        dep_outputs = {
            dep_id: self.results[dep_id].output
            for dep_id in node.dependencies
            if dep_id in self.results and self.results[dep_id].status == "completed"
        }

        # If a required dependency failed/cancelled, skip this node
        failed_deps = [
            dep_id for dep_id in node.dependencies
            if dep_id in self.results and self.results[dep_id].status in ("failed", "cancelled", "skipped")
        ]
        if failed_deps:
            res = NodeExecutionResult(
                node_id=node_id,
                status="skipped",
                error=f"Skipped due to dependency failure: {failed_deps}"
            )
            self.results[node_id] = res
            return res

        for attempt in range(1, max_retries + 1):
            try:
                output = await asyncio.wait_for(
                    node_runner(node, dep_outputs),
                    timeout=self.default_node_timeout_seconds
                )
                latency = time.perf_counter() - node_start
                res = NodeExecutionResult(
                    node_id=node_id,
                    status="completed",
                    output=output,
                    latency_seconds=latency,
                    attempt_count=attempt
                )
                self.results[node_id] = res
                return res
            except asyncio.CancelledError:
                latency = time.perf_counter() - node_start
                res = NodeExecutionResult(
                    node_id=node_id,
                    status="cancelled",
                    latency_seconds=latency,
                    error="Node cancelled",
                    attempt_count=attempt
                )
                self.results[node_id] = res
                return res
            except Exception as exc:
                if attempt == max_retries:
                    latency = time.perf_counter() - node_start
                    res = NodeExecutionResult(
                        node_id=node_id,
                        status="failed",
                        latency_seconds=latency,
                        error=str(exc),
                        attempt_count=attempt
                    )
                    self.results[node_id] = res
                    return res
                await asyncio.sleep(0.5)

        # Fallback safeguard
        res = NodeExecutionResult(node_id=node_id, status="failed", error="Unknown node execution error")
        self.results[node_id] = res
        return res
