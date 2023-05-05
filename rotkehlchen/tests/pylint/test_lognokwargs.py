import astroid

from tools.pylint import LogNokwargsChecker
from tools.pylint.log_checker import LOGNOKWARGS_SYMBOL


def test_simple_logger_with_kwargs(pylint_test_linter):
    """Test that we can detect the usage of kwargs in a normal logging call

    But that we also allow it for RotkehlchenLogsAdapter
    """
    checker = LogNokwargsChecker(linter=pylint_test_linter)
    # Check that simple loggers with kwargs raise the checker's error
    for method_name in ('info', 'debug', 'error', 'warning'):
        node = astroid.extract_node(f"""
        import logging
        logger = logging.getLogger(__name__)
        logger.{method_name}('foo', a=1) #@
        """)

        checker.visit_call(node)
        messages = checker.linter.release_messages()
        assert len(messages) == 2
        for m in messages:
            assert m.msg_id == LOGNOKWARGS_SYMBOL
            assert m.node == node

    # But also check that if it's a RotkehlchenLogsAdapter there is no error
    for method_name in ('info', 'debug', 'error', 'warning'):
        node = astroid.extract_node(f"""
        import logging
        from rotkehlchen.logging import RotkehlchenLogsAdapter
        logger = logging.getLogger(__name__)
        log = RotkehlchenLogsAdapter(logger)
        log.{method_name}('foo', a=1) #@
        """)

        checker.visit_call(node)
        messages = checker.linter.release_messages()
        assert len(messages) == 0


def test_works_for_nodes_without_kwargs(pylint_test_linter):
    """Test that the custome checker also works for nodes without kwargs"""
    checker = LogNokwargsChecker(linter=pylint_test_linter)
    # Check that simple loggers with kwargs raise the checker's error
    node = astroid.extract_node("""
    import logging
    logger = logging.getLogger(__name__)
    logger.info('foo') #@
    """)

    checker.visit_call(node)
    messages = checker.linter.release_messages()
    assert len(messages) == 0
