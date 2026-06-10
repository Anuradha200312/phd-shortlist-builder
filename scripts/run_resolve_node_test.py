import sys
sys.path.append('.')

from tests.test_resolve_node import test_resolve_node_basic

if __name__ == '__main__':
    try:
        test_resolve_node_basic()
        print('TEST_OK')
    except Exception:
        import traceback

        traceback.print_exc()
        raise
