from utils.parsers import parse_tests, parse_degrees
from utils.helpers import res, Question, Answer, Test

TESTS = parse_tests(res("tests.enc", "state"), encrypted=True)
# questions = [Question("sad", None, [Answer("YES!!", False)] * 3)] * 3
# TESTS.extend([Test(1, "Hey", "you!", 5000, questions, 3, []), Test(2, "Hello", "asda", 2200, questions, 3, []),
#               Test(3, "How", "are you?", 2705, questions, 5, [])])

DEGREES = parse_degrees(res("degrees.enc", "state"), encrypted=True)
