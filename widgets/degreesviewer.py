import functools
from typing import List

from PyQt4 import QtCore, QtGui

from utils.helpers import Test, res, StudentDegree, ReasonFlag
from utils.vals import headers
from widgets.innerwidgets import NameItemDelegate, PhoneItemDelegate, GradeItemDelegate, SchoolItemDelegate


class DegreesTable(QtGui.QTableWidget):
    class PreserveFocusReason(ReasonFlag):
        NONE = ""
        INVALID_NAME = "Invalid name"
        INVALID_SCHOOL = "Invalid school name"
        INVALID_PHONE = "Invalid phone number"

    def __init__(self, test: Test, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)
        self.test = test
        self.want_focus_reasons = DegreesTable.PreserveFocusReason.NONE

        self.bar_headers = headers[:-1]  # no need for `test` now
        self.setColumnCount(len(self.bar_headers))
        self.setHorizontalHeaderLabels(self.bar_headers)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.Interactive)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        def f(col: int, row: int, acceptable: bool):
            if col == self.bar_headers.index("name"):
                self._check_reason(DegreesTable.PreserveFocusReason.INVALID_NAME, not acceptable)
            elif col == self.bar_headers.index("school"):
                self._check_reason(DegreesTable.PreserveFocusReason.INVALID_SCHOOL, not acceptable)
            elif col == self.bar_headers.index("phone"):
                self._check_reason(DegreesTable.PreserveFocusReason.INVALID_PHONE, not acceptable)

            if not acceptable:
                # don't (yet) know why but it works
                QtCore.QTimer.singleShot(0, lambda: self.editItem(self.item(row, col)))

        name_delegate = NameItemDelegate(self)
        name_delegate.acceptableInputChanged.connect(functools.partial(f, self.bar_headers.index("name")))
        self.setItemDelegateForColumn(self.bar_headers.index("name"), name_delegate)
        school_delegate = SchoolItemDelegate(self)
        school_delegate.acceptableInputChanged.connect(functools.partial(f, self.bar_headers.index("school")))
        self.setItemDelegateForColumn(self.bar_headers.index("school"), school_delegate)
        self.setItemDelegateForColumn(self.bar_headers.index("grade"), GradeItemDelegate(self))
        phone_delegate = PhoneItemDelegate(self)
        phone_delegate.acceptableInputChanged.connect(functools.partial(f, self.bar_headers.index("phone")))
        self.setItemDelegateForColumn(self.bar_headers.index("phone"), phone_delegate)

        for degree in self.test.student_degrees:
            self.add_degree(degree, from_init=True)

        self.resizeColumnsToContents()

    def add_degree(self, degree: StudentDegree, from_init=False):

        if not from_init:
            if degree in self.test.student_degrees:
                return
            self.test.student_degrees.append(degree)

        row = self.rowCount()
        self.insertRow(row)

        for i, header in enumerate(self.bar_headers):
            item = getattr(degree, header)
            item = ((', '.join(map(lambda x: str(int(x) + 1), item)) if item else 'N/A')
                    if isinstance(item, list) else str(item))

            item = QtGui.QTableWidgetItem(item)
            if header in ("degree", "out_of", "left", "failed_at"):
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.setItem(row, i, item)

        if not from_init:
            self.resizeColumnsToContents()

    def delete_row(self, row: int):
        if QtGui.QMessageBox.question(self, "Deleting Row {}".format(row + 1),
                                      "Are you sure you want to delete row {row}?"
                                      " This <font color=red><b>cannot</b></font>"
                                      " be <font color=red><b>undone</b></font>.".format(row=row + 1),
                                      QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            self.removeRow(row)

        if self.rowCount() == 0:
            self.emptied.emit()

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
            self.updateStatus.emit("<font color=red>{}</font>".format("<br>".join(self.want_focus_reasons.split(";"))))

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        row = self.rowAt(event.pos().y())
        if row == -1:
            return
        menu = QtGui.QMenu()
        delete = menu.addAction("Delete")
        delete.setIcon(QtGui.QIcon(res("halt.png", "icon")))
        action = menu.exec_(QtGui.QCursor.pos())

        if action == delete:
            self.delete_row(row)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if e.key() == QtCore.Qt.Key_Delete:
            self.delete_row(self.currentRow())

    @property
    def degrees(self) -> List[StudentDegree]:
        degrees = []
        for i in range(self.rowCount()):
            degree = {}
            for j, header in enumerate(self.bar_headers):
                if header in ("failed_at", "left"):  # should be converted into a list
                    text = self.item(i, j).text()
                    values = list(map(lambda v: int(v) - 1, text.split(", "))) if text != 'N/A' else []
                    degree[header] = values
                elif header in ("degree", "out_of"):
                    degree[header] = float(self.item(i, j).text())
                else:
                    degree[header] = self.item(i, j).text()
            degree = StudentDegree(**degree)
            degrees.append(degree)
        return degrees

    @property
    def edited(self) -> bool:
        return self.degrees != self.test.student_degrees

    wantFocusChanged = QtCore.pyqtSignal(PreserveFocusReason, name="wantFocusChanged")
    updateStatus = QtCore.pyqtSignal(str, name="updateStatus")
    emptied = QtCore.pyqtSignal(name="emptied")


class DegreesWidget(QtGui.QWidget):
    def __init__(self, test: Test, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)
        self.test = test
        self.table = None
        self.lbl = QtGui.QLabel("<font size=5>No student has done this test yet.</font>")
        self.status = QtGui.QLabel()

        self.lyt = lyt = QtGui.QVBoxLayout()
        self.setLayout(lyt)

        if not self.test.student_degrees:
            lyt.addWidget(self.lbl, 1, alignment=QtCore.Qt.AlignCenter)
        else:
            self.table = DegreesTable(test)
            self.table.wantFocusChanged.connect(self.wantFocusChanged.emit)
            self.table.emptied.connect(lambda: self.replace(to_table=False))
            self.table.updateStatus.connect(self.status.setText)
            lyt.addWidget(self.table)

        lyt.addWidget(self.status)

    def add_degree(self, degree: StudentDegree):
        if degree in self.test.student_degrees:
            return

        self.test.student_degrees.append(degree)
        if self.table is None:
            self.replace()

    def replace(self, to_table=True):
        if to_table:
            if self.lyt.indexOf(self.lbl) != -1:
                self.lyt.removeWidget(self.lbl)

            self.table = DegreesTable(self.test)
            self.table.wantFocusChanged.connect(lambda r: self.wantFocusChanged.emit())
            self.table.emptied.connect(lambda: self.replace(to_table=False))
            self.table.updateStatus.connect(self.status.setText)
            self.lyt.addWidget(self.table)
        else:
            if self.table is not None:
                self.table.deleteLater()

            self.table = None
            self.lyt.addWidget(self.lbl, 1, alignment=QtCore.Qt.AlignCenter)

    @property
    def want_focus_reasons(self) -> DegreesTable.PreserveFocusReason:
        if self.table is None:
            return DegreesTable.PreserveFocusReason.NONE
        return self.table.want_focus_reasons

    @property
    def degrees(self) -> List[StudentDegree]:
        return [] if self.table is None else self.table.degrees

    @property
    def edited(self) -> bool:
        return False if self.table is None else self.table.edited

    wantFocusChanged = QtCore.pyqtSignal(DegreesTable.PreserveFocusReason, name="wantFocusChanged")
