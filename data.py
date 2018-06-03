from utils.helpers import res, _init
from utils.parsers import parse_tests

_init()

TESTS = parse_tests(res("data.enc", "state"), encrypted=True)
