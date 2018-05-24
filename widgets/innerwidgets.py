import os
import re

from PyQt4 import QtGui, QtCore

from utils.helpers import (
    Test, Answer,
    res, format_secs,
)


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
        self.close_btn = IconButton(QtGui.QPixmap(res("cancel_red.png", "icon")), -1)
        self.close_btn.hide()
        self.close_btn.setToolTip("Remove the Image")
        self.close_btn.clicked.connect(self.hideImage)
        self.add_btn = IconButton(QtGui.QPixmap(res("plus_green.png", "icon")), -1)
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

        self.add_pixmap = QtGui.QPixmap(res("plus_green.png", "icon"))
        self.remove_pixmap = QtGui.QPixmap(res("cancel_red.png", "icon"))

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

    @property
    def text(self):
        return self.edt.text()

    @property
    def valid(self):
        return self.chk.isChecked()

    isEmpty = QtCore.pyqtSignal(int, name="isEmpty")
    filled = QtCore.pyqtSignal(int, name="filled")
    addRequest = QtCore.pyqtSignal(int, name="addRequest")
    deleteRequest = QtCore.pyqtSignal(int, name="deleteRequest")
    validityChanged = QtCore.pyqtSignal(bool, int, name="validityChanged")


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
        self.description = QtGui.QLabel(description)
        lyt.addWidget(self.description, 1)


class TestCard(QtGui.QFrame):
    def __init__(self, test: Test, index: int, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.index = index

        self.setFrameShadow(QtGui.QFrame.Sunken)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        lyt = QtGui.QGridLayout()
        lyt.addWidget(QtGui.QLabel("<b><font size=5>%s</font></b>" % test.name), 0, 0, alignment=QtCore.Qt.AlignLeft)
        lyt.addWidget(QtGui.QLabel("<hr>"), 1, 0, 1, 2)
        lyt.addWidget(
            QtGui.QLabel("<font size=3 color=grey>%s</font>" % (test.description or "<i>" "لا يوجد وصف" "</i>")),
            1, 0, 2, 2, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("افتح", self)
        btn.setIcon(QtGui.QIcon(res("arrow.png", "icon")))
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
