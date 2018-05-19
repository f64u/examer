from utils.parsers import parse_tests
from utils.helpers import res

TESTS = parse_tests(res("tests2.enc", "state"), encrypted=True)
# questions = [Question("sad", None, [Answer("YES!!", False)] * 3)] * 3
# TESTS.extend([Test(1, "Hey", "you!", 5000, questions, 3, []), Test(2, "Hello", "asda", 2200, questions, 3, []),
#               Test(3, "How", "are you?", 2705, questions, 5, [])])
