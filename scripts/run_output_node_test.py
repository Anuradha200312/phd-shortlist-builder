import sys
sys.path.append('.')

from tests.test_output_node import test_output_node_basic

if __name__ == '__main__':
    try:
        test_output_node_basic()
        print('TEST_OK')
    except Exception:
        import traceback

        traceback.print_exc()
        raise
