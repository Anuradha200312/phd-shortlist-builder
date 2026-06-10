import sys
sys.path.append('.')

from tests.test_retrieve_node import test_retrieve_node_minimal

if __name__ == '__main__':
    try:
        test_retrieve_node_minimal()
        print('TEST_OK')
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
