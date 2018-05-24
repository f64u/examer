import copy
import re
from typing import List

from PyQt4 import QtCore, QtGui
from cryptography.fernet import InvalidToken

from data import TESTS
from utils.helpers import Test, res, StudentDegree
from utils.parsers import dump_degrees, parse_degrees
from utils.vals import headers, GRADES


class DegreesTable(QtGui.QTableWidget):

    def __init__(self, test: Test, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)
        self.test = test

        self.bar_headers = headers[:-1]  # no need for `test` now
        self.setColumnCount(len(self.bar_headers))
        self.setHorizontalHeaderLabels(self.bar_headers)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        self.cellChanged.connect(self.cell_changed)

        for degree in self.test.student_degrees:
            self.add_degree(degree, from_init=True)

    def add_degree(self, degree: StudentDegree, from_init=False):

        if degree.test != self.test.name:
            raise ValueError("{} is not of the same test.".format(degree))

        if not from_init:
            if degree in self.test.student_degrees:
                return
            self.test.student_degrees.append(degree)

        row_count = self.rowCount()
        self.insertRow(row_count)

        for i, header in enumerate(self.bar_headers):
            item = getattr(degree, header)
            item = ((', '.join(map(lambda x: str(int(x) + 1), item)) if item else 'N/A')
                    if isinstance(item, list) else str(item))

            if header == "grade":
                combo = QtGui.QComboBox()
                combo.addItems(GRADES)
                combo.setCurrentIndex(GRADES.index(item))
                self.setCellWidget(row_count, i, combo)
            else:
                item = QtGui.QTableWidgetItem(item)
                if header in ("degree", "out_of", "left", "failed_at"):
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.setItem(row_count, i, item)

    def delete_row(self, row: int):
        if QtGui.QMessageBox.question(self, "Deleting Row {}".format(row + 1),
                                      "Are you sure you want to delete row {row}?"
                                      " This <font color=red><b>cannot</b></font>"
                                      " be <font color=red><b>undone</b></font>.".format(row=row + 1),
                                      QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
            self.removeRow(row)

    def cell_changed(self, row, column):
        item = self.item(row, column)
        text = item.text()
        if column == 0:
            if not re.match("^\w{3,}\s\w{3,}$", text):
                QtGui.QMessageBox.warning(self, "Invalid Name", "{!r} is not valid name, it should contain"
                                                                " the first name and the last name separated"
                                                                " by a space.".format(text))
                self.openPersistentEditor(item)
            else:
                self.closePersistentEditor(item)
        elif column == 3:
            if not re.match("^(\+2)?01[0125]\d{8}$", text):
                QtGui.QMessageBox.warning(self, "Invalid Phone Number", "{!r} is not a valid phone number,"
                                                                        " it should be 11 numbers started with '01'"
                                                                        " preceded by an optional '+2'".format(text))
                self.openPersistentEditor(item)
            else:
                if not text.startswith("+2"):
                    item.setText("+2" + text)
                self.closePersistentEditor(item)

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
            degree = {"test": self.test.name}
            for j, header in enumerate(self.bar_headers):
                if header == "grade":  # a combobox, not an item
                    degree["grade"] = self.cellWidget(i, j).currentText()
                elif header in ("failed_at", "left"):  # should be converted into a list
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


class DegreesWidget(QtGui.QWidget):
    def __init__(self, test: Test, parent: QtGui.QWidget = None) -> None:
        super().__init__(parent)
        self.test = test
        self.table = None

        lyt = QtGui.QVBoxLayout()
        self.setLayout(lyt)

        if not self.test.student_degrees:
            self.lbl = QtGui.QLabel("<font size=5>No student has done this test yet.</font>")
            lyt.addWidget(self.lbl, 1, alignment=QtCore.Qt.AlignCenter)
        else:
            self.table = DegreesTable(test)
            lyt.addWidget(self.table)

    def add_degree(self, degree: StudentDegree):
        if degree.test != self.test.name:
            raise ValueError("{} is not of the same test.".format(degree))
        if degree not in self.test.student_degrees:
            self.test.student_degrees.append(degree)
        else:
            return

        if self.table is None:
            self.table = DegreesTable(self.test)
        else:
            self.table.add_degree(degree)

    @property
    def degrees(self) -> List[StudentDegree]:
        return [] if self.table is None else self.table.degrees

    @property
    def edited(self) -> bool:
        return False if self.table is None else self.table.edited


class DegreesViewer(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(900, 580)
        self.setWindowTitle("Degrees Viewer")

        open_action = QtGui.QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open)
        quit_action = QtGui.QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        self.parent_window = None

        sts_bar = QtGui.QStatusBar()
        sts_bar.setStyleSheet("QStatusBar { background-color: #ccc; border-top: 1.5px solid grey } ")
        self.sts_bar_lbl = QtGui.QLabel("Ready.")
        sts_bar.addWidget(self.sts_bar_lbl)
        self.setStatusBar(sts_bar)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.save)

        frame = QtGui.QFrame()
        lyt = QtGui.QVBoxLayout()
        frame.setLayout(lyt)
        self.setCentralWidget(frame)

        self.degrees_widget = QtGui.QStackedWidget()
        for test in TESTS:
            widget = DegreesWidget(copy.deepcopy(test))
            self.degrees_widget.addWidget(widget)

        inner_lyt = QtGui.QHBoxLayout()
        inner_lyt.addWidget(QtGui.QLabel("Available Tests: "))
        self.tests_combo = QtGui.QComboBox()
        self.tests_combo.currentIndexChanged.connect(lambda i: self.degrees_widget.setCurrentIndex(i))
        self.tests_combo.addItems([test.name for test in TESTS])
        inner_lyt.addWidget(self.tests_combo)
        inner_lyt.addStretch(1)
        save_btn = QtGui.QPushButton(QtGui.QIcon(res("save.png", "icon")), "Save")
        save_btn.clicked.connect(self.save)
        inner_lyt.addWidget(save_btn)

        lyt.addLayout(inner_lyt)
        lyt.addSpacing(20)

        lyt.addWidget(self.degrees_widget)

    def add_degree(self, degree: StudentDegree):
        names = self.tests_names
        if degree.test not in names:
            self.tests_combo.addItem(degree.test)
            self.degrees_widget.addWidget(DegreesWidget(Test(-1, degree.test, "", -1, [], -1, [degree])))
        else:
            self.degrees_widget.widget(names.index(degree.test)).add_degree(degree)

    def save(self):
        self.sts_bar_lbl.setText("Saved Degrees.")
        dump_degrees(self.degrees, res("degrees.enc", "state"), encrypt=True)
        QtCore.QTimer.singleShot(3000, lambda: self.sts_bar_lbl.setText("Ready."))

    def open(self):
        file, _ = QtGui.QFileDialog.getOpenFileNameAndFilter(self, filter="Degrees File (degrees.enc degrees.json)")
        try:
            degrees = parse_degrees(file, file.endswith(".enc"))
        except (ValueError, InvalidToken):
            QtGui.QMessageBox.warning(self, "Error parsing degrees", "{} is not a valid degrees file.".format(file))
            return
        except Exception as e:
            QtGui.QMessageBox.warning(self, "Error parsing degrees",
                                      "Unknown error happened parsing the degrees file."
                                      " Error signature {}{!s}".format(e.__class__.__name__, e))
            return
        else:
            if not degrees:
                QtGui.QMessageBox.warning(self, "Error parsing degrees", "{} is empty.".format(file))
                return

        self.sts_bar_lbl.setText("Added degrees.")
        QtCore.QTimer.singleShot(3000, lambda: self.sts_bar_lbl.setText("Ready."))
        for degree in degrees:
            self.add_degree(degree)

    def closeEvent(self, e: QtGui.QCloseEvent):
        if self.edited:
            result = QtGui.QMessageBox.question(self, "Are you sure you want to exit?",
                                                "You have some unsaved changes. Do you want to save them?",
                                                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
            if result == QtGui.QMessageBox.Yes:
                self.save()
            elif result == QtGui.QMessageBox.No:
                pass
            else:
                e.ignore()
                return

        if self.parent_window is not None:
            self.parent_window.show()
        e.accept()

    @property
    def widgets(self) -> List[DegreesWidget]:
        return [self.degrees_widget.widget(i) for i in range(self.degrees_widget.count())]

    @property
    def degrees(self):
        final_degrees = []
        for table in self.widgets:
            final_degrees.extend(table.degrees)
        return final_degrees

    @property
    def edited(self) -> bool:
        return any(wid.edited for wid in self.widgets)

    @property
    def tests_names(self) -> List[str]:
        return [self.tests_combo.itemText(i) for i in range(self.tests_combo.count())]
