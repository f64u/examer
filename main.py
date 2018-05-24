# -*- coding: utf-8 -*-

"""
:author: Fady Adel (2masadel at gmail dot com)
:link: https://bitbucket.org/faddyy/examer
"""

import hashlib
import sys

from PyQt4 import QtGui, QtCore
from typing import List

from data import TESTS
from utils.helpers import (
    res, center_widget,
    _init, _defer
)
from widgets.degreesviewer import DegreesViewer
from widgets.editor import TestsEditor
from widgets.innerwidgets import TestCard
from widgets.tester import TestWizard

# it's just used to make the garbage collector doesn't delete the window reference
CURRENT_ACTIVE = [None]  # type: List[QtGui.QWidget]


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
                widget = TestsEditor()
            CURRENT_ACTIVE[0] = widget
            widget.parent_window = self.parent()
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


class TestChooser(QtGui.QWidget):  # the real MainWindow is a QWidget, that's funny :")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إختر امتحانًا")
        self.setWindowIcon(QtGui.QIcon(res("test.ico", "icon")))
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

        def f(_):
            auth = Auth(parent=self)
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


def main():
    _init()
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName("Examer")
    app.setApplicationVersion("0.1")
    app.setWindowIcon(QtGui.QIcon(res("test.ico", "icon")))
    main_widget = DegreesViewer()
    center_widget(main_widget)
    main_widget.show()
    app.exec_()
    del main_widget
    del app
    _defer()


if __name__ == '__main__':
    main()
