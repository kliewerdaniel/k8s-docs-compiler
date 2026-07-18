"""k8s-docs-compiler — a compile-time knowledge compiler for Kubernetes.

Moves intelligence from runtime query-time computation into build-time
compilation, producing deterministic, inspectable, versioned knowledge
artifacts (JSON / SQLite / GEXF) that are deployable without backend inference.
"""
from .compiler import Compiler

__all__ = ["Compiler"]
__version__ = "0.1.0"
