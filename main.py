# -*- coding: utf-8 -*-

"""
:author: Fady Adel (2masadel at gmail dot com)
:link: https://bitbucket.org/faddyy/examer
"""

import base64
import datetime
import hashlib
import json
import os
import random
import re
import sys
import unicodedata
from collections import namedtuple, OrderedDict

import aenum
from PyQt4 import QtGui, QtCore
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import List, Union

DEBUG = True

# it's just used to make the garbage collector doesn't delete the window reference
CURRENT_ACTIVE = [None]  # type: List[QtGui.QWidget]

IMAGES_PATH = os.path.join(".", "res", "images")
DATA_PATH = os.path.join(".", "res", "state")

headers = ['name',
           'school',
           'grade',
           'phone',
           'degree',
           'out_of',
           'left',
           'failed_at',
           'test',
           ]

# ==================== Data Holders =====================
Answer = namedtuple("Answer", "string valid")
Question = namedtuple("Question", "string pic answers")
Test = namedtuple("Test", "name description time questions degree student_degrees")
StudentDegree = namedtuple("Degree", "name phone school grade degree out_of failed_at left test")


# =======================================================


# =================== Util Functions ====================
def parse_tests(infile: str, encrypted=False) -> List[Test]:
    with open(infile, "rb") if encrypted else open(infile, encoding="utf8") as f:
        contents = f.read()
        if not contents:
            return []
        data = unicodedata.normalize("NFKD", Encryptor.decrypt(contents) if encrypted else contents)

    tests = json.loads(data, encoding="utf8")
    test_list = []
    for test in tests:
        questions = [Question(q["question"], q["pic"], [Answer(a, i in q["valid"]) for i, a in enumerate(q["answers"])])
                     for q in test["questions"]]

        test_list.append(Test(test["name"], test["description"], test["time"], questions, test["degree"], []))

    return test_list


def parse_degrees(infile: str, encrypted=False) -> List[StudentDegree]:
    with open(infile, "rb") if encrypted else open(infile, encoding="utf8") as f:
        contents = f.read()
        if not contents:
            return []
        data = unicodedata.normalize("NFKD", Encryptor.decrypt(contents) if encrypted else contents)

    students = json.loads(data)
    return [StudentDegree(s["name"], s["phone"], s["school"], s["grade"], s["degree"], s["out_of"], s["failed_at"],
                          s["left"], s["test"]) for s in students]


def dump_tests(tests: List[Test], outfile: str, encrypt=False) -> None:
    with open(outfile, "wb") if encrypt else open(outfile, "w", encoding="utf8") as f:
        data = json.dumps([d._asdict() for d in tests])
        f.write(unicodedata.normalize("NFKD", Encryptor.encrypt(data) if encrypt else data))


def dump_degrees(degrees: List[StudentDegree], outfile: str, encrypt=False) -> None:
    with open(outfile, "wb") if encrypt else open(outfile, "w", encoding="utf8") as f:
        data = json.dumps([d._asdict() for d in degrees])
        f.write(unicodedata.normalize("NFKD", Encryptor.encrypt(data) if encrypt else data))


def center_widget(widget: QtGui.QWidget) -> None:
    widget.move(QtGui.QApplication.desktop().screen().rect().center() - widget.rect().center())


def format_secs(seconds: int, sp=("ساعة", "دقيقة", "ثانية"), sep="، ") -> str:
    return sep.join(["%d %s" % (int(d), s) for d, s in zip(str(datetime.timedelta(seconds=seconds)).split(':'), sp)
                     if not int(d) == 0])


def _rel_icon(name: str) -> str:
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, "icons", name)


def _res(name: str, kind="image") -> str:
    assert kind in ("image", "icon", "state")

    if kind == "image":
        return os.path.join(IMAGES_PATH, name)
    elif kind == "icon":
        if DEBUG:
            return os.path.join('icos', name)
        return _rel_icon(name)
    else:
        return os.path.join(DATA_PATH, name)


def _init():
    for e in [("degrees.enc", "state"), ("tests.enc", "state")]:
        r = _res(*e)
        if not os.path.isfile(r):
            with open(r, "w") as f:
                f.write("")


def _defer():
    if os.path.isfile("qt.conf"):
        os.remove("qt.conf")


def _tab_repr(index: int, deleted=False) -> str:
    return "Details" if index == 0 else "Q " + str(index) + (" (Deleted)" if deleted else "")


# =======================================================

# ====================== Encryption =====================

class Encryptor(object):
    p = base64.b64decode(b'ZnVja3k0MmZ1bmt5NDJmdWM0Mmtpbmc0MndvcmxkNDI=')

    @staticmethod
    def encrypt(string: str) -> bytes:
        s = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=s,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(Encryptor.p))
        fer = Fernet(key)
        return s + fer.encrypt(string.encode())

    @staticmethod
    def decrypt(data: bytes) -> str:
        s = data[:16]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=s,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(Encryptor.p))
        fer = Fernet(key)
        return fer.decrypt(data[16:]).decode()


# ========================================================


TESTS = parse_tests(_res("tests.enc", "state"), encrypted=True)
questions = [Question("sad", None, [Answer("YES!!", False)] * 3)] * 3
TESTS.extend([Test("Hey", "you!", 5000, questions, 3, []), Test("Hello", "asda", 2200, questions, 3, []),
              Test("How", "are you?", 2705, questions, 5, [])])


# ======================= Test Wizard =======================

class TestWizard(QtGui.QWizard):
    degrees = []

    def __init__(self, test: Test, parent: QtGui.QWidget = None):
        super().__init__(parent)
        self.test = test
        self.parent_window = None
        self.degree_per_q = self.test.degree / len(self.test.questions)
        self.setButtonText(self.NextButton, 'التالي >')
        self.setButtonText(self.CancelButton, 'الغاء')
        self.setButtonText(self.FinishButton, 'انتهي')
        self.setButtonText(self.BackButton, '< السابق')
        self.button(QtGui.QWizard.NextButton).clicked.connect(self.next_or_back_clicked)
        self.button(QtGui.QWizard.BackButton).clicked.connect(self.next_or_back_clicked)

        self.setWizardStyle(QtGui.QWizard.ClassicStyle)
        self.setWindowTitle(self.test.name)
        self.setMinimumSize(480, 380)

        self.resize(720, 540)

        self.setStyleSheet("QWidget {font-family: Times; }\n"
                           "QLabel {font: bold 15pt}\nQRadioButton, QCheckBox {font: 10pt}")

        self.addPage(FormPage())

        for question in self.test.questions:
            self.addPage(QuestionPage(question))

        self.addPage(FinalPage())

        def f():
            self.calculate()
            d = self.degrees

            if not all(i != -1 for i in d) and not self.timeout:
                msg_box = QtGui.QMessageBox(QtGui.QMessageBox.Warning,
                                            "انتبه", 'انت لم تجب عن كل السئلة، هل تريد المتابعة؟',
                                            QtGui.QMessageBox.NoButton, self)
                msg_box.addButton("&اجل", QtGui.QMessageBox.AcceptRole)
                msg_box.addButton("&لا", QtGui.QMessageBox.RejectRole)

                if msg_box.exec_() == QtGui.QMessageBox.AcceptRole:
                    return True
                return False
            return True

        # validation happens in the last question page (-2 by index of pages)
        self.page(self.pageIds()[-2]).validatePage = f

        self.time = test.time
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_lcd)
        self.timeout = self.timer_started = False
        self.finished_answering = False

    def update_lcd(self):
        self.time -= 1

        if self.time >= 0:
            if isinstance(self.currentPage(), QuestionPage):
                self.currentPage().lcdScreen.display("%d:%02d" % (self.time // 60, self.time % 60))
        else:
            self.timeout = True
            self.timer.stop()
            self.setButtonText(QtGui.QWizard.NextButton, 'احسب')
            self.calculate()
            QtGui.QMessageBox.information(self, "انتهي الوقت !", "اضغط علي 'احسب' لتري نتائجك")

            # because back button erases visited pages
            self.already_visited_pages = self.visitedPages()
            self.disallow_answering()

    def disallow_answering(self):
        self.finished_answering = True
        for p in self.pageIds()[:-1]:
            self.page(p).setEnabled(False)

        # no validation anymore
        self.page(self.pageIds()[-2]).validatePage = lambda: True

    def nextId(self):
        if self.currentId() == self.pageIds()[-1]:
            return -1
        if self.timeout:
            # no showing for non-visited ones, evil.
            if self.currentId() + 1 in self.already_visited_pages:
                return self.currentId() + 1
            return self.pageIds()[-1]
        return super().nextId()

    def next_or_back_clicked(self):
        if self.currentId() == self.pageIds()[-2] and not self.finished_answering:
            self.setButtonText(QtGui.QWizard.NextButton, 'احسب')
        else:
            self.setButtonText(QtGui.QWizard.NextButton, 'التالي >')

        if self.currentId() == self.pageIds()[1] and not self.timer_started:
            self.timer.start(1000)
            self.timer_started = True

        if self.currentId() == self.pageIds()[-1]:
            if self.timer.isActive():
                self.timer.stop()
            self.disallow_answering()

        if self.currentId() == self.pageIds()[1]:
            self.button(QtGui.QWizard.BackButton).setDisabled(True)

        p = self.currentPage()
        if isinstance(p, QuestionPage):
            p.lcdScreen.display("%d:%02d" % (self.time // 60, self.time % 60))

    def calculate(self):
        self.degrees = []
        for p in self.pageIds():
            p = self.page(p)
            if isinstance(p, QuestionPage):
                self.degrees.append(p.degree)

    def closeEvent(self, event: QtGui.QCloseEvent):
        if not self.pageIds()[-1] > self.currentId() > 0:
            self.parent_window.show()
            event.accept()
        elif (QtGui.QMessageBox.question(self, "هل انت متأكد؟", "انت علي وشك ان تغلق النافذة، كل الإجابات سوف تنسي.",
                                         QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)) == QtGui.QMessageBox.Yes:
            self.parent_window.show()
            event.accept()
        else:
            event.ignore()


class FormPage(QtGui.QWizardPage):
    GRADES = [
        "الأول الإعدادي",
        "الثاني الإعدادي",
        "الثالث الإعدادي",
        "الأول الثانوي",
        "الثاني الثانوي",
        "الثالث الثانوي",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("<font color=red>" 'ادخل بياناتك' "</font>")
        self.setSubTitle(" ")

        my_layout = QtGui.QGridLayout()
        my_layout.setColumnStretch(0, 1)
        my_layout.setColumnStretch(3, 1)
        my_layout.setRowStretch(0, 1)
        my_layout.setRowStretch(3, 1)

        # self.setStyleSheet("QLineEdit { size: 40px 30px }")

        self.nameedit = QtGui.QLineEdit()
        self.schooledit = QtGui.QLineEdit()
        self.numberedit = QtGui.QLineEdit()

        self.nameedit.setPlaceholderText('ادخل اسمك')
        self.schooledit.setPlaceholderText('ادخل اسم مدرستك')
        self.numberedit.setPlaceholderText('ادخل رقم تليفونك')

        self.gradecombo = QtGui.QComboBox()

        e = [self.nameedit, self.schooledit, self.numberedit, self.gradecombo]
        for i in e:
            font = i.font()
            font.setPointSize(11)
            font.setBold(True)
            i.setFont(font)

        regexp = QtCore.QRegExp("^(\+\d\d?)?\d{6,11}$")
        self.numberedit.setValidator(QtGui.QRegExpValidator(regexp, self.numberedit))

        self.gradecombo.addItems(["<ادخل صفك>"] + FormPage.GRADES)

        self.gradecombo.model().item(0).setEnabled(False)

        self.registerField("name*", self.nameedit)
        self.registerField("school*", self.schooledit)
        self.registerField("grade*", self.gradecombo)
        self.registerField("number*", self.numberedit)

        nameL = QtGui.QLabel('الاسم :')
        nameL.setBuddy(self.nameedit)
        schoolL = QtGui.QLabel('المدرسة :')
        schoolL.setBuddy(self.schooledit)
        gradeL = QtGui.QLabel('الصف :')
        gradeL.setBuddy(self.gradecombo)
        numberL = QtGui.QLabel('رقم التليفون :')
        numberL.setBuddy(self.numberedit)

        my_layout.addWidget(nameL, 0, 2)
        my_layout.addWidget(schoolL, 1, 2)
        my_layout.addWidget(gradeL, 2, 2)
        my_layout.addWidget(numberL, 3, 2)
        my_layout.addWidget(self.nameedit, 0, 1)
        my_layout.addWidget(self.schooledit, 1, 1)
        my_layout.addWidget(self.gradecombo, 2, 1)
        my_layout.addWidget(self.numberedit, 3, 1)

        self.setLayout(my_layout)

    def validatePage(self):

        if len(self.nameedit.text().split(" ")) < 2:
            QtGui.QMessageBox.information(self, "خطأ في الاسم", 'يرجي ادخال الاسم ثنائيا او اكثر')
        elif self.gradecombo.currentText() == "<ادخل صفك>":
            QtGui.QMessageBox.information(self, "خطأ في الصف", 'يرجي ادخال الصف')
        else:
            return True

        return False


class FinalPage(QtGui.QWizardPage):
    class ColorBox(QtGui.QWidget):
        def __init__(self, color: str, description: str, parent=None):
            super().__init__(parent)
            lyt = QtGui.QHBoxLayout()
            self.setLayout(lyt)
            lyt.setDirection(QtGui.QBoxLayout.RightToLeft)
            widget = QtGui.QWidget()
            widget_lyt = QtGui.QHBoxLayout()
            widget.setLayout(widget_lyt)
            widget_lyt.addWidget(QtGui.QLabel())
            widget.setStyleSheet("background-color: {}".format(color))
            widget.resize(50, 50)
            lyt.addWidget(widget)
            lyt.addWidget(QtGui.QLabel(description), 1)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.lyt = lyt = QtGui.QHBoxLayout()
        self.setLayout(lyt)

        details_group = QtGui.QGroupBox()
        details_layout = QtGui.QGridLayout()
        details_group.setTitle("البيانات")

        self.nameL = QtGui.QLabel()
        self.schoolL = QtGui.QLabel()
        self.gradeL = QtGui.QLabel()
        self.numberL = QtGui.QLabel()
        details_layout.addWidget(self.nameL, 0, 0)
        details_layout.addWidget(self.schoolL, 1, 0)
        details_layout.addWidget(self.gradeL, 2, 0)
        details_layout.addWidget(self.numberL, 3, 0)

        details_layout.addWidget(QtGui.QLabel("الاسم: "), 0, 1)
        details_layout.addWidget(QtGui.QLabel("المدرسة: "), 1, 1)
        details_layout.addWidget(QtGui.QLabel("الصف: "), 2, 1)
        details_layout.addWidget(QtGui.QLabel("رقم التليفون: "), 3, 1)

        details_group.setLayout(details_layout)

        group_and_color = QtGui.QVBoxLayout()

        colors_group = QtGui.QGroupBox()
        colors_group.setTitle("الألوان")
        colors_lyt = QtGui.QVBoxLayout()
        colors_group.setLayout(colors_lyt)
        colors_lyt.addWidget(FinalPage.ColorBox("grey", "لم يجب"))
        colors_lyt.addWidget(FinalPage.ColorBox("red", "أجاب خطأً"))
        colors_lyt.addWidget(FinalPage.ColorBox("green", "أجاب صوابًا"))

        group_and_color.addWidget(details_group)
        group_and_color.addWidget(colors_group)

        lyt.insertLayout(1, group_and_color)

    def initializePage(self):
        degrees = self.wizard().degrees
        test = self.wizard().test
        name = self.field("name")
        school = self.field("school")
        grade = FormPage.GRADES[int(self.field("grade")) - 1]
        number = self.field("number")
        sum_of_degrees = sum(i for i in degrees if i != -1)

        if number.startswith("01") and len(number) == 11:
            number = "+2" + number

        self.nameL.setText(name)
        self.schoolL.setText(school)
        self.gradeL.setText(grade)
        self.numberL.setText(number)

        failed_at = []
        left = []
        for i, v in enumerate(degrees):
            if v == 0:
                failed_at.append(i)
            elif v == -1:
                left.append(i)

        student = dict(zip(headers, [name,
                                     school,
                                     grade,
                                     number,
                                     sum_of_degrees,
                                     test.degree,
                                     left,
                                     failed_at,
                                     test.name,
                                     ]))

        pieces = (len(left) * test.degree, len(failed_at) * test.degree, sum_of_degrees)
        set_angle = 0
        total = sum(pieces)
        colors = [QtGui.QColor(128, 128, 128), QtGui.QColor(255, 0, 0), QtGui.QColor(0, 128, 0)]
        scene = QtGui.QGraphicsScene()
        for i, piece in enumerate(pieces):
            angle = round(float(piece * 5760) / total)
            ellipse = QtGui.QGraphicsEllipseItem(0, 0, 400, 400)
            ellipse.setPos(0, 0)
            ellipse.setStartAngle(set_angle)
            ellipse.setSpanAngle(angle)
            ellipse.setBrush(colors[i])
            set_angle += angle
            scene.addItem(ellipse)

        view = QtGui.QGraphicsView(scene)
        view.setStyleSheet("background-color: transparent")
        self.lyt.insertWidget(0, view)

        dump_degrees(parse_degrees(_res("degrees.enc", "state")) + [StudentDegree(**student)],
                     _res("degrees.enc", "state"), encrypt=True)


class QuestionPage(QtGui.QWizardPage):
    QUESTION_NUM = 0

    def __init__(self, question: Question, parent=None):

        super().__init__(parent)
        QuestionPage.QUESTION_NUM += 1
        self.id = QuestionPage.QUESTION_NUM
        self.degree = -1
        random.shuffle(question.answers)
        self.question = question
        self.valid = [question.answers.index(a) for a in self.question.answers if a.valid]
        self.is_radio = len(self.valid) == 1
        self.pic = QtGui.QLabel()

        my_layout = QtGui.QVBoxLayout()

        self.question = QtGui.QLabel("<font size=2 color=red><b>" + question.string + "</b></font>")
        self.question.setBackgroundRole(QtGui.QPalette.Background)
        self.question.setFont(QtGui.QFont("Times", weight=QtGui.QFont.Bold))
        self.question.setWordWrap(True)
        my_layout.addWidget(self.question)
        self.setTitle("سؤال رقم " + str(self.id))
        my_layout.addWidget(QtGui.QLabel("<hr>"))

        answers_images_lyt = QtGui.QHBoxLayout()
        answers_lyt = QtGui.QVBoxLayout()

        if self.is_radio:
            self.answers = QtGui.QButtonGroup()
            for a in question.answers:
                btn = QtGui.QRadioButton(a.string)
                btn.clicked.connect(self.answering)
                self.answers.addButton(btn)
                answers_lyt.addWidget(btn)
        else:
            self.answers = []
            for a in question.answers:
                btn = QtGui.QCheckBox(a.string)
                btn.stateChanged.connect(self.answering)
                answers_lyt.addWidget(btn)
                self.answers.append(btn)
                self.checkbox_clicked = 0

        answers_images_lyt.addLayout(answers_lyt, 3)
        answers_images_lyt.addStretch(1)
        answers_images_lyt.addWidget(self.pic, 2, alignment=QtCore.Qt.AlignRight)
        my_layout.addLayout(answers_images_lyt)
        if question.pic:
            self.pic.setPixmap(QtGui.QPixmap(_res(question.pic)))

        self.lcdScreen = QtGui.QLCDNumber()
        self.lcdScreen.setSegmentStyle(QtGui.QLCDNumber.Flat)

        my_layout.addItem(QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))
        my_layout.addWidget(QtGui.QLabel("<hr>"))
        child_layout = QtGui.QHBoxLayout()
        self.number_label = QtGui.QLabel()
        child_layout.addWidget(self.number_label, alignment=QtCore.Qt.AlignRight)
        vline = QtGui.QFrame()
        vline.setFrameShape(QtGui.QFrame.VLine)
        vline.setFrameShadow(QtGui.QFrame.Sunken)
        child_layout.addWidget(vline)
        child_layout.addWidget(self.lcdScreen, alignment=QtCore.Qt.AlignLeft)

        my_layout.addLayout(child_layout)

        self.setLayout(my_layout)

    def answering(self, state):

        if self.is_radio:
            valid = tuple(map(lambda x: -2 - x, self.valid))
            if self.answers.checkedId() == valid[0]:
                self.degree = self.wizard().degree_per_q
            else:
                self.degree = 0
        else:
            if state == QtCore.Qt.Checked:
                self.checkbox_clicked += 1
            elif state == QtCore.Qt.Unchecked:
                self.checkbox_clicked -= 1

            if len(self.valid) == self.checkbox_clicked:
                for i in self.answers:
                    if not i.isChecked():
                        i.setDisabled(True)
            elif len(self.valid) > self.checkbox_clicked:
                for i in self.answers:
                    if not i.isChecked():
                        i.setDisabled(False)

            # none is checked, this can't happen with the radio buttons
            if not any(i.isChecked() for i in self.answers):
                self.degree = -1
                return

            self.degree = 0
            for i, b in enumerate(self.answers):
                if b.isChecked() and i in self.valid:
                    self.degree += self.wizard().degree_per_q / len(self.valid)

    def initializePage(self):
        time = self.wizard().time
        self.lcdScreen.display("%d:%02d" % (time // 60, time % 60))
        self.number_label.setText(str(self.id) + " / " + str(QuestionPage.QUESTION_NUM))


# =======================================================

class ReasonFlag(str, aenum.Flag, settings=(aenum.AutoValue,)):
    _settings_ = aenum.AutoValue

    def __new__(cls, value, string):
        obj = str.__new__(cls, string)
        obj._value_ = value
        obj.string = string
        return obj

    @classmethod
    def _create_pseudo_member_values_(cls, members, *values):
        code = ";".join(m.string for m in members if m.string)
        return values + (code,)

    def __eq__(self, other):
        return type(self) is type(other) and self._value_ == other._value_

    def __ne__(self, other):
        return not self == other


# ========== Degrees Viewer && Questions Editor =========

# ==================== Inner Widgets ====================


class EditableLabel(QtGui.QLineEdit):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)

        self.setReadOnly(True)
        self.setStyleSheet("""
        QLineEdit:read-only {
            border: none;
            background: transparent;
        }

        QLineEdit {
            background: white;
        }
        """)

        def f():
            self.unsetCursor()
            self.setSelection(0, 0)
            self.setReadOnly(True)

        self.editingFinished.connect(f)

    def mouseDoubleClickEvent(self, event):
        self.setReadOnly(False)
        self.selectAll()


class IconButton(QtGui.QLabel):
    def __init__(self, icon: QtGui.QPixmap, index: int):
        super().__init__()

        self.icon = icon
        self.setPixmap(self.icon)
        self.index = index

        self.setStyleSheet("""

        IconButton {
            border: 2px solid rgba(221, 221, 221, 0.8);
            border-radius: 5px;
        }


        IconButton:hover {
            background-color: rgb(243, 232, 234);
        }
        """)

    def mouseReleaseEvent(self, event):
        self.clicked.emit(self.index)

    clicked = QtCore.pyqtSignal(int, name="clicked")


class QuestionImage(QtGui.QFrame):
    def __init__(self, image: str = None, parent=None):
        super().__init__(parent)

        self._path = image
        self.image = None
        if image is not None:
            self.image = os.path.basename(image)

        lyt = QtGui.QGridLayout()
        self.setLayout(lyt)
        self.close_btn = IconButton(QtGui.QPixmap(_res("cancel_red.png", "icon")), -1)
        self.close_btn.hide()
        self.close_btn.setToolTip("Remove the Image")
        self.close_btn.clicked.connect(self.hideImage)
        self.add_btn = IconButton(QtGui.QPixmap(_res("plus_green.png", "icon")), -1)
        self.add_btn.clicked.connect(self.choose_image)
        self.add_btn.setToolTip("Add an Image")
        self.lbl = QtGui.QLabel("<font size=10 color=grey><i>Insert an Image<i></font>")

        lyt.addWidget(self.close_btn, 1, 1)
        lyt.addWidget(self.add_btn, 1, 1)
        lyt.addWidget(self.lbl, 0, 0, 2, 2, alignment=QtCore.Qt.AlignCenter)
        lyt.setRowStretch(0, 1)
        lyt.setColumnStretch(0, 1)

        if image is not None:
            self.setImage(image)

    def setImage(self, image: str):
        assert image

        self.path = image
        self.imageShown.emit()

        self.add_btn.hide()
        self.close_btn.show()
        self.lbl.hide()

        self.setStyleSheet("""
            QuestionImage {{
                border-image: url("{}");
            }}
        """.format(image.replace("\\", "/")))  # fucking windows

    def hideImage(self):

        self.image = None

        self.imageHidden.emit()
        self.close_btn.hide()
        self.add_btn.show()
        self.lbl.show()

        self.setStyleSheet("""
            QuestionImage {
                border-image: none;
            }
        """)

    def choose_image(self):
        f, _ = QtGui.QFileDialog.getOpenFileNameAndFilter(self.parent(), filter="Images (*.png *.xpm *.jpg)")
        if f:
            self.setImage(f)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        if value is not None:
            self.image = os.path.basename(value)

    imageHidden = QtCore.pyqtSignal(name="imageHidden")
    imageShown = QtCore.pyqtSignal(name="imageShown")


class AnswerWidget(QtGui.QWidget):
    def __init__(self, answer: Answer, index: int, last=False, parent: QtGui.QWidget = None, **kwargs):
        QtGui.QWidget.__init__(self, parent, **kwargs)

        self._last = last
        self.index = index
        self.mod = None
        self.deleted = False

        lyt = QtGui.QHBoxLayout()

        self.add_pixmap = QtGui.QPixmap(_res("plus_green.png", "icon"))
        self.remove_pixmap = QtGui.QPixmap(_res("cancel_red.png", "icon"))

        self.setLayout(lyt)
        self.chk = chk = QtGui.QCheckBox()
        chk.stateChanged.connect(lambda x: self.validityChanged.emit(x == QtCore.Qt.Checked, self.index))
        if answer.valid:
            chk.toggle()

        lyt.addWidget(chk)

        self.edt = edt = EditableLabel("")  # to get the signal emitted
        edt.textChanged.connect(self.observe_text)
        edt.setText(answer.string)
        edt.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Maximum)
        edt.setAlignment(QtCore.Qt.AlignAbsolute)
        lyt.addWidget(edt)

        self.last = last

        lyt.setDirection(QtGui.QBoxLayout.LeftToRight)

    @property
    def last(self):
        return self._last

    @last.setter
    def last(self, value):
        self._last = value
        if self.mod is not None:
            self.mod.deleteLater()

        if value:
            self.mod = IconButton(self.add_pixmap, self.index)
            self.mod.clicked.connect(lambda: self.addRequest.emit(self.index))
            self.mod.setToolTip("Add an Answer")

            if not self.edt.text():
                self.isEmpty.emit(self.index)
        else:
            self.mod = IconButton(self.remove_pixmap, self.index)
            self.mod.clicked.connect(lambda: self.deleteRequest.emit(self.index))
            self.mod.setToolTip("Delete this Answer")

        self.layout().addWidget(self.mod)

    def observe_text(self, s: str) -> None:
        if s == "":
            self.isEmpty.emit(self.index)
        else:
            self.filled.emit(self.index)

    @property
    def answer(self):
        return Answer(self.edt.text(), self.chk.isChecked())

    isEmpty = QtCore.pyqtSignal(int, name="isEmpty")
    filled = QtCore.pyqtSignal(int, name="filled")
    addRequest = QtCore.pyqtSignal(int, name="addRequest")
    deleteRequest = QtCore.pyqtSignal(int, name="deleteRequest")
    validityChanged = QtCore.pyqtSignal(bool, int, name="validityChanged")


# =======================================================

# ==================== Degrees Viewer ===================


# class DegreesViewer(QtGui.QMainWindow):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.resize(580, 400)
#         self.setWindowTitle("Degrees Viewer")
#
#         self.parent_window = None
#
#         degree_view = QtGui.QTreeView()
#         degree_view.setRootIsDecorated(False)
#         degree_view.setAlternatingRowColors(True)
#         degree_model = QtGui.QStandardItemModel(0, 9)
#         degree_model.setHeaderData(0, QtCore.Qt.Horizontal, 'الاسم')
#         degree_model.setHeaderData(1, QtCore.Qt.Horizontal, 'المدرسة')
#         degree_model.setHeaderData(2, QtCore.Qt.Horizontal, 'الصف')
#         degree_model.setHeaderData(3, QtCore.Qt.Horizontal, 'رقم التليفون')
#         degree_model.setHeaderData(4, QtCore.Qt.Horizontal, 'الدرجة')
#         degree_model.setHeaderData(5, QtCore.Qt.Horizontal, 'من')
#         degree_model.setHeaderData(6, QtCore.Qt.Horizontal, 'لم يجب علي')
#         degree_model.setHeaderData(7, QtCore.Qt.Horizontal, 'أجاب خطأًً')
#         degree_model.setHeaderData(8, QtCore.Qt.Horizontal, 'الإمتحان')
#         degree_view.setModel(degree_model)
#         self.setCentralWidget(degree_view)
#
#         try:
#             files = glob.glob(os.path.join(DATA_PATH, "degrees*.enc"))
#             if len(files) == 0:
#                 QtGui.QMessageBox.warning(self, 'خطأ', "مفيش ولا ملف degrees*.enc")
#                 return
#
#             data, errs = parse_degrees(*files, encrypted=True)
#
#             if len(data) == 0 and not errs:
#                 QtGui.QMessageBox.warning(self, 'خطأ', "الملفات فاضية")
#                 return
#
#             if len(errs) > 0:
#                 QtGui.QMessageBox.warning(self, 'خطأ', "الملف(ات) %s فيها خطأ لذا متفتحتش" % ", ".join(errs))
#
#         except Exception as e:
#             QtGui.QMessageBox.warning(self, e.__class__.__name__, str(e))
#
#         else:
#             for i, name in enumerate(data):
#                 degree_model.insertRow(i)
#                 degree_model.setData(degree_model.index(i, 0), name)
#                 for j, head in enumerate(headers, 1):
#                     item = data[name][head]
#                     item = ((', '.join(map(lambda x: str(int(x) + 1), item)) if item else 'N/A')
#                             if isinstance(item, list) else item)
#                     degree_model.setData(degree_model.index(i, j), item)
#
#     def closeEvent(self, event):
#         if self.parent_window is not None:
#             self.parent_window.parent_window.show()
#         event.accept()
#

class DegreesViewer(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(900, 580)
        self.setWindowTitle("Degrees Viewer")

        self.parent_window = None

        degrees = parse_degrees(_res("degrees.enc", "state"), encrypted=True)
        degrees_widget = QtGui.QTableWidget(len(degrees), len(headers))
        degrees_widget.setHorizontalHeaderLabels(headers)
        degrees_widget.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)

        degrees_widget.setAlternatingRowColors(True)
        degrees_widget.setSortingEnabled(True)
        self.setCentralWidget(degrees_widget)

        for i, degree in enumerate(degrees):
            for j, header in enumerate(headers):
                item = getattr(degree, header)
                item = ((', '.join(map(lambda x: str(int(x) + 1), item)) if item else 'N/A')
                        if isinstance(item, list) else item)
                item = QtGui.QTableWidgetItem(item)
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                degrees_widget.setItem(i, j, QtGui.QTableWidgetItem(item))


# =======================================================

# =================== Questions Tabs ====================


class TestDetails(QtGui.QWidget):
    class PreserveFocusReason(ReasonFlag):
        NONE = ''
        INVALID_NAME = "Name cannot be less than three characters."

    def __init__(self, test: Test = None, parent: QtGui.QWidget = None):
        super().__init__(parent)

        lyt = QtGui.QGridLayout()
        self.want_focus_reasons = TestDetails.PreserveFocusReason.NONE
        self.setLayout(lyt)

        nameL = QtGui.QLabel("Test Name:")
        self.nameT = QtGui.QLineEdit()
        self.nameT.setPlaceholderText("Enter test name")
        nameL.setBuddy(self.nameT)
        self.nameT.textChanged.connect(self.observe_name)

        descriptionL = QtGui.QLabel("Test Description:")
        self.descriptionT = QtGui.QTextEdit()
        descriptionL.setBuddy(self.descriptionT)

        timeL = QtGui.QLabel("Test Time:")
        self.timeT = QtGui.QTimeEdit()
        self.timeT.setDisplayFormat("hh:mm:ss")
        self.timeT.setTimeRange(QtCore.QTime(0, 15), QtCore.QTime(4, 0))
        timeL.setBuddy(self.timeT)

        degreeL = QtGui.QLabel("Test Degree:")
        self.degreeT = QtGui.QDoubleSpinBox()
        self.degreeT.setDecimals(1)
        self.degreeT.setRange(15, 300)
        degreeL.setBuddy(self.degreeT)

        self.status = QtGui.QLabel()

        lyt.addWidget(nameL, 0, 0)
        lyt.addWidget(self.nameT, 0, 1)

        lyt.addWidget(descriptionL, 1, 0)
        lyt.addWidget(self.descriptionT, 1, 1, 2, 2)

        lyt.addWidget(timeL, 3, 0)
        lyt.addWidget(self.timeT, 3, 1)

        lyt.addWidget(degreeL, 4, 0)
        lyt.addWidget(self.degreeT, 4, 1)

        lyt.addWidget(self.status, 5, 0, 1, 2)

        if test is not None:
            self.nameT.setText(test.name)
            self.descriptionT.setPlainText(test.description)
            self.timeT.setTime(QtCore.QTime(0, 0).addSecs(test.time))
            self.degreeT.setValue(test.degree)

    def observe_name(self, s: str):
        self._check_reason(TestDetails.PreserveFocusReason.INVALID_NAME, len(s) < 3)
        if not len(s) < 3:
            self.nameChanged.emit(s)

    def _check_reason(self, reason: PreserveFocusReason, happened: bool):
        mod = False
        if happened:
            if reason not in self.want_focus_reasons:
                self.want_focus_reasons |= reason
                mod = True
        else:
            if reason in self.want_focus_reasons:
                self.want_focus_reasons ^= reason
                mod = True

        if mod:
            self.wantFocusChanged.emit(self.want_focus_reasons)
            self.status.setText("<font color=red>{}</font>"
                                .format("<br>".join(self.want_focus_reasons.split(";"))))

    @property
    def test(self):
        time = self.timeT.time()  # type: QtCore.QTime
        return Test(self.nameT.text(), self.descriptionT.toPlainText(),
                    time.second() + time.minute() * 60 + time.hour() * 60 * 60,
                    [], self.degreeT.value(), [])

    wantFocusChanged = QtCore.pyqtSignal(PreserveFocusReason, name="wantFocusChange")
    nameChanged = QtCore.pyqtSignal(str, name="nameChanged")


class QuestionTab(QtGui.QWidget):
    class PreserveFocusReason(ReasonFlag):
        NONE = ''
        EMPTY_QUESTION = "Question cannot be empty."
        NUMBER_OF_ANSWERS = "Number of answers cannot be less than 2."
        NO_CORRECT_ANSWER = "A question cannot have no correct answers."

    def __init__(self, question: Question = None, index: int = -1, parent: QtGui.QWidget = None):
        super().__init__(parent)

        self.want_focus_reasons = QuestionTab.PreserveFocusReason.NONE
        self.answers_lyt = QtGui.QVBoxLayout()
        self.s_question = question or Question("", None, [Answer("", False)])
        self.answers = []  # type: List[AnswerWidget]
        self.deleted = False
        self.image = QuestionImage(self.s_question.pic and _res(self.s_question.pic))
        self.disabled_because = set()
        self.questionT = QtGui.QTextEdit()
        self.questionT.textChanged.connect(self.observe_name)
        self.answers_num = 0
        self.valid_num = 0
        self.index = index

        if not self.s_question.string:
            self.questionT.setPlainText("Enter question")
            self.questionT.selectAll()
        else:
            self.questionT.setPlainText(self.s_question.string)

        lyt = QtGui.QVBoxLayout()
        self.setLayout(lyt)

        wrap = QtGui.QWidget()
        wrap.setStyleSheet("background-color: transparent;")
        wrap.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Maximum)
        wrap.setLayout(self.answers_lyt)
        self.scroll = answers_scroll = QtGui.QScrollArea()
        answers_scroll.setWidget(wrap)
        answers_scroll.setWidgetResizable(True)
        answers_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        image_and_answers = QtGui.QHBoxLayout()
        image_and_answers.addWidget(answers_scroll, 3)

        image_lyt = QtGui.QVBoxLayout()
        image_lyt.addWidget(self.image, 3)
        image_lyt.addWidget(QtGui.QLabel(), 2)

        image_and_answers.addLayout(image_lyt, 2)

        lyt.addWidget(self.questionT, 1)
        lyt.addWidget(QtGui.QLabel("<hr>"))
        lyt.addLayout(image_and_answers, 2)
        self.status = QtGui.QLabel()
        lyt.addWidget(self.status)

        self.add_answers(self.s_question.answers)

    def add_answer(self, e=None, answer: Answer = None):

        if len(self.answers) > 0:
            self.answers[-1].last = False

        if answer is None:
            answer = Answer("", False)

        answer_widget = AnswerWidget(answer, len(self.answers), last=True,
                                     deleteRequest=self.delete_answer, addRequest=self.add_answer,
                                     validityChanged=self.validity_changed)
        answer_widget.filled.connect(self.filled_answer)
        answer_widget.isEmpty.connect(self.empty_answer)

        if not answer.string:
            answer_widget.mod.setDisabled(True)

        self.answers.append(answer_widget)
        self.answers_lyt.addWidget(answer_widget)
        self.answers_num += 1

        self._check_reason(QuestionTab.PreserveFocusReason.NUMBER_OF_ANSWERS, self.answers_num < 2)

    def add_answers(self, answers: List[Answer]):
        assert answers

        if len(self.answers) > 0:
            self.answers[-1].last = False

        for i, answer in enumerate(answers):

            if i != 0 and not answer.string:
                continue

            widget = AnswerWidget(answer, len(self.answers),
                                  deleteRequest=self.delete_answer, addRequest=self.add_answer,
                                  validityChanged=self.validity_changed)
            widget.filled.connect(self.filled_answer)
            widget.isEmpty.connect(self.empty_answer)

            self.answers.append(widget)
            self.answers_lyt.addWidget(widget)

        self.answers[-1].last = True

        self.answers_num += len(answers)

        self._check_reason(QuestionTab.PreserveFocusReason.NUMBER_OF_ANSWERS, self.answers_num < 2)

    def delete_answer(self, index):
        if len(self.disabled_because) == 1 and index in self.disabled_because:
            self.disabled_because.clear()
            self.answers[-1].mod.setEnabled(True)

        self.answers_num -= 1
        self.answers[index].deleted = True
        self.answers[index].deleteLater()

        self._check_reason(QuestionTab.PreserveFocusReason.NUMBER_OF_ANSWERS, self.answers_num < 2)

    def validity_changed(self, checked, index):
        if checked:
            self.valid_num += 1
        else:
            self.valid_num -= 1

        self._check_reason(QuestionTab.PreserveFocusReason.NO_CORRECT_ANSWER, self.valid_num <= 0)

    def empty_answer(self, index):
        self.disabled_because.add(index)
        if len(self.disabled_because) == 1:
            self.answers[-1].mod.setDisabled(True)

    def filled_answer(self, index):
        if index in self.disabled_because:
            self.disabled_because.remove(index)
        if len(self.disabled_because) == 0:
            self.answers[-1].mod.setDisabled(False)

    def _check_reason(self, reason: PreserveFocusReason, happened: bool):
        mod = False
        if happened:
            if reason not in self.want_focus_reasons:
                self.want_focus_reasons |= reason
                mod = True
        else:
            if reason in self.want_focus_reasons:
                self.want_focus_reasons ^= reason
                mod = True

        if mod:
            self.wantFocusChanged.emit(self.index, self.want_focus_reasons)
            self.status.setText("<font color=red>{}</font>"
                                .format("<br>".join(self.want_focus_reasons.split(";"))))

    def observe_name(self):
        self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_QUESTION, not self.questionT.toPlainText())

    @property
    def edited(self):
        return self.s_question == self.question

    @property
    def question(self):
        return Question(self.questionT.toPlainText(), self.image.image,
                        [ans.answer for ans in self.answers if not ans.deleted])

    wantFocusChanged = QtCore.pyqtSignal(int, PreserveFocusReason, name="wantFocusChanged")


class DeletedQuestion(QtGui.QWidget):
    def __init__(self, question: QuestionTab, index: int, parent: QtGui.QWidget = None):
        super().__init__(parent)

        self.question = question
        self.question.deleted = True
        self._index = index

        self.link = QtGui.QLabel("<a href='#undo'>Undo Close Question {}</a>".format(self.index))
        self.link.setOpenExternalLinks(False)

        def f(s):
            self.question.deleted = False
            self.openRequested.emit(self.index)

        self.link.linkActivated.connect(f)

        lyt = QtGui.QVBoxLayout()
        self.setLayout(lyt)

        lyt.addWidget(self.link, alignment=QtCore.Qt.AlignCenter)

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, value):
        self._index = value
        self.link.setText("<a href='#undo'>Undo Close Question {}</a>".format(self.index))

    openRequested = QtCore.pyqtSignal(int, name="openRequested")


class QuestionsTabWidget(QtGui.QTabWidget):

    def __init__(self, test: Test, index: int, parent: QtGui.QWidget = None):
        super().__init__(parent)

        self.index = index
        self.s_test = test
        self.setTabsClosable(True)
        self.setUpdatesEnabled(True)
        self.setMovable(True)
        self.current_index = -1
        self.reasons = OrderedDict()

        btn = QtGui.QToolButton()
        btn.setIcon(QtGui.QIcon(_res("add.png", "icon")))
        btn.clicked.connect(self.add_question)
        self.setCornerWidget(btn)

        details = TestDetails(test)
        self.reasons[0] = TestDetails.PreserveFocusReason.NONE

        details.wantFocusChanged.connect(lambda r: self.updateErrors.emit(self.errors))
        details.nameChanged.connect(self.name_changed)
        self.addTab(details, "Details")
        self.tabBar().tabButton(0, QtGui.QTabBar.RightSide).resize(0, 0)  # makes it not closable
        # self.tabBar().tabMoved.connect(self._check_questions_name)
        self.tabBar().tabMoved.connect(self.tab_moved)

        for question in test.questions:
            self.add_question(question=question, setfocus=False)

        self.tabCloseRequested.connect(self.delete_question)

    def name_changed(self, s):
        self.nameChanged.emit(self.index, s)

    def delete_question(self, index):

        old_ques = self.widget(index)
        if (isinstance(old_ques, DeletedQuestion)
                and QtGui.QMessageBox.question(self, "Are you sure?",
                                               "Are you sure you want to <font color=red>force delete</font> Q %d?"
                                               " This cannot be <b><font color=red>undone</font></b>." % index,
                                               QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes):

            self.removeTab(index)
            self._check_questions_name(*range(index, self.count()))

        elif QtGui.QMessageBox.question(self, "Are you sure?", "Are you sure you want to delete Q %d?" % index,
                                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            self.removeTab(index)
            del_ques = DeletedQuestion(old_ques, index, self)
            del_ques.openRequested.connect(self.open_deleted_question)
            self.insertTab(index, del_ques, "Q %d (Deleted)" % index)
            self.tabBar().tabButton(index, QtGui.QTabBar.RightSide).setToolTip("Force Delete Question")
            self.setCurrentIndex(index)
            del self.reasons[index]
            self.updateErrors.emit(self.errors)

    def add_question(self, _=False, question=None, setfocus=True):
        index = self.count()
        tab = QuestionTab(question, index)
        self.reasons[index] = QuestionTab.PreserveFocusReason.NONE
        tab.wantFocusChanged.connect(lambda i, r: self.updateErrors.emit(self.errors))
        self.addTab(tab, "Q %d" % self.count())
        tab.questionT.setFocus()
        btn = self.tabBar().tabButton(index, QtGui.QTabBar.RightSide)  # type: QtGui.QAbstractButton
        btn.setToolTip("Delete Question")
        if setfocus:
            self.setCurrentIndex(index)

    def set_reason(self, index: int, reason: Union[QuestionTab.PreserveFocusReason, TestDetails.PreserveFocusReason]):
        self.reasons[index] = reason
        self.updateErrors.emit(self.errors)

    def _check_questions_name(self, *locations):
        for loc in locations:
            wid = self.widget(loc)
            fmt = "Q %d" % loc
            if isinstance(wid, DeletedQuestion):
                fmt += " (Deleted)"
                wid.index = loc

            self.setTabText(loc, fmt)

    def tab_moved(self, *args):
        self.updateErrors.emit(self.errors)
        self._check_questions_name(*args)

    def open_deleted_question(self, index):
        question = self.widget(index).question
        self.removeTab(index)
        self.insertTab(index, question, "Q %d" % index)
        self.tabBar().tabButton(index, QtGui.QTabBar.RightSide).setToolTip("Delete Question")
        self.setCurrentIndex(index)
        self.reasons[index] = question.want_focus_reasons
        self.updateErrors.emit(self.errors)

    @property
    def test(self):
        details = self.widget(0).test  # type: Test
        return Test(details.name, details.description, details.time,
                    [self.widget(i).question for i in range(1, self.count()) if
                     isinstance(self.widget(i), QuestionTab)],
                    details.degree, [])

    @property
    def edited(self):
        return self.test != self.s_test

    @property
    def errors(self):
        errs = OrderedDict()

        details_reason = self.widget(0).want_focus_reasons
        if details_reason != TestDetails.PreserveFocusReason.NONE:
            errs[0] = details_reason

        for i in range(1, self.count()):
            reason = self.widget(i).want_focus_reasons
            if reason != QuestionTab.PreserveFocusReason.NONE:
                errs[i] = reason

        return errs

    nameChanged = QtCore.pyqtSignal(int, str, name="nameChanged")
    updateErrors = QtCore.pyqtSignal(OrderedDict, name="updateErrors")


class QuestionsEditor(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        toolBar = QtGui.QToolBar()
        toolBar.setMovable(False)
        toolBar.addSeparator()
        save_btn = QtGui.QPushButton(QtGui.QIcon(_res("save.png", "icon")), "")
        toolBar.addWidget(save_btn)
        self.addToolBar(toolBar)
        self.setWindowTitle("Questions Editor")

        sts_bar = QtGui.QStatusBar()
        sts_bar.setStyleSheet("QStatusBar { background-color: #ccc; border-top: 1.5px solid grey } ")
        self.sts_bar_lbl = QtGui.QLabel("Ready.")
        self.sts_bar_lbl.setOpenExternalLinks(False)
        self.sts_bar_lbl.linkActivated.connect(lambda i: self.questions_tabs.setCurrentIndex(int(i)))
        sts_bar.addWidget(self.sts_bar_lbl)
        self.setStatusBar(sts_bar)

        self.resize(1000, 600)
        self._cache = {}
        self.parent_window = None
        self._current_row = 0

        frm = QtGui.QFrame()
        self.lyt = lyt = QtGui.QGridLayout()
        frm.setLayout(lyt)
        self.setCentralWidget(frm)

        lyt.setMargin(10)

        self.tests = QtGui.QListWidget()
        self.tests.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tests.currentItemChanged.connect(self.item_changed)
        for test in TESTS:
            QtGui.QListWidgetItem(test.name, self.tests)
        self.tests.setCurrentItem(self.tests.item(0))

        leftSide = QtGui.QVBoxLayout()
        leftSide.addWidget(QtGui.QLabel("Available Tests:"))
        leftSide.addWidget(self.tests)
        self.btn_add_test = btn_add_test = QtGui.QPushButton()
        btn_add_test.setToolTip("Add a new test")
        btn_add_test.setIcon(QtGui.QIcon(_res("add.png", "icon")))
        btn_add_test.clicked.connect(self.add_test)

        self.btn_remove_test = btn_remove_test = QtGui.QPushButton()
        btn_remove_test.setToolTip("Remove selected test")
        btn_remove_test.setIcon(QtGui.QIcon(_res("minus.png", "icon")))
        btn_remove_test.clicked.connect(self.remove_test)

        buttons = QtGui.QHBoxLayout()
        buttons.addWidget(btn_add_test, alignment=QtCore.Qt.AlignLeft)
        buttons.addStretch(1)
        buttons.addWidget(btn_remove_test, alignment=QtCore.Qt.AlignRight)

        leftSide.addLayout(buttons)

        lyt.addLayout(leftSide, 0, 0, 3, 1)

        lyt.addWidget(QtGui.QLabel(), 0, 2, 3, 1)

        self.questions_tabs = QuestionsTabWidget(TESTS[0], 0)
        self.questions_tabs.updateErrors.connect(self.update_status_bar)
        self.questions_tabs.nameChanged.connect(self.update_name)
        self._cache[0] = self.questions_tabs
        lyt.addWidget(self.questions_tabs, 0, 3, 3, 3)

        lyt.setColumnStretch(3, 1)
        lyt.setRowStretch(1, 1)

    def add_test(self, _):
        q = QtGui.QDialog(self)
        q.setWindowTitle("Enter Test Details")
        q.setModal(True)
        lay = QtGui.QVBoxLayout()
        q.setLayout(lay)
        test_widg = TestDetails()
        q.test = test_widg
        lay.addWidget(test_widg)
        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
                                         QtCore.Qt.Horizontal, q)
        buttons.button(QtGui.QDialogButtonBox.Ok).setDisabled(True)
        q.buttons = buttons
        test_widg.isEmpty.connect(lambda: buttons.button(QtGui.QDialogButtonBox.Ok).setDisabled(True))
        test_widg.filled.connect(lambda: buttons.button(QtGui.QDialogButtonBox.Ok).setDisabled(False))

        def f():
            test_obj = test_widg.test
            if not any(test_obj.name == t for t in TESTS):
                q.accept()
                QtGui.QListWidgetItem(test_obj.name, self.tests)
                TESTS.append(test_obj)
            else:
                QtGui.QMessageBox.warning(q, "Error",
                                          "Test '%s' already exists, please choose another name" % test_obj.name)

        buttons.accepted.connect(f)
        buttons.rejected.connect(q.reject)
        lay.addWidget(buttons)
        q.show()

    def remove_test(self):
        if QtGui.QMessageBox.question(self, "Are you sure?", "Are you sure you want to delete '%s' ? This "
                                                             "<font color=red><b>cannot</b></font> be <font color=red>"
                                                             "<b>undone</b></font>" % self.tests.currentItem().text(),
                                      QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            index = self.tests.row(self.tests.currentItem())
            del self._cache[index]
            self.tests.takeItem(index)

    def update_name(self, index: int, string: str):
        self.tests.item(index).setText(string)

    def item_changed(self, current: QtGui.QListWidgetItem, previous: QtGui.QListWidgetItem):

        previous_index = self.tests.row(previous)
        current_index = self.tests.row(current)

        if current_index == self._current_row:
            return

        errs = self._cache[previous_index].errors
        if len(errs) != 0:
            locs = ", ".join(_tab_repr(i) for i in errs)
            QtGui.QMessageBox.warning(self, "Cannot Change The Current Test.",
                                      "Test `{}` has some errors so you can't leave it. See the {} tab{}."
                                      .format(previous.text(), locs, 's' if len(errs) > 1 else ''))

            QtCore.QTimer.singleShot(0, lambda: self.tests.setCurrentRow(self._current_row))
            return
        else:
            self._current_row = self.tests.row(current)

        self.questions_tabs.hide()
        if current_index not in self._cache:
            self._cache[current_index] = self.questions_tabs = QuestionsTabWidget(TESTS[current_index], current_index)
            self.questions_tabs.updateErrors.connect(self.update_status_bar)
            self.questions_tabs.nameChanged.connect(self.update_name)
            self.lyt.addWidget(self.questions_tabs, 0, 3, 3, 3)
        else:
            self.questions_tabs = self._cache[current_index]
            self.questions_tabs.show()

    def update_status_bar(self, errs: OrderedDict):

        if errs:
            self.sts_bar_lbl.setText("Error in the {} tab{}."
                                     .format(", ".join("<a href='{}'>{}</a>".format(i, _tab_repr(i)) for i in errs),
                                             's' if len(errs) > 1 else ''))
        else:
            self.sts_bar_lbl.setText("Ready.")

    @property
    def edited(self):
        return any(wid.edited for wid in self._cache.values())

    def closeEvent(self, event):
        if self.edited:
            rslt = QtGui.QMessageBox.question(self, "Are you sure you want to exit?",
                                              "You have some unsaved changes.",
                                              QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
            if rslt == QtGui.QMessageBox.Yes:
                print("Clicked Yes.")
            elif rslt == QtGui.QMessageBox.No:
                event.accept()
            else:
                event.ignore()
                return

        if self.parent_window is not None:
            self.parent_window.parent_window.show()
        event.accept()


# =======================================================

# =======================================================

# ==================== Outer Widgets ====================


class Auth(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auth")
        self.setFixedSize(350, 200)
        self.parent_window = None

        frm = QtGui.QFrame(self)
        self.setCentralWidget(frm)

        lyt = QtGui.QGridLayout()
        self.types = QtGui.QButtonGroup()

        self.questions = QtGui.QRadioButton("Questions Editor")
        self.questions.toggle()  # make it pressed by default
        self.degrees = QtGui.QRadioButton("Degrees Viewer")
        self.types.addButton(self.questions)
        self.types.addButton(self.degrees)

        lyt.addWidget(self.questions, 0, 0)
        lyt.addWidget(self.degrees, 0, 1)

        lyt.addWidget(QtGui.QLabel(), 1, 0)

        nameL = QtGui.QLabel("Enter your Name:")
        self.nameT = QtGui.QLineEdit(self)
        self.nameT.setFocus()
        self.nameT.setPlaceholderText("Enter your name")
        nameL.setBuddy(self.nameT)

        passwordL = QtGui.QLabel("Enter your password:")
        self.passwordT = QtGui.QLineEdit(self)
        self.passwordT.setPlaceholderText("Enter your password")
        self.passwordT.setEchoMode(QtGui.QLineEdit.Password)
        passwordL.setBuddy(self.passwordT)

        lyt.addWidget(nameL, 2, 0)
        lyt.addWidget(self.nameT, 2, 1)
        lyt.addWidget(passwordL, 3, 0)
        lyt.addWidget(self.passwordT, 3, 1)

        self.status = QtGui.QLabel()
        lyt.addWidget(self.status, 4, 0, 1, 2)

        btn = QtGui.QPushButton("Login")
        btn.clicked.connect(self.login)
        lyt.addWidget(btn, 5, 1)

        frm.setLayout(lyt)

    def login(self):
        name = self.nameT.text()
        password = self.passwordT.text()
        if (
                hashlib.md5(name.encode()).digest() == b'\tM\x84\x1b\x8f\x171\x8bZ\xf6h\xa2\xe7\xde"P'
                and hashlib.md5(password.encode()).digest() == b'\xec+\xb9B\xd9\xcb>\xc6dh\xe5\xcc=\xfa\x144'
        ):
            if self.degrees.isChecked():
                widget = DegreesViewer()
            else:
                widget = QuestionsEditor()
            CURRENT_ACTIVE[0] = widget
            widget.parent_window = self
            center_widget(widget)
            widget.show()
            self.hide()
        else:
            fmt = "<font color=red>%s</font>"
            if not name and not password:
                fmt %= "Name and Password fields can't be empty"
            elif not name:
                fmt %= "Name field can't be empty"
            elif not password:
                fmt %= "Password field can't be empty"
            else:
                fmt %= "Invalid username or password"

            self.status.setText(fmt)

            if name:
                self.passwordT.setFocus()
                self.passwordT.selectAll()
            elif password:
                self.nameT.setFocus()

    def closeEvent(self, event):
        if self.parent_window is not None:
            self.parent_window.show()
        event.accept()


# ==================== Initial Window ==================


class TestCard(QtGui.QFrame):
    def __init__(self, test: Test, index: int, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.index = index

        self.setFrameShadow(QtGui.QFrame.Sunken)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        lyt = QtGui.QGridLayout()
        lyt.addWidget(QtGui.QLabel("<b><font size=5>%s</font></b>" % test.name), 0, 0, alignment=QtCore.Qt.AlignLeft)
        lyt.addWidget(QtGui.QLabel("<hr>"), 1, 0, 1, 2)
        lyt.addWidget(QtGui.QLabel("<font size=3 color=grey>%s</font>" % (test.description or "لا يوجد وصف")),
                      1, 0, 2, 2, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("افتح", self)
        btn.setIcon(QtGui.QIcon("arrow.png"))
        btn.clicked.connect(self.open)
        lyt.addWidget(QtGui.QLabel(), 2, 0)
        text = re.sub(r'\b(\d+)\b', r'<b>\1</b>', "%s | %d درجة | %d سؤال"
                      % (format_secs(test.time), int(test.degree), len(test.questions)))
        lyt.addWidget(QtGui.QLabel("<font size=3 color=grey>%s</font>" % text),
                      3, 0, 1, 2, alignment=QtCore.Qt.AlignLeft)
        lyt.addWidget(btn, 4, 1, alignment=QtCore.Qt.AlignRight)

        self.setLayout(lyt)

    def open(self):
        self.chose.emit(self.index)

    chose = QtCore.pyqtSignal(int, name="chose")


class TestChooser(QtGui.QWidget):  # the real MainWindow is a QWidget, that's funny :")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إختر امتحانًا")
        self.setWindowIcon(QtGui.QIcon(_res("test.ico", "icon")))
        self.resize(600, 300)
        lyt = QtGui.QVBoxLayout()

        wrap = QtGui.QWidget()
        wrap.setLayout(lyt)
        scroll = QtGui.QScrollArea()
        scroll.setWidget(wrap)
        topmost = QtGui.QVBoxLayout()
        scroll.setWidgetResizable(True)
        topmost.addWidget(scroll)
        self.setLayout(topmost)
        lyt.setMargin(8)

        a = len(TESTS)

        if a == 0:
            lyt.addWidget(QtGui.QLabel("لا يوجد أية إمتحان، اضف واحدًا لتكمل."), alignment=QtCore.Qt.AlignCenter)
            return

        for i, test in enumerate(TESTS):
            lyt.addWidget(TestCard(test, i, self, chose=self.chose))

        if a > 1:
            lyt.addWidget(QtGui.QLabel("<hr>"))
            lyt.addWidget(QtGui.QLabel("النهاية"), alignment=QtCore.Qt.AlignCenter)

        login_link = QtGui.QLabel("<a href='#open'>Open questions editor</a>")
        login_link.setOpenExternalLinks(False)

        def f(s):
            auth = Auth()
            center_widget(auth)
            auth.parent_window = self
            auth.show()
            CURRENT_ACTIVE[0] = auth
            self.hide()

        login_link.linkActivated.connect(f)

        topmost.addWidget(QtGui.QLabel("<hr>"))
        dwn = QtGui.QHBoxLayout()
        dwn.addWidget(QtGui.QLabel())
        dwn.addWidget(QtGui.QLabel("{} Test{}".format(a, 's' if a > 1 else '')), alignment=QtCore.Qt.AlignCenter)
        dwn.addWidget(login_link, alignment=QtCore.Qt.AlignRight)
        topmost.addLayout(dwn)

    def chose(self, index):
        wizard = TestWizard(TESTS[index])
        CURRENT_ACTIVE[0] = wizard
        wizard.parent_window = self
        center_widget(wizard)
        wizard.show()
        self.hide()


# =======================================================

# =======================================================


def main():
    _init()
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName("Examer")
    app.setApplicationVersion("0.1")
    app.setWindowIcon(QtGui.QIcon(_res("test.ico", "icon")))
    main_widget = QuestionsEditor()
    center_widget(main_widget)
    main_widget.show()
    app.exec_()
    del main_widget
    del app
    _defer()


if __name__ == '__main__':
    main()
