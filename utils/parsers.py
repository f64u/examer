import json
import unicodedata
from typing import List

from .helpers import (
    Encryptor,
    Test, Question, Answer, StudentDegree
)


def parse_tests(infile: str, encrypted=False) -> List[Test]:
    with open(infile, "rb") if encrypted else open(infile, encoding="utf8") as f:
        contents = f.read()
        if not contents:
            return []
        data = unicodedata.normalize("NFKD", Encryptor.decrypt(contents) if encrypted else contents)

    tests = json.loads(data, encoding="utf8")
    final_tests = []
    for test in tests:
        final_questions = []
        for question in test["questions"]:
            question["answers"] = [Answer(**ans) for ans in question["answers"]]
            final_questions.append(Question(**question))
        test["questions"] = final_questions
        test["student_degrees"] = [StudentDegree(**s) for s in test["student_degrees"]]
        final_tests.append(Test(**test))

    return final_tests


def dump_tests(tests: List[Test], outfile: str, encrypt=False) -> None:
    final_tests = []
    for test in tests:
        test_dict = test._asdict()
        final_questions = []
        for question in test_dict["questions"]:
            question_dict = question._asdict()
            final_answers = [ans._asdict() for ans in question_dict["answers"]]
            question_dict["answers"] = final_answers
            final_questions.append(question_dict)
        test_dict["questions"] = final_questions
        test_dict["student_degrees"] = [s._asdict() for s in test_dict["student_degrees"]]
        final_tests.append(test_dict)

    with open(outfile, "wb") if encrypt else open(outfile, "w", encoding="utf8") as f:
        data = unicodedata.normalize("NFKD", json.dumps(final_tests))
        f.write(Encryptor.encrypt(data) if encrypt else data)
