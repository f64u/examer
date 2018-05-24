import random

from PyQt4 import QtGui, QtCore

from utils.helpers import (
    Test, Question, StudentDegree,
    res,
)
from utils.parsers import dump_degrees, parse_degrees
from utils.vals import headers, GRADES
from widgets.innerwidgets import ColorBox


class TestWizard(QtGui.QWizard):
    degrees = []

    def __init__(self, test: Test, parent: QtGui.QWidget = None):
        super().__init__(parent)
        self.test = test
        self.question_num = len(self.test.questions)
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

        for id_, question in enumerate(self.test.questions):
            self.addPage(QuestionPage(id_ + 1, question))

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

                return msg_box.exec_() == QtGui.QMessageBox.AcceptRole

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
        print("called")
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

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("<font color=red>" 'ادخل بياناتك' "</font>")
        self.setSubTitle(" ")

        my_layout = QtGui.QGridLayout()
        my_layout.setColumnStretch(0, 1)
        my_layout.setColumnStretch(3, 1)
        my_layout.setRowStretch(0, 1)
        my_layout.setRowStretch(3, 1)

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

        self.nameedit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp("^\w{3,}\s\w{3,}$"), self.nameedit))
        self.numberedit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp("^(?:\+2)?01[0125]\d{8}"), self.numberedit))

        self.gradecombo.addItems(["<ادخل صفك>"] + GRADES)

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
        elif any(student.name == self.nameedit.text() and student.grade == self.gradecombo.currentText()
                 for student in self.wizard().test.student_degrees):
            return QtGui.QMessageBox.question(self, "خطأ في الإدخال",
                                              "لقد امتحن '{}' (بالنظر للاسم والصف) هذا الإمتحات من قبل. "
                                              "هل تريد إعادة الإمتحان (او انه شخص مختلف)؟"
                                              .format(self.nameedit.text()),
                                              QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes
        elif self.gradecombo.currentText() == "<ادخل صفك>":
            QtGui.QMessageBox.information(self, "خطأ في الصف", 'يرجي ادخال الصف')
        else:
            return True

        return False


class FinalPage(QtGui.QWizardPage):

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
        self.grey = ColorBox("grey", "لم يجب" " ({:.2f}%)")
        self.red = ColorBox("red", "أجاب خطأً" " ({:.2f}%)")
        self.green = ColorBox("green", "أجاب صوابًا" " ({:.2f}%)")
        colors_lyt.addWidget(self.grey)
        colors_lyt.addWidget(self.red)
        colors_lyt.addWidget(self.green)

        group_and_color.addWidget(details_group)
        group_and_color.addWidget(colors_group)

        lyt.insertLayout(1, group_and_color)

    def initializePage(self):
        degrees = self.wizard().degrees
        test = self.wizard().test
        name = self.field("name").title()
        school = self.field("school")
        grade = GRADES[int(self.field("grade")) - 1]
        number = self.field("number")
        sum_of_degrees = float(sum(i for i in degrees if i != -1))

        if not number.startswith("+2"):
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

        questions_n = len(test.questions)
        left_n = len(left)
        failed_at_n = len(failed_at)
        self.grey.description.setText(self.grey.description.text().format(left_n / questions_n * 100))
        self.red.description.setText(self.red.description.text().format(failed_at_n / questions_n * 100))
        self.green.description.setText(
            self.green.description.text().format((questions_n - (left_n + failed_at_n)) / questions_n * 100)
        )
        pieces = (left_n * test.degree / questions_n, failed_at_n * test.degree / questions_n, sum_of_degrees)
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

        dump_degrees(parse_degrees(res("degrees.enc", "state"), encrypted=True) + [StudentDegree(**student)],
                     res("degrees.enc", "state"), encrypt=True)


class QuestionPage(QtGui.QWizardPage):

    def __init__(self, id_: int, question: Question, parent=None):

        super().__init__(parent)
        self.id = id_
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
            self.pic.setPixmap(QtGui.QPixmap(res(question.pic)))

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
        self.number_label.setText("{} / {}".format(self.id, self.wizard().question_num))
