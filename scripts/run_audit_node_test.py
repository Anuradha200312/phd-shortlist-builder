import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "test_audit_node",
    Path(__file__).parent.parent / "tests" / "test_audit_node.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if __name__ == '__main__':
    module.test_audit_node()
