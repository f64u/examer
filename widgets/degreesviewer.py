from PyQt4 import QtCore, QtGui
from utils.vals import headers
from data import DEGREES


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
#         # try:
#         #     files = glob.glob(os.path.join(DATA_PATH, "degrees*.enc"))
#         #     if len(files) == 0:
#         #         QtGui.QMessageBox.warning(self, 'خطأ', "مفيش ولا ملف degrees*.enc")
#         #         return
#         #
#         #     data, errs = parse_degrees(*files, encrypted=True)
#         #
#         #     if len(data) == 0 and not errs:
#         #         QtGui.QMessageBox.warning(self, 'خطأ', "الملفات فاضية")
#         #         return
#         #
#         #     if len(errs) > 0:
#         #         QtGui.QMessageBox.warning(self, 'خطأ', "الملف(ات) %s فيها خطأ لذا متفتحتش" % ", ".join(errs))
#         #
#         # except Exception as e:
#         #     QtGui.QMessageBox.warning(self, e.__class__.__name__, str(e))
#         #
#         # else:
#
#         data = parse_degrees(res("degrees.enc", "state"), encrypted=True)
#         for i, degree in enumerate(data):
#             degree_model.insertRow(i)
#             degree_model.setData(degree_model.index(i, 0), degree.name)
#             for j, header in enumerate(headers, 1):
#                 item = getattr(degree, header)
#                 item = ((', '.join(map(lambda x: str(int(x) + 1), item)) if item else 'N/A')
#                         if isinstance(item, list) else item)
#                 degree_model.setData(degree_model.index(i, j), item)
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

        frame = QtGui.QFrame()
        lyt = QtGui.QVBoxLayout()
        frame.setLayout(lyt)
        self.setCentralWidget(frame)

        inner_lyt = QtGui.QHBoxLayout()
        inner_lyt.addWidget(QtGui.QLabel("Available Tests: "))
        tests_combo = QtGui.QComboBox()
        tests_combo.addItems([degree.test for degree in DEGREES])
        inner_lyt.addWidget(tests_combo)
        inner_lyt.addStretch(1)

        lyt.addLayout(inner_lyt)
        lyt.addSpacing(20)

        degrees_widget = QtGui.QTableWidget(len(DEGREES), len(headers))
        degrees_widget.setHorizontalHeaderLabels(headers)
        degrees_widget.horizontalHeader().setResizeMode(QtGui.QHeaderView.Interactive)
        degrees_widget.horizontalHeader().setStretchLastSection(True)

        degrees_widget.setAlternatingRowColors(True)
        degrees_widget.setSortingEnabled(True)
        lyt.addWidget(degrees_widget)

        for i, degree in enumerate(DEGREES):
            for j, header in enumerate(headers):
                item = getattr(degree, header)
                item = ((', '.join(map(lambda x: str(int(x) + 1), item)) if item else 'N/A')
                        if isinstance(item, list) else str(item))
                item = QtGui.QTableWidgetItem(item)
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                degrees_widget.setItem(i, j, item)


