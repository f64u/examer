import copy
from collections import OrderedDict
from typing import List, Optional, cast, Set

from PyQt4 import QtCore, QtGui
from cryptography.fernet import InvalidToken

from data import TESTS
from utils.helpers import (
    Test, Question, Answer,
    res, tab_repr,
    ReasonFlag)
from utils.parsers import dump_tests, parse_tests
from widgets.degreesviewer import DegreesWidget, DegreesTable
from widgets.innerwidgets import QuestionImage, AnswerWidget, TabBar


class TestDetails(QtGui.QWidget):
    class PreserveFocusReason(ReasonFlag):
        NONE = ''
        INVALID_NAME = "Test name cannot be less than three characters."
        ALREADY_CHOSEN_NAME = "Test name must be unique (there's already a test with the same name)."

    def __init__(self, test: Test = None, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)
        self.s_test = test
        self.editor = self.parent().parent()  # type: TestsEditor

        lyt = QtGui.QGridLayout()
        self.want_focus_reasons = TestDetails.PreserveFocusReason.NONE
        self.setLayout(lyt)

        nameL = QtGui.QLabel("Test Name:")
        self.nameT = QtGui.QLineEdit()
        self.nameT.setPlaceholderText("Enter test name")
        nameL.setBuddy(self.nameT)
        self.nameT.textChanged.connect(self.observe_name)

        descriptionL = QtGui.QLabel("Test Description:<br><i>(Optional)</i>")
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

        if self.s_test is not None:
            self.nameT.setText(self.s_test.name)
            self.descriptionT.setPlainText(self.s_test.description)
            self.timeT.setTime(QtCore.QTime(0, 0).addSecs(self.s_test.time))
            self.degreeT.setValue(self.s_test.degree)

        self._check_reason(TestDetails.PreserveFocusReason.INVALID_NAME,
                           self.s_test is None or len(self.s_test.name) < 3)

    def observe_name(self, s: str):
        update = True
        same_name_num = len(list(filter(lambda test: test == s, self.editor.names)))
        for reason, happened in [(TestDetails.PreserveFocusReason.INVALID_NAME, len(s) < 3),
                                 (TestDetails.PreserveFocusReason.ALREADY_CHOSEN_NAME,
                                  (self.s_test is None and same_name_num > 0) or same_name_num > 1)]:
            if happened:
                update = False
            self._check_reason(reason, happened)

        if update:
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
        return Test(-1, self.nameT.text(), self.descriptionT.toPlainText(),
                    time.second() + time.minute() * 60 + time.hour() * 60 * 60,
                    [], float(self.degreeT.value()), [])

    wantFocusChanged = QtCore.pyqtSignal(PreserveFocusReason, name="wantFocusChange")
    nameChanged = QtCore.pyqtSignal(str, name="nameChanged")


class QuestionTab(QtGui.QWidget):
    class PreserveFocusReason(ReasonFlag):
        NONE = ''
        EMPTY_QUESTION = "Question cannot be empty."
        NUMBER_OF_ANSWERS = "Number of answers cannot be less than 2."
        NO_CORRECT_ANSWER = "A question cannot have no correct answers."
        ALL_ANSWERS_CORRECT = "A question's answers cannot be all correct."
        EMPTY_ANSWER = "A question's answer cannot be empty."

    def __init__(self, question: Question = None, index: int = -1, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)

        self.want_focus_reasons = QuestionTab.PreserveFocusReason.NONE
        self.answers_lyt = QtGui.QVBoxLayout()
        self.s_question = question or Question("", None, [Answer("", False)])
        self.answers = []  # type: List[AnswerWidget]
        self.deleted = False
        self.image = QuestionImage(self.s_question.pic and res(self.s_question.pic))
        self.disabled_because = set()   # type: Set[int]
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
        wrap.setObjectName("wrap")
        wrap.setStyleSheet("wrap { background-color: transparent; }")
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

        self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_QUESTION, not self.s_question.string)
        self._check_reason(QuestionTab.PreserveFocusReason.NUMBER_OF_ANSWERS, len(self.s_question.answers) < 2)
        self._check_reason(QuestionTab.PreserveFocusReason.NO_CORRECT_ANSWER,
                           not any(ans.valid for ans in self.s_question.answers))
        self._check_reason(QuestionTab.PreserveFocusReason.ALL_ANSWERS_CORRECT,
                           all(ans.valid for ans in self.s_question.answers))
        self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_ANSWER,
                           any(not ans.string for ans in self.s_question.answers))

    def add_answer(self, *, answer: Answer = None):

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
        self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_ANSWER, not answer.string)
        self._check_reason(QuestionTab.PreserveFocusReason.ALL_ANSWERS_CORRECT, answer.valid)

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
        self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_ANSWER,
                           any(not q.string for q in self.question.answers))

    def delete_answer(self, index):
        if {index} == self.disabled_because:
            self.disabled_because.clear()
            self.answers[-1 if index != len(self.answers) - 1 else -2].mod.setEnabled(True)

        self.answers_num -= 1
        answer = self.answers[index]
        if answer.valid:
            self.valid_num -= 1

        answer.deleted = True
        answer.deleteLater()

        self._check_reason(QuestionTab.PreserveFocusReason.NUMBER_OF_ANSWERS, self.answers_num < 2)
        self._check_reason(QuestionTab.PreserveFocusReason.NO_CORRECT_ANSWER, self.valid_num <= 0)
        self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_ANSWER,
                           any(not q.string for q in self.question.answers))

    def validity_changed(self, checked, _):
        if checked:
            self.valid_num += 1
        else:
            self.valid_num -= 1

        self._check_reason(QuestionTab.PreserveFocusReason.NO_CORRECT_ANSWER, self.valid_num <= 0)
        self._check_reason(QuestionTab.PreserveFocusReason.ALL_ANSWERS_CORRECT, self.valid_num == self.answers_num)

    def empty_answer(self, index):
        self.disabled_because.add(index)
        if len(self.disabled_because) == 1:
            self.answers[-1].mod.setDisabled(True)
            self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_ANSWER, True)

    def filled_answer(self, index):
        if index in self.disabled_because:
            self.disabled_because.remove(index)
        if len(self.disabled_because) == 0:
            self.answers[-1].mod.setDisabled(False)
            self._check_reason(QuestionTab.PreserveFocusReason.EMPTY_ANSWER, False)

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
    def __init__(self, question: QuestionTab, index: int, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)

        self.question = question
        self.question.deleted = True
        self._index = index

        self.link = QtGui.QLabel("<a href='#undo'>Undo Close Question {}</a>".format(self.index))
        self.link.setOpenExternalLinks(False)

        def f(_):
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


class TestTabWidget(QtGui.QTabWidget):

    def __init__(self, test: Test, item: QtGui.QListWidgetItem, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)

        self._item = item
        self.s_test = test
        self.setTabBar(TabBar())
        self.setTabsClosable(True)
        self.setUpdatesEnabled(True)
        self.setMovable(True)

        btn = QtGui.QToolButton()
        btn.setIcon(QtGui.QIcon(res("add.png", "icon")))
        btn.clicked.connect(self.add_question)
        self.setCornerWidget(btn)

        self.details = details = TestDetails(test, parent=self)
        details.wantFocusChanged.connect(lambda r: self.updateErrors.emit(self.errors))
        details.nameChanged.connect(lambda s: self.nameChanged.emit(self.index, s))
        self.addTab(details, "Details")
        self.tabBar().tabButton(0, QtGui.QTabBar.RightSide).resize(0, 0)  # makes it not closable

        self.degrees_widget = degrees_widget = DegreesWidget(copy.deepcopy(test), parent=self)

        def f(r):
            self.tabBar().setEnabled(r is DegreesTable.PreserveFocusReason.NONE)
            self.cornerWidget().setEnabled(r is DegreesTable.PreserveFocusReason.NONE)
            self.updateErrors.emit(self.errors)

        degrees_widget.wantFocusChanged.connect(f)
        self.addTab(degrees_widget, "Degrees")
        self.tabBar().tabButton(1, QtGui.QTabBar.RightSide).resize(0, 0)  # makes it not closable

        self.tabBar().tabMoved.connect(self.tab_moved)

        for question in test.questions:
            self.add_question(question=question, setfocus=False)

        self.tabCloseRequested.connect(self.delete_question)

    def delete_question(self, index):

        old_ques = self.widget(index)
        if (isinstance(old_ques, DeletedQuestion)
                and QtGui.QMessageBox.question(self, "Are you sure?",
                                               "Are you sure you want to <font color=red>force delete</font> {}?"
                                               " This cannot be "
                                               "<b><font color=red>undone</font></b>.".format(tab_repr(index)),
                                               QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes):

            self.removeTab(index)
            self._check_questions_name(*range(index, self.count()))

        elif QtGui.QMessageBox.question(self, "Are you sure?",
                                        "Are you sure you want to delete {}?".format(tab_repr(index)),
                                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            self.removeTab(index)
            del_ques = DeletedQuestion(old_ques, index, self)
            del_ques.openRequested.connect(self.open_deleted_question)
            self.insertTab(index, del_ques, tab_repr(index, deleted=True))
            self.tabBar().tabButton(index, QtGui.QTabBar.RightSide).setToolTip("Force Delete Question")
            self.setCurrentIndex(index)
            self.updateErrors.emit(self.errors)

    def add_question(self, *, question=None, setfocus=True):
        index = self.count()
        tab = QuestionTab(question, index)
        tab.wantFocusChanged.connect(lambda i, r: self.updateErrors.emit(self.errors))
        self.addTab(tab, tab_repr(self.count()))
        tab.questionT.setFocus()
        btn = self.tabBar().tabButton(index, QtGui.QTabBar.RightSide)
        btn.setToolTip("Delete Question")
        if setfocus:
            self.setCurrentIndex(index)

    def _check_questions_name(self, *locations):
        for loc in locations:
            wid = self.widget(loc)
            if isinstance(wid, (QuestionTab, DeletedQuestion)):
                if loc in (0, 1):
                    loc += 2
                self.setTabText(loc, tab_repr(loc, deleted=type(wid) is DeletedQuestion))

    def tab_moved(self, from_: int, to: int):
        if from_ in (0, 1):
            self.tabBar().moveTab(to, from_)

        self.updateErrors.emit(self.errors)
        self._check_questions_name(from_, to)

    def open_deleted_question(self, index):
        question = self.widget(index).question
        self.removeTab(index)
        self.insertTab(index, question, tab_repr(index))
        self.tabBar().tabButton(index, QtGui.QTabBar.RightSide).setToolTip("Delete Question")
        self.setCurrentIndex(index)
        self.updateErrors.emit(self.errors)

    @property
    def test(self):
        details = self.widget(0).test  # type: Test
        return Test(self.index, details.name, details.description, details.time,
                    [self.widget(i).question for i in range(1, self.count()) if
                     isinstance(self.widget(i), QuestionTab)],
                    details.degree, self.degrees_widget.degrees)

    @property
    def index(self):
        questions_editor = self.parent().parent().parent()  # type: TestsEditor
        return questions_editor.tests_list.row(self._item)

    @property
    def edited(self):
        return self.test != self.s_test

    @property
    def errors(self):
        errs = OrderedDict()
        for i in range(0, self.count()):
            widget = self.widget(i)
            if isinstance(widget, (TestDetails, QuestionTab, DegreesWidget)):
                reasons = widget.want_focus_reasons
            elif isinstance(widget, DeletedQuestion):
                reasons = QuestionTab.PreserveFocusReason.NONE  # emulate that nothing is wrong
            else:
                raise ValueError("Unknown page: {}".format(type(widget).__name__))

            if reasons not in (TestDetails.PreserveFocusReason.NONE, QuestionTab.PreserveFocusReason.NONE,
                               DegreesTable.PreserveFocusReason.NONE):
                errs[i] = reasons

        return errs

    nameChanged = QtCore.pyqtSignal(int, str, name="nameChanged")
    updateErrors = QtCore.pyqtSignal(OrderedDict, name="updateErrors")


class TestsEditor(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Tests Editor")

        self.just_deleted_a_test = False  # used in navigation (not to test that there were errors in the deleted test)
        self.old_tests = None  # type: Optional[List[Test]]

        open_action = QtGui.QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        save_action = QtGui.QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        quit_action = QtGui.QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")

        open_action.triggered.connect(self.open)
        save_action.triggered.connect(self.save)
        quit_action.triggered.connect(self.close)
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        sts_bar = QtGui.QStatusBar()
        sts_bar.setStyleSheet("QStatusBar { background-color: #ccc; border-top: 1.5px solid grey } ")
        self.sts_bar_lbl = QtGui.QLabel("Ready.")
        self.sts_bar_lbl.setOpenExternalLinks(False)
        self.sts_bar_lbl.linkActivated.connect(lambda index:
                                               self.tests_widget.currentWidget().setCurrentIndex(int(index)))
        sts_bar.addWidget(self.sts_bar_lbl)
        self.setStatusBar(sts_bar)

        self.resize(1000, 600)
        self.parent_window = None
        self._current_row = 0

        frm = QtGui.QFrame()
        self.lyt = lyt = QtGui.QGridLayout()
        frm.setLayout(lyt)
        self.setCentralWidget(frm)

        lyt.setMargin(10)

        self.save_btn = save_btn = QtGui.QPushButton(QtGui.QIcon(res("save.png", "icon")), "Save")
        save_btn.clicked.connect(self.save)
        save_btn.setToolTip("Save Tests")

        filter_edit = QtGui.QLineEdit()
        filter_edit.setPlaceholderText("Search tests...")
        filter_edit.textChanged.connect(self.update_tests_list)

        self.tests_list = QtGui.QListWidget()

        def f1(e: QtGui.QContextMenuEvent):
            selected_item = self.tests_list.itemAt(e.pos())
            if selected_item is None:
                return
            menu = QtGui.QMenu()
            delete = menu.addAction("Delete")
            delete.setIcon(QtGui.QIcon(res("halt.png", "icon")))
            action = menu.exec_(QtGui.QCursor.pos())

            if action == delete:
                self.delete_test(index=self.tests_list.row(selected_item))

        def f2(e: QtGui.QKeyEvent):
            if e.key() == QtCore.Qt.Key_Delete:
                self.delete_test()

        self.tests_list.contextMenuEvent = f1
        self.tests_list.keyPressEvent = f2
        self.tests_list.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tests_list.currentItemChanged.connect(self.item_changed)

        left_side = QtGui.QVBoxLayout()
        left_side.addWidget(filter_edit)
        left_side.addWidget(self.tests_list)
        self.btn_add_test = btn_add_test = QtGui.QPushButton()
        btn_add_test.setToolTip("Add a new test")
        btn_add_test.setIcon(QtGui.QIcon(res("add.png", "icon")))
        btn_add_test.clicked.connect(self.open_test_dialog)

        self.btn_remove_test = btn_remove_test = QtGui.QPushButton()
        btn_remove_test.setToolTip("Remove selected test")
        btn_remove_test.setIcon(QtGui.QIcon(res("minus.png", "icon")))
        btn_remove_test.clicked.connect(self.delete_test)

        buttons = QtGui.QHBoxLayout()
        buttons.addWidget(btn_add_test, alignment=QtCore.Qt.AlignLeft)
        buttons.addStretch(1)
        buttons.addWidget(btn_remove_test, alignment=QtCore.Qt.AlignRight)

        left_side.addLayout(buttons)

        lyt.addLayout(left_side, 0, 0, 3, 1)
        lyt.addItem(QtGui.QSpacerItem(10, 1), 0, 2)

        self.tests_widget = QtGui.QStackedWidget()

        for test in TESTS:
            self.add_test(test)

        if TESTS:
            self.tests_list.setCurrentItem(self.tests_list.item(0))

        lyt.addWidget(self.tests_widget, 0, 3, 2, 3)
        lyt.addWidget(save_btn, 2, 5)

        lyt.setColumnStretch(3, 1)
        lyt.setRowStretch(1, 1)

    def add_test(self, test: Test):
        item = QtGui.QListWidgetItem(test.name, self.tests_list)
        question_widget = TestTabWidget(test, item, parent=self)
        question_widget.updateErrors.connect(self.update_status_bar)
        question_widget.updateErrors.connect(lambda err: self.save_btn.setEnabled(not err))
        question_widget.nameChanged.connect(self.update_name)
        self.tests_widget.addWidget(question_widget)

    def delete_test(self, *, index=-1):
        if QtGui.QMessageBox.question(self, "Are you sure?", "Are you sure you want to delete {!r} ? This "
                                                             "<font color=red><b>cannot</b></font> be <font color=red>"
                                                             "<b>undone</b>"
                                                             "</font>.".format(self.tests_list.currentItem().text()),
                                      QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            if index == -1:
                index = self.tests_list.currentRow()
            self.just_deleted_a_test = True
            self.tests_list.takeItem(index)
            if index == self.tests_list.count():
                self._current_row -= 2
            elif index <= self.tests_list.currentRow():
                self._current_row -= 1
            self.tests_widget.removeWidget(self.tests_widget.widget(index))

    def open_test_dialog(self, _):
        cur_wid = self.tests_widget.currentWidget()
        errors = cur_wid and cur_wid.errors
        if errors:
            QtGui.QMessageBox.warning(self, "Invalid Operation", "Cannot add test while there's an error.")
            return

        q = QtGui.QDialog(self)
        q.setWindowTitle("Enter Test Details")
        q.setModal(True)
        q.resize(450, 400)
        lay = QtGui.QVBoxLayout()
        q.setLayout(lay)
        test_widg = TestDetails(parent=q)
        q.test = test_widg
        lay.addWidget(test_widg)
        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
                                         QtCore.Qt.Horizontal, q)
        buttons.button(QtGui.QDialogButtonBox.Ok).setDisabled(True)
        q.buttons = buttons
        test_widg.wantFocusChanged.connect(
            lambda r: buttons.button(QtGui.QDialogButtonBox.Ok).setDisabled(r != TestDetails.PreserveFocusReason.NONE)
        )

        def f():
            self.add_test(test_widg.test)
            q.accept()

        buttons.accepted.connect(f)
        buttons.rejected.connect(q.reject)
        lay.addWidget(buttons)
        q.show()

    def update_name(self, index: int, string: str):
        self.tests_list.item(index).setText(string)

    def item_changed(self, current: QtGui.QListWidgetItem, previous: QtGui.QListWidgetItem):

        previous_index = self.tests_list.row(previous)
        current_index = self.tests_list.row(current)

        if current_index == self._current_row:
            return

        widget = self.tests_widget.widget(previous_index)
        errs = widget.errors if widget is not None else []
        if not self.just_deleted_a_test and errs:
            locs = ", ".join(tab_repr(i) for i in errs)
            QtGui.QMessageBox.warning(self, "Cannot Change The Current Test.",
                                      "Test `{}` has some errors so you can't leave it. See the {} tab{}."
                                      .format(previous.text(), locs, 's' if len(errs) > 1 else ''))

            QtCore.QTimer.singleShot(0, lambda: self.tests_list.setCurrentRow(self._current_row))
            return
        else:
            self.just_deleted_a_test = False
            self._current_row = self.tests_list.row(current)

        self.tests_widget.setCurrentIndex(current_index)
        self.update_status_bar()

    def update_status_bar(self, errs: OrderedDict = None):
        if errs is None:
            errs = self.tests_widget.currentWidget().errors

        if errs:
            self.sts_bar_lbl.setText("Error in the {} tab{}."
                                     .format(", ".join("<a href='{}'>{}</a>".format(i, tab_repr(i)) for i in errs),
                                             's' if len(errs) > 1 else ''))
        else:
            self.sts_bar_lbl.setText("Ready.")

    def update_tests_list(self, s: str):
        for i in range(self.tests_list.count()):
            item = self.tests_list.item(i)
            item.setHidden(s not in item.text())

    def save(self) -> bool:
        errors = self.tests_widget.currentWidget().errors
        if errors:
            QtGui.QMessageBox.warning(self, "Invalid Operation", "Cannot save while there's an error.")
            return False
        else:
            self.sts_bar_lbl.setText("Saved Tests.")
            QtCore.QTimer.singleShot(3000, self.update_status_bar)

            new_tests = self.tests
            for widget, test in zip(self.widgets, new_tests):
                widget.s_test = test

            self.old_tests = TESTS[:]
            TESTS.clear()
            TESTS.extend(new_tests)

            dump_tests(new_tests, res("data.enc", "state"), encrypt=True)
            return True

    def open(self):
        file, _ = QtGui.QFileDialog.getOpenFileNameAndFilter(self, caption="Load new tests",
                                                             filter="Data file (data.enc data.json)")
        if not file:
            return

        try:
            new_tests = parse_tests(file, encrypted=file.endswith(".enc"))
        except (ValueError, InvalidToken):
            QtGui.QMessageBox.warning(self, "Error parsing tests", "{} is not a valid data file.".format(file))
            return
        except Exception as e:
            QtGui.QMessageBox.warning(self, "Error parsing tests",
                                      "Unknown error happened parsing the data file."
                                      " Error signature {}{!s}".format(e.__class__.__name__, e, e.__traceback__))
            return
        else:
            if not new_tests:
                QtGui.QMessageBox.warning(self, "Error parsing tests", "{} is empty.".format(file))
                return

        same_test = []
        same_name_different_details = []
        same_name_different_questions = []
        names = self.names
        for i, test in enumerate(new_tests, TESTS[-1].id + 1):
            test_dict = test._asdict()
            test_dict["id"] = i
            test = Test(**test_dict)

            if test.name in names:
                if test in TESTS:
                    same_test.append(test)
                    continue
                # else: not the same test, bring the similar test in name

                similar_test = None
                for t in TESTS:
                    if test.name == t.name:
                        similar_test = t
                        break
                assert similar_test is not None
                if test.questions != similar_test.questions:
                    same_name_different_questions.append(test)
                else:  # the details are different then.
                    same_name_different_details.append(test)
                continue

            self.add_test(test)

        if same_test:
            plural = len(same_test) > 1
            QtGui.QMessageBox.information(self, "Same Tests",
                                          "Test{} {} already exist{}, so they were discarded.".format(
                                              's' if plural else '', ", ".join(same_test), 's' if not plural else ''))

        for test in same_name_different_details:
            box = QtGui.QMessageBox()
            box.setIcon(QtGui.QMessageBox.Question)
            box.setWindowTitle("Same name different details")
            box.setText("There's a test with the same name {}"
                        " but different details, What do you want to do?".format(test.name))
            override = box.addButton("&Override", QtGui.QMessageBox.YesRole)
            ignore = box.addButton("&Ignore", QtGui.QMessageBox.NoRole)
            box.addButton("&Skip", QtGui.QMessageBox.RejectRole)

            result = box.exec_()

            index = names.index(test.name)
            old_test = TESTS[index]
            assert old_test.name == test.name
            if result == override:
                old_test_dict = old_test._asdict()

                for attr in ["description", "time", "degree"]:
                    old_test[attr] = getattr(test, attr)
                old_test_dict["student_degrees"].update(test.student_degrees)

                overridden_test = Test(**old_test_dict)
                TESTS[index] = overridden_test

                details_tab = self.tests_widget.widget(index).widget(0)  # type: TestDetails

                details_tab.descriptionT.setPlainText(test.description)
                details_tab.timeT.setTime(QtCore.QTime(0, 0).addSecs(test.time))
                details_tab.degreeT.setValue(test.degree)

            elif result == ignore:
                old_test.student_degrees.update(test.student_degrees)

        for test in same_name_different_questions:
            box = QtGui.QMessageBox()
            box.setIcon(QtGui.QMessageBox.Question)
            box.setWindowTitle("Same name different questions")
            box.setText("There's a test with the same name {}"
                        " but different set of questions, What do you want to do?".format(test.name))
            override = box.addButton("&Override", QtGui.QMessageBox.YesRole)
            add = box.addButton("&Add them together", QtGui.QMessageBox.NoRole)
            ignore = box.addButton("&Ignore", QtGui.QMessageBox.NoRole)
            box.addButton("&Skip", QtGui.QMessageBox.RejectRole)

            result = box.exec_()

            index = names.index(test.name)
            old_test = TESTS[index]
            assert old_test.name == test.name

            if result == override:
                self.tests_widget.widget(index).set_questions(test.questions)

        self.sts_bar_lbl.setText("Added Tests.")
        QtCore.QTimer.singleShot(3000, lambda: self.sts_bar_lbl.setText("Ready."))

    def closeEvent(self, event):

        if self.edited:
            result = QtGui.QMessageBox.question(self, "Are you sure you want to exit?",
                                                "You have some unsaved changes. Do you want to save them?",
                                                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
            if result == QtGui.QMessageBox.Yes and self.save():
                pass
            elif result == QtGui.QMessageBox.No:
                pass
            else:
                event.ignore()
                return
        if self.parent_window is not None:
            self.parent_window.show()
        event.accept()

    @property
    def edited(self) -> bool:
        return len(self.tests) != len(TESTS) or any(wid.edited for wid in self.widgets)

    @property
    def widgets(self) -> List[TestTabWidget]:
        return cast(List[TestTabWidget], [self.tests_widget.widget(i) for i in range(0, self.tests_widget.count())])

    @property
    def names(self) -> List[str]:
        return [widget.widget(0).nameT.text() for widget in self.widgets]

    @property
    def tests(self) -> List[Test]:
        return [widget.test for widget in self.widgets]
