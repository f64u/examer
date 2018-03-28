# -*- coding: utf-8 -*-

from __future__ import division, print_function, unicode_literals
from typing import List, Union
from PyQt4 import QtGui, QtCore
from collections import namedtuple
import json
import random
import os.path

# ==================== Data Holders ====================
Answer = namedtuple("Answer", "string valid")
Question = namedtuple("Question", "string pic answers")
Test = namedtuple("Test", "name description questions degree")


# ==================== Util Functions ====================
def parse_tests(file_name):
    # type: (Union[str, unicode]) -> List[Test]
    with open(file_name) as f:
        tests = json.load(f)

    test_list = []
    for test in tests:
        name = test
        test = tests[test]
        description = test["description"]
        degree = test["degree"]
        questions = [Question(q["question"], q["pic"], [Answer(a, i in q["valid"]) for i, a in enumerate(q["answers"])])
                     for q in test["questions"]]

        test_list.append(Test(name, description, questions, degree))

    return test_list


TESTS = parse_tests("tests.json")


class MainWizard(QtGui.QWizard):
    degrees = []

    def __init__(self, parent=None, test_num=0):
        super(MainWizard, self).__init__(parent)
        self.test = TESTS[test_num]

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

        # ====================== The Questions (the whole thing really (:) ==========================
        # self.addPage(QuestionPage(Question(" ما ميزة شراء كمبيوتر لوحي (tablet) عن شراء كمبيوتر محمول عادي (laptop)؟",
        #                                    ("القدرة اللاسلكية", "حجم/وزن أقل", "وصول أسرع إلى الإنترنت",
        #                                     "قدرات كتابة أسرع", "سرعة معالجة أسرع",
        #                                     "إمكانية توصيل عدد أكبر من الأجهزة المرفقة"), (1,)
        #                                    )))
        #
        # self.addPage(QuestionPage(Question("ما ترقية الأجهزة المحتمل استخدامها لإضافة مزيد"
        #                                    + " من مساحة التخزين إلى هاتف ذكي حديث؟",
        #                                    ("microSD", "قرص ثابت", "CompactFlash", "محرك أقراص Flash"),
        #                                    (0,)
        #                                    )))
        #
        # self.addPage(QuestionPage(Question("ما المكون الذي يوضع داخل علبة الكمبيوتر؟",
        #                                    ("الشاشة", "الطابعة", "(RAM) ذاكرة الوصول العشوائي",
        #                                     "الثابتة USB محرك أقراص"),
        #                                    (2,)
        #                                    )))
        #
        # self.addPage(QuestionPage(Question("ما المكون المادي للكمبيوتر الذي يجب تثبيته"
        #                                    + " في كمبيوتر شخصي لتوفير الاتصال بالشبكة؟",
        #                                    ("ناقل PCI", "المنفذ التسلسلي", "واجهة الشبكة", "فتحة التوسعة"),
        #                                    (2,)
        #                                    )))
        # self.addPage(
        #     QuestionPage(Question("أي نوعين من أنظمة التشغيل يجري استخدامهما في الهواتف الذكية؟ (اختر خيارين.)",
        #                           ("iOS", "OS X", "Android", "Snow Leopard", "Windows 7"),
        #                           (0, 2)
        #                           )))
        # self.addPage(QuestionPage(Question("أي جهازين مما يلي يعدان من أجهزة الإخراج؟ (اختر خيارين.)",
        #                                    ("لوحة المفاتيح", "الشاشة", "الماوس", "الطابعة", "كاميرا الفيديو"),
        #                                    (1, 3)
        #                                    )))
        # self.addPage(QuestionPage(Question("أي إجراءين مما يلي يعدان إجراءات احتياطية عامة يجب اتباعهما"
        #                                    + " عند استخدام الأدوات اليدوية؟ (اختر خيارين.)",
        #                                    ("استخدام أدوات ذات حجم ونوع صحيحين.",
        #                                     "الحرص دومًا على حمل الأدوات ذات الأطراف"
        #                                     + " المدببة بجانبك بحيث تتجه أطرافها المدببة لأعلى.",
        #                                     "بقاء أدوات القطع حادة وفي حالة جيدة للعمل.",
        #                                     "حمل الأدوات التي تستخدمها بكثرة في جيوبك."),
        #                                    (0, 2)
        #                                    )))
        #
        # self.addPage(QuestionPage(Question("في حالة فقد جهاز محمول أو سرقته، ما الإجراءان اللذان يساعدان في"
        #                                    + " حماية المعلومات الخاصة المخزنة على هذا الجهاز؟ (اختر خيارين.)",
        #                                    ("استخدام عميل بريد إلكتروني آمن.", "تشفير وسائط التخزين.",
        #                                     "تمكين كلمة مرور للوصول إلى الجهاز.",
        #                                     "إيقاف تشغيل الجهاز حينما لا يكون قيد الاستخدام.",
        #                                     "إيقاف تشغيل الاتصال اللاسلكي حينما لا يكون قيد الاستخدام."),
        #                                    (1, 2)
        #                                    )))
        # self.addPage(PicQuestionPage("image001.png",
        #                              Question(
        #                                  "بالنظر إلى الصورة الموضحه ما العنصر الذي يشير إليه الرمز المعروض؟",
        #                                  ("مجلد عبارة عن مجموعة من المجلدات الفرعية والملفات",
        #                                   "مستند Word مخزن على القرص", "ملف قاعدة بيانات",
        #                                   "برنامج يُستخدم في التنقل عبر الملفات المخزنة على القرص"),
        #                                  (0,)
        #                              )))
        # self.addPage(QuestionPage(Question("كيف يمكن تظليل مقطع نصي في"
        #                                    + " مستند \"المفكرة\" لنسخه إلى مكان آخر داخل المستند؟",
        #                                    ("من خلال النقر فوق الرمز \"نسخ\" ثم سحب المؤشر فوق النص المراد نسخه",
        #                                     "من خلال النقر نقرًا مزدوجًا فوق الكلمات التي تريد نسخها",
        #                                     '"ونقل المؤشر إلى نهاية النص ثم النقر فوق الرمز "نسخ Windows من خلال'
        #                                     + ' نقل المؤشر إلى بداية النص المراد نسخه والضغط على مفتاح رمز',
        #                                     "من خلال النقر فوق بداية النص وسحب المؤشر إلى نهاية النص، ثم تحرير الزر"),
        #                                    (3,)
        #                                    )))
        # self.addPage(PicQuestionPage("image002.png",
        #                              Question("بالنظر إلى الصورة أدناه. لماذا يظهر الخيار تراجع باللون"
        #                                       + " الأسود، في حين تظهر العناصر الأخرى باللون الرمادي؟",
        #                                       ("تظهر الأوامر باللون الأسود، بينما تظهر عمليات التحرير باللون الرمادي",
        #                                        ".يتغير لون مجموعات عناصر القائمة إلى اللون"
        #                                        + " الأسود واللون الرمادي لكي يتم العثور عليها بسهولة أكبر",
        #                                        "لا توجد عمليات يمكن التراجع عنها، لذلك فإن هذه العملية غير متوفرة",
        #                                        "لا يوجد نص يمكن قصه أو نسخه أو لصقه أو حذفه،"
        #                                        + " لذلك فإن هذه العمليات غير متوفرة"),
        #                                       (3,)
        #                                       )))
        # self.addPage(PicQuestionPage("image003.png",
        #                              Question("بالنظر إلى الصورة أدناه. ما سبب ظهور القائمة الموضحة"
        #                                       " بالصورة على شاشة المستخدم؟",
        #                                       ("نقر المستخدم نقرًا مزدوجًا فوق أحد رموز سطح المكتب",
        #                                        "نقر المستخدم بزر الماوس الأيمن فوق أحد رموز سطح المكتب",
        #                                        ".Enter تظليل المستخدم لرمز ثم الضغط على مفتاح",
        #                                        ".Esc تظليل المستخدم لرمز ثم الضغط على مفتاح"),
        #                                       (1,)
        #                                       )))
        # self.addPage(QuestionPage(Question("اشترى طالب كمبيوترًا لوحيًا جديدًا مزودًا بإمكانية WiFi."
        #                                    + " فما المطلوب لتوصيل هذا الجهاز بالإنترنت؟",
        #                                    ("شبكة G3 أو G4", "شركة هواتف", "شبكة محلية (LAN) لاسلكية",
        #                                     "موفر خدمات هاتف محمول"),
        #                                    (2,)
        #                                    )))
        # self.addPage(QuestionPage(Question("ما الإجراء الاحتياطي الذي يجب اتخاذه قبل"
        #                                    + " إزالة أي مكون إلكتروني من نظام الكمبيوتر؟",
        #                                    ("وضع الكمبيوتر على فرش عازل",
        #                                     "التأكد من أن الكمبيوتر غير موصل بالتيار الكهربائي",
        #                                     "توصيل سلك تأريض بعلبة الكمبيوتر",
        #                                     "استخدام الأدوات المعدنية المعتمدة فقط"),
        #                                    (1,)
        #                                    )))
        # self.addPage(QuestionPage(Question("من المتوقع أن يستغرق تحديث نظام شركة بأكملها حوالي 60 ساعة عمل من فني"
        #                                    + " واحد حتى يكتمل. فكم المدة التي يستغرقها خمسة فنيين لأداء هذا"
        #                                    + " التحديث إذا عمل كل واحد منهم بنفس المقدار الزمني؟",
        #                                    ("5 ساعات", "8 ساعات", "10 ساعات", "12 ساعات"),
        #                                    (3,)
        #                                    )))
        # self.addPage(QuestionPage(Question("يقوم طالب بكتابة لغة جديدة من اختراعه باستعمال حروف لاتينية. فيما يلي بعض"
        #                                    + " الكلمات التي وضعها الطالب: " + "<br /> " + "(stalopheah تعني good day) و "
        #                                    + " (stalopjink تعني goodness) و (drahplunk تعني light house) و "
        #                                    + "(finsjink تعني happiness) و (pluckgercki تعني house fly)"
        #                                    + "<br /><br />"
        #                                    + "فما الكلمة التي يحب علي الطالب استخدامها لتعني \"daylight\"؟",
        #                                    ("jinkstalop", "stalopflins", "heahflins", "heahdrah", "drahjink", "heahgrecki"),
        #                                    (3,)
        #                                    )))
        # self.addPage(QuestionPage(Question("من خصائص ذاكرة الوصول العشوائى",
        #                                    ("لا تؤثر على سرعة اداء الحاسب", "تفقد محتوياتها عند انقطاع التيار الكهربائى",
        #                                     "لا يمكن تغيير محتوياتها", "دائمة"),
        #                                    (1,)
        #                                    )))
        # self.addPage(QuestionPage(Question("أصغر وحدة تخزين فى الحاسب الالى",
        #                                    ("Bit", "Byte", "KiloByte", "MegaByte"),
        #                                    (0,)
        #                                    )))
        # self.addPage(QuestionPage(Question("اى رقم يكمل تسلسل الأرقام : "
        #                                    + "4، 6، 9، 6، 14، 6، ...",
        #                                    ("6", "17", "19", "21"),
        #                                    (2,)
        #                                    )))
        # ===========================================================================================
        self.addPage(FinalPage())

        def f():
            self.calculate()
            d = self.degrees

            if not all(i != -1 for i in d) and not self.timeout:
                msg_box = QtGui.QMessageBox(QtGui.QMessageBox.Warning,
                                            "انتبه", 'انت لم تجب عن كل السئلة, هل تريد المتابعة؟',
                                            QtGui.QMessageBox.NoButton, self)
                msg_box.addButton("&اجل", QtGui.QMessageBox.AcceptRole)
                msg_box.addButton("&لا", QtGui.QMessageBox.RejectRole)

                if msg_box.exec_() == QtGui.QMessageBox.AcceptRole:
                    return True
                return False
            return True

        self.page(self.pageIds()[-2]).validatePage = f

        self.time = 2700  # 45 minutes
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_lcd)
        self.timeout = self.timer_started = False
        self.finished_answering = False

    def update_lcd(self):
        self.time -= 1

        if self.time >= 0:
            if isinstance(self.currentPage(), QuestionPage):
                self.currentPage().lcdScreen.display("%d:%02d" % (self.time / 60, self.time % 60))
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
        return super(MainWizard, self).nextId()

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

        p = self.currentPage()
        if isinstance(p, QuestionPage):
            p.lcdScreen.display("%d:%02d" % (self.time / 60, self.time % 60))

    def calculate(self):
        self.degrees = []
        for p in self.pageIds():
            p = self.page(p)
            if isinstance(p, QuestionPage):
                self.degrees.append(p.degree)


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

        # completer = QtGui.QCompleter()
        # self.gradeedit.setCompleter(completer)
        # model = QtGui.QStringListModel()
        # model.setStringList([
        #     "الأول الإعدادي",
        #     "الثاني الإعدادي",
        #     "الثالث الإعدادي",
        #     "الأول الثانوي",
        #     "الثاني الثانوي",
        #     "الثالث الثانوي",
        # ])
        # completer.setModel(model)

        self.gradecombo = QtGui.QComboBox()
        # self.gradecombo.setEditable(True)

        e = [self.nameedit, self.schooledit, self.numberedit, self.gradecombo]
        for i in e:
            # if isinstance(i, QtGui.QLineEdit): i.setAlignment(QtCore.Qt.AlignRight)
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

        nameL = QtGui.QLabel('&' + 'الاسم :')
        nameL.setBuddy(self.nameedit)
        schoolL = QtGui.QLabel('&' 'المدرسة :')
        schoolL.setBuddy(self.schooledit)
        gradeL = QtGui.QLabel('&' + 'الصف :')
        gradeL.setBuddy(self.gradecombo)
        numberL = QtGui.QLabel('&' + 'رقم التليفون :')
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
        test = self.wizard().test
        vm.setData(vm.index(0, 0), test.degree / len(test.questions))
        vm.setData(vm.index(0, 1), test.degree)
        vm.setData(vm.index(0, 2), sum_of_degrees)

        failed_at = [degrees.index(i, f) for f, i in enumerate(degrees) if i == 0]
        left = [degrees.index(i, f) for f, i in enumerate(degrees) if i == -1]
        user = {"school": unicode(school), "grade": unicode(grade), "number": unicode(number),
                "degree": unicode(sum_of_degrees), "outof": QuestionPage.QUESTION_NUM * QuestionPage.QUESTION_DEGREE,
                "failed_at": failed_at, "left": left, "test": TESTS[self.wizard().test_num].name}

        if not os.path.exists("data/degrees.json"):
            with open("data/degrees.json", "w") as f:
                f.write("{}")

        with open("data/degrees.json", "r") as f:
            try:
                data = json.load(f)
            except ValueError as e:
                print("error" + str(e))
                data = {}

        with open("data/degrees.json", "w") as f:
            data[unicode(name)] = user
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
        hline = QtGui.QFrame()
        hline.setFrameShape(QtGui.QFrame.HLine)
        hline.setFrameShadow(QtGui.QFrame.Sunken)
        my_layout.addWidget(hline)

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
                self.degree = 2
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
                    self.degree += 2 / len(self.valid)

    def initializePage(self):
        time = self.wizard().time
        self.lcdScreen.display("%d:%02d" % (time / 60, time % 60))
        self.number_label.setText(str(self.id) + " / " + str(QuestionPage.QUESTION_NUM))


if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)
    wizard = MainWizard()
    wizard.show()
    app.exec_()
