import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "test_score_node_chroma",
    Path(__file__).parent.parent / "tests" / "test_score_node_chroma.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if __name__ == '__main__':
    module.test_score_node_chroma()
