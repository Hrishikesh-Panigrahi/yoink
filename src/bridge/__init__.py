"""Python <-> JavaScript bridge package.

Re-exports the Bridge class so legacy ``from bridge import Bridge`` callers
keep working after the module-to-package split.
"""

from bridge.core import Bridge

__all__ = ["Bridge"]
