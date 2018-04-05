# -*- coding: utf-8 -*-

"""
:author: Fady Adel (2masadel at gmail dot com)
:link: https://github.com/faddyy
"""


from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import datetime
import glob
import json
import os
import random
import re
import sys
from collections import namedtuple

from PyQt4 import QtGui, QtCore
from typing import List, Dict, Union, Tuple

if sys.version_info[0] < 3:
    str = unicode
    chr = unichr

# =======================================================

headers = ['school',
           'grade',
           'number',
           'degree',
           'out_of',
           'left',
           'failed_at',
           'test',
           ]

# ==================== Data Holders =====================
Answer = namedtuple("Answer", "string valid")
Question = namedtuple("Question", "string pic answers")
Test = namedtuple("Test", "name description time questions degree")


# =======================================================


# ==================== Util Function ====================
def parse_tests(file_name):
    # type: (str) -> List[Test]

    with open(file_name) as f:
        tests = json.load(f)

    test_list = []
    for test in tests:
        name = test
        test = tests[test]
        questions = [Question(q["question"], q["pic"], [Answer(a, i in q["valid"]) for i, a in enumerate(q["answers"])])
                     for q in test["questions"]]

        test_list.append(Test(name, test["description"], test["time"], questions, test["degree"]))

    return test_list


def parse_degrees(*args):
    # type: (*str) -> Tuple[Dict[str, Dict[str, Union[float, int, str]]], List[str]]

    assert not args

    data = {}
    errs = []
    err = False
    for fn in args:
        with open(fn) as f:
            d = json.load(f)
            for j in d.values():
                if len(set(j.keys()) & set(headers)) < len(headers):
                    errs.append(fn)
                    err = True
                    break

            if err:
                err = False
                continue

            data.update(d)

    return data, errs


def center_widget(widget):
    # type: (QtGui.QWidget) -> None
    widget.move(QtGui.QApplication.desktop().screen().rect().center() - widget.rect().center())


def rot13(string):
    # type: (str) -> str
    return "".join(map(lambda c: chr(ord(c) + 13), list(string)))


def format_secs(seconds, sp=("ساعة", "دقيقة", "ثانية"), sep="، "):
    return sep.join(["%d %s" % (int(d), s) for d, s in zip(str(datetime.timedelta(seconds=seconds)).split(':'), sp)
                     if not int(d) == 0])


# =======================================================


TESTS = parse_tests("tests.json")
questions = [Question("sad", None, [Answer("Fuck", False)] * 3)] * 3
TESTS.extend([Test("Hey", "you!", 5000, questions, 3), Test("Hello", "asda", 2200, questions, 3),
              Test("How", "are you?", 2705, questions, 5)])


# ======================= Test Wizard =======================

class TestWizard(QtGui.QWizard):
    degrees = []

    def __init__(self, test, parent=None):
        # type: (Test, QtGui.QWidget) -> None
        super(TestWizard, self).__init__(parent)
        self.test = test
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
        self.setWindowIcon(QtGui.QIcon("data/test.ico"))

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

        #: validation happens in the last question page (-2 by index of pages)
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
        return super(TestWizard, self).nextId()

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

    def closeEvent(self, event):
        # type: (QtGui.QCloseEvent) -> None
        if not self.pageIds()[-1] > self.currentId() > 0:
            event.accept()
        elif (QtGui.QMessageBox.question(self, "هل انت متأكد؟", "انت علي وشك ان تغلق النافذة، كل الإجابات سوف تنسي.",
                                         QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)) == QtGui.QMessageBox.Yes:
            self.parent().show()
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
        super(FormPage, self).__init__(parent)

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

        if len(self.nameedit.text().simplified().split(" ")) < 2:
            QtGui.QMessageBox.information(self, "خطأ في الاسم", 'يرجي ادخال الاسم ثنائيا او اكثر')
        elif self.gradecombo.currentText() == "<ادخل صفك>":
            QtGui.QMessageBox.information(self, "خطأ في الصف", 'يرجي ادخال الصف')
        else:
            return True

        return False


class FinalPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(FinalPage, self).__init__(parent)
        my_layout = QtGui.QGridLayout()
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
        my_layout.addWidget(details_group, 2, 1)
        my_layout.addItem(QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding), 0, 0, 2, 2)

        degree_view = QtGui.QTreeView()
        degree_view.setRootIsDecorated(False)
        degree_view.setAlternatingRowColors(True)

        self.degree_model = QtGui.QStandardItemModel(0, 3)
        self.degree_model.setHeaderData(0, QtCore.Qt.Horizontal, "درجة السؤال الواحد")
        self.degree_model.setHeaderData(1, QtCore.Qt.Horizontal, "المجموع")
        self.degree_model.setHeaderData(2, QtCore.Qt.Horizontal, "الدرجة")
        degree_view.setModel(self.degree_model)
        my_layout.addWidget(degree_view, 2, 0)

        self.setLayout(my_layout)

    def initializePage(self):

        degrees = self.wizard().degrees
        test = self.wizard().test
        name = self.field("name").toString()
        school = self.field("school").toString()
        grade = FormPage.GRADES[self.field("grade").toInt()[0] - 1]
        number = self.field("number").toString()
        sum_of_degrees = sum(i for i in degrees if i != -1)

        if number.startsWith("01") and len(number) == 11:
            number = "+2" + number

        self.nameL.setText(name)
        self.schoolL.setText(school)
        self.gradeL.setText(grade)
        self.numberL.setText(number)

        vm = self.degree_model
        vm.insertRow(0)
        vm.setData(vm.index(0, 0), self.wizard().degree_per_q)
        vm.setData(vm.index(0, 1), test.degree)
        vm.setData(vm.index(0, 2), sum_of_degrees)

        failed_at = []
        left = []
        for i, v in enumerate(degrees):
            if v == 0:
                failed_at.append(i)
            elif v == -1:
                left.append(i)

        user = dict(zip(headers, [str(school),
                                  str(grade),
                                  str(number),
                                  sum_of_degrees,
                                  test.degree,
                                  left,
                                  failed_at,
                                  test.name,
                                  ]))

        if not os.path.exists("degrees.json"):
            with open("degrees.json", "w") as f:
                f.write("{}")

        with open("degrees.json", "r") as f:
            try:
                data = json.load(f)
            except ValueError as e:
                print("error" + str(e))
                data = {}

        with open("degrees.json", "w") as f:
            data[str(name)] = user
            json.dump(data, f)


class QuestionPage(QtGui.QWizardPage):
    QUESTION_NUM = 0

    def __init__(self, question, parent=None):
        # type: (Question, QtGui.QWidget) -> None

        super(QuestionPage, self).__init__(parent)
        QuestionPage.QUESTION_NUM += 1
        self.id = QuestionPage.QUESTION_NUM
        self.degree = -1
        random.shuffle(question.answers)
        self.question = question
        self.valid = [question.answers.index(a) for a in self.question.answers if a.valid]
        self.is_radio = len(self.valid) == 1

        my_layout = QtGui.QVBoxLayout()

        self.question = QtGui.QLabel("<font size=2 color=red><b>" + question.string + "</b></font>")
        self.question.setBackgroundRole(QtGui.QPalette.Background)
        self.question.setFont(QtGui.QFont("Times", weight=QtGui.QFont.Bold))
        self.question.setWordWrap(True)
        my_layout.addWidget(self.question)
        self.setTitle("سؤال رقم " + str(self.id))
        my_layout.addWidget(QtGui.QLabel("<hr>"))

        if self.is_radio:
            self.answers = QtGui.QButtonGroup()
            for a in question.answers:
                btn = QtGui.QRadioButton(a.string)
                btn.clicked.connect(self.answering)
                self.answers.addButton(btn)
                my_layout.addWidget(btn)
        else:
            self.answers = []
            for a in question.answers:
                btn = QtGui.QCheckBox(a.string)
                btn.stateChanged.connect(self.answering)
                my_layout.addWidget(btn)
                self.answers.append(btn)
                self.checkbox_clicked = 0

        self.pic = QtGui.QLabel()
        my_layout.addWidget(self.pic)
        if question.pic:
            self.pic.setPixmap(QtGui.QPixmap(question.pic["name"]))
            self.pic.setFixedSize(*question.pic["size"])

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
            if state == 2:
                self.checkbox_clicked += 1
            elif state == 0:
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
            # as they are not reversible to their original state
            if not any(i.isChecked() for i in self.answers):
                self.degree = -1
                return

            self.degree = 0
            for i, b in enumerate(self.answers):
                if b.isChecked() and i in self.valid:
                    self.degree += self.wizard().degree_per_q / len(self.valid)

    def initializePage(self):
        time = self.wizard().time
        self.lcdScreen.display("%d:%02d" % (time / 60, time % 60))
        self.number_label.setText(str(self.id) + " / " + str(QuestionPage.QUESTION_NUM))


# =======================================================


# ========== Degrees Viewer && Questions Editor =========


class DegreesViewer(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super(DegreesViewer, self).__init__(parent)
        self.resize(580, 400)
        self.setWindowTitle("Degrees Viewer")
        self.setWindowIcon(QtGui.QIcon('test.ico'))
        degree_view = QtGui.QTreeView()
        degree_view.setRootIsDecorated(False)
        degree_view.setAlternatingRowColors(True)
        degree_model = QtGui.QStandardItemModel(0, 9)
        degree_model.setHeaderData(0, QtCore.Qt.Horizontal, 'الاسم')
        degree_model.setHeaderData(1, QtCore.Qt.Horizontal, 'المدرسة')
        degree_model.setHeaderData(2, QtCore.Qt.Horizontal, 'الصف')
        degree_model.setHeaderData(3, QtCore.Qt.Horizontal, 'رقم التليفون')
        degree_model.setHeaderData(4, QtCore.Qt.Horizontal, 'الدرجة')
        degree_model.setHeaderData(5, QtCore.Qt.Horizontal, 'من')
        degree_model.setHeaderData(6, QtCore.Qt.Horizontal, 'لم يجب علي')
        degree_model.setHeaderData(7, QtCore.Qt.Horizontal, 'أجاب خطأًً')
        degree_model.setHeaderData(8, QtCore.Qt.Horizontal, 'الإمتحان')
        degree_view.setModel(degree_model)
        self.setCentralWidget(degree_view)

        try:
            files = glob.glob("degrees*.json")
            if len(files) == 0:
                QtGui.QMessageBox.warning(self, 'خطأ', "مفيش ولا ملف degrees*.json")
                return

            data, errs = parse_degrees(*files)

            if len(data) == 0 and not errs:
                QtGui.QMessageBox.warning(self, 'خطأ', "الملفات فاضية")
                return

            if len(errs) > 0:
                QtGui.QMessageBox.warning(self, 'خطأ', "الملف(ات) %s فيها خطأ لذا متفتحتش" % ", ".join(errs))

        except Exception as e:
            QtGui.QMessageBox.warning(self, e.__class__.__name__, e.message)

        else:
            for i, name in enumerate(data):
                degree_model.insertRow(i)
                degree_model.setData(degree_model.index(i, 0), name)
                for j, head in enumerate(headers, 1):
                    item = data[name][head]
                    item = ((', '.join(map(lambda x: str(int(x) + 1), item)) if item else 'N/A')
                            if isinstance(item, list) else item)
                    degree_model.setData(degree_model.index(i, j), item)

    def closeEvent(self, event):
        self.parent().parent().show()
        event.accept()


# =================== Questions Tabs ====================
class TestConfigTab(QtGui.QWidget):
    def __init__(self, test=None, parent=None):
        # type: (Test, QtGui.QWidget) -> None
        super(TestConfigTab, self).__init__(parent)

        lyt = QtGui.QGridLayout()
        self.setLayout(lyt)

        nameL = QtGui.QLabel("Test Name:")
        self.nameT = QtGui.QLineEdit()
        self.nameT.setPlaceholderText("Enter test name")
        nameL.setBuddy(self.nameT)

        descriptionL = QtGui.QLabel("Test Description:")
        self.descriptionT = QtGui.QTextEdit()
        descriptionL.setBuddy(self.descriptionT)

        timeL = QtGui.QLabel("Test Time:")
        self.timeT = QtGui.QLineEdit()
        self.timeT.setPlaceholderText("Enter time in seconds")
        self.timeT.setValidator(QtGui.QDoubleValidator())
        timeL.setBuddy(self.timeT)

        degreeL = QtGui.QLabel("Test Degree:")
        self.degreeT = QtGui.QLineEdit()
        self.degreeT.setPlaceholderText("Enter test degree")
        self.degreeT.setValidator(QtGui.QDoubleValidator())
        degreeL.setBuddy(self.degreeT)

        lyt.addWidget(nameL, 0, 0)
        lyt.addWidget(self.nameT, 0, 1)

        lyt.addWidget(descriptionL, 1, 0)
        lyt.addWidget(self.descriptionT, 1, 1, 2, 2)

        lyt.addWidget(timeL, 3, 0)
        lyt.addWidget(self.timeT, 3, 1)

        lyt.addWidget(degreeL, 4, 0)
        lyt.addWidget(self.degreeT, 4, 1)

        if test is not None:
            self.nameT.setText(test.name)
            self.descriptionT.setText(test.description)
            self.timeT.setText(str(test.time))
            self.degreeT.setText(str(test.degree))


class EditableLabel(QtGui.QLineEdit):

    def __init__(self, text, parent=None):
        super(EditableLabel, self).__init__(text, parent)

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


class QuestionTab(QtGui.QWidget):

    def __init__(self, question=None, parent=None):
        # type: (Question, QtGui.QWidget) -> None
        super(QuestionTab, self).__init__(parent)

        if question is None:
            question = Question("", None, [Answer("", False)])

        self.answers_lyt = QtGui.QVBoxLayout()
        self.question = question
        self.answs_checks = []
        self.image = QtGui.QLabel()
        self.questionT = QtGui.QTextEdit()
        self.questionT.setText(self.question.string)

        lyt = QtGui.QVBoxLayout()
        self.setLayout(lyt)

        image_and_answers = QtGui.QHBoxLayout()
        image_and_answers.addLayout(self.answers_lyt)
        image_and_answers.addWidget(self.image)

        if self.question.pic is not None:
            self.image.setPixmap(QtGui.QPixmap(self.question.pic["name"]))

        lyt.addWidget(self.questionT)
        lyt.addWidget(QtGui.QLabel("<hr>"))

        for ans in self.question.answers:
            self.add_answer(ans)

        lyt.addLayout(image_and_answers)
        lyt.addStretch(1)

        add_and_camera = QtGui.QHBoxLayout()
        add = QtGui.QPushButton()
        add.setIcon(QtGui.QIcon("add.png"))

        camera = QtGui.QPushButton()
        camera.setIcon(QtGui.QIcon("camera.png"))
        add_and_camera.addWidget(add, alignment=QtCore.Qt.AlignLeft)
        add_and_camera.addWidget(camera, alignment=QtCore.Qt.AlignRight)

        lyt.addLayout(add_and_camera)

    def add_answer(self, answer):
        answer_lyt = QtGui.QHBoxLayout()
        chk = QtGui.QCheckBox()
        if answer.valid:
            chk.toggle()

        self.answs_checks.append(chk)
        answer_lyt.addWidget(chk)
        edt = EditableLabel(answer.string)
        edt.setAlignment(QtCore.Qt.AlignAbsolute)
        answer_lyt.addWidget(edt)
        answer_lyt.setDirection(QtGui.QBoxLayout.LeftToRight)
        self.answers_lyt.addLayout(answer_lyt)


class QuestionsTabWidget(QtGui.QTabWidget):

    def __init__(self, test, parent=None):
        # type: (Test, QtGui.QWidget) -> None
        super(QuestionsTabWidget, self).__init__(parent)

        self.test = test
        self.setTabsClosable(True)
        self.setUpdatesEnabled(True)

        btn = QtGui.QToolButton()
        btn.setIcon(QtGui.QIcon("add.png"))
        self.setCornerWidget(btn)

        self.addTab(TestConfigTab(test), "Config")
        self.tabBar().tabButton(0, QtGui.QTabBar.RightSide).resize(0, 0)  # makes it not closable

        for question in test.questions:
            self.addTab(QuestionTab(question), "Q %d" % self.count())

        self.tabCloseRequested.connect(self.delete_question)

    def delete_question(self, index):
        print("HEHE")
        self.removeTab(index)


class QuestionsEditor(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super(QuestionsEditor, self).__init__(parent)
        self.setWindowTitle("Questions Editor")

        self.resize(1000, 600)

        frm = QtGui.QFrame()
        self.lyt = lyt = QtGui.QGridLayout()
        frm.setLayout(lyt)
        self.setCentralWidget(frm)

        lyt.setMargin(10)

        self.tests = QtGui.QListWidget()
        self.tests.currentItemChanged.connect(self.item_changed)
        self.tests_d = {t.name: t for t in TESTS}
        for test in TESTS:
            QtGui.QListWidgetItem(test.name, self.tests)

        leftSide = QtGui.QVBoxLayout()
        leftSide.addWidget(QtGui.QLabel("Available Tests:"))
        leftSide.addWidget(self.tests)
        btn_add_test = QtGui.QPushButton()
        btn_add_test.setIcon(QtGui.QIcon("add.png"))
        leftSide.addWidget(btn_add_test, alignment=QtCore.Qt.AlignLeft)

        lyt.addLayout(leftSide, 0, 0, 3, 1)

        lyt.addWidget(QtGui.QLabel(), 0, 2, 3, 1)

        self.questions_tabs = QuestionsTabWidget(TESTS[0])
        lyt.addWidget(self.questions_tabs, 0, 3, 3, 3)

        lyt.setColumnStretch(3, 1)
        lyt.setRowStretch(1, 1)

    def item_changed(self, now, last):
        # type: (QtGui.QListWidgetItem, QtGui.QListWidgetItem) -> None

        self.questions_tabs.hide()
        self.questions_tabs = QuestionsTabWidget(self.tests_d[str(now.text())])
        self.lyt.addWidget(self.questions_tabs, 0, 3, 3, 3)

    def closeEvent(self, event):
        if self.parent() is not None:
            self.parent().parent().show()
        event.accept()


class Auth(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super(Auth, self).__init__(parent)
        self.setWindowTitle("Auth")
        self.setFixedSize(350, 200)

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
        name = str(self.nameT.text())
        password = str(self.passwordT.text())
        fmt = "<font color=red>%s</font>"
        if (
                rot13(name) == 'un\x80{nnlsn\x81u\x86>?@'
                and rot13(password) == 'sn\x81u\x86lFFFF'
        ):
            if self.degrees.isChecked():
                widget = DegreesViewer(self)
            else:
                widget = QuestionsEditor(self)

            center_widget(widget)
            widget.show()
            self.hide()
        else:

            if not name and not password:
                self.status.setText(fmt % "Name and Password fields can't be empty")
            elif not name:
                self.status.setText(fmt % "Name field can't be empty")
            elif not password:
                self.status.setText(fmt % "Password field can't be empty")
            else:
                self.status.setText(fmt % "Invalid username or password")

            if name:
                self.passwordT.setFocus()
                self.passwordT.selectAll()
            elif password:
                self.nameT.setFocus()

    def closeEvent(self, event):
        self.parent().show()
        event.accept()


# =======================================================


# ==================== Initial Window ==================


class TestChooser(QtGui.QWidget):  # the real MainWindow is a QWidget, that's funny :")

    def __init__(self, parent=None):
        super(TestChooser, self).__init__(parent)
        self.setWindowTitle("إختر امتحانًا")
        self.resize(600, 300)
        self.cards = []
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

        for test in TESTS:
            card = TestCard(test, self)
            lyt.addWidget(card)
            self.cards.append(card)

        # focus on the first efta7 [[faksii]] button
        self.cards[0].children()[0].setFocus()

        if a > 1:
            lyt.addWidget(QtGui.QLabel("<hr>"))
            lyt.addWidget(QtGui.QLabel("النهاية"), alignment=QtCore.Qt.AlignCenter)

        login_link = QtGui.QLabel("<u><font color=blue>Open questions editor</font></u>")

        def f1(e):
            auth = Auth(self)
            center_widget(auth)
            auth.show()
            self.hide()

        login_link.mouseReleaseEvent = f1

        def f2(e):
            login_link.setText("<u><font color=purple>Open questions editor</font></u>")

        login_link.mousePressEvent = f2
        login_link.setCursor(QtCore.Qt.PointingHandCursor)

        topmost.addWidget(QtGui.QLabel("<hr>"))
        dwn = QtGui.QHBoxLayout()
        dwn.addWidget(QtGui.QLabel())
        dwn.addWidget(QtGui.QLabel("%d Test%s " % (a, 's' if a > 1 else '')), alignment=QtCore.Qt.AlignCenter)
        dwn.addWidget(login_link, alignment=QtCore.Qt.AlignRight)
        topmost.addLayout(dwn)

    def chose(self):
        test = self.cards.index(self.sender().parent())
        wizard = TestWizard(TESTS[test], self)
        center_widget(wizard)
        wizard.show()
        self.hide()


class TestCard(QtGui.QFrame):
    def __init__(self, test, parent=None):
        # type: (Test, QtGui.QWidget) -> None
        super(TestCard, self).__init__(parent)

        self.setFrameShadow(QtGui.QFrame.Sunken)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        lyt = QtGui.QGridLayout()
        lyt.addWidget(QtGui.QLabel("<b><font size=5>%s</font></b>" % test.name), 0, 0, alignment=QtCore.Qt.AlignLeft)
        lyt.addWidget(QtGui.QLabel("<hr>"), 1, 0, 1, 2)
        lyt.addWidget(QtGui.QLabel("<font size=3 color=grey>%s</font>" % (test.description or "لا يوجد وصف")),
                      1, 0, 2, 2, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("افتح", self)
        btn.setIcon(QtGui.QIcon("arrow.png"))
        btn.clicked.connect(self.parent().chose)
        lyt.addWidget(QtGui.QLabel(), 2, 0)
        text = re.sub(r'\b(\d+)\b', r'<b>\1</b>', "%s | %d درجة | <b>%d</b> سؤال"
                      % (format_secs(test.time), int(test.degree), len(test.questions)))
        lyt.addWidget(QtGui.QLabel("<font size=3 color=grey>%s</font>" % text),
                      3, 0, 1, 2, alignment=QtCore.Qt.AlignLeft)
        lyt.addWidget(btn, 4, 1, alignment=QtCore.Qt.AlignRight)

        self.setLayout(lyt)


# =======================================================


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    main = QuestionsEditor()
    center_widget(main)
    main.show()
    app.exec_()
