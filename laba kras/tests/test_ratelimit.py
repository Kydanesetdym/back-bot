from server.ratelimit import FailureLimiter


def test_blocks_after_max_failures():
    lim = FailureLimiter(max_failures=3, window=60)
    for i in range(3):
        assert lim.retry_after("ip", now=100.0 + i) == 0
        lim.register_failure("ip", now=100.0 + i)
    assert lim.retry_after("ip", now=103.0) > 0


def test_unblocks_after_window():
    lim = FailureLimiter(max_failures=2, window=60)
    lim.register_failure("ip", now=100.0)
    lim.register_failure("ip", now=101.0)
    assert lim.retry_after("ip", now=102.0) > 0
    assert lim.retry_after("ip", now=161.0) == 0


def test_reset_clears_failures():
    lim = FailureLimiter(max_failures=1, window=60)
    lim.register_failure("ip", now=100.0)
    lim.reset("ip")
    assert lim.retry_after("ip", now=101.0) == 0