import base64
import datetime
import os
import sys
from collections import namedtuple

import aenum
from PyQt4 import QtGui
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .vals import (
    IMAGES_PATH, DATA_PATH
)

Answer = namedtuple("Answer", "string valid")
Question = namedtuple("Question", "string pic answers")
Test = namedtuple("Test", "id name description time questions degree student_degrees")
StudentDegree = namedtuple("StudentDegree", "name phone school grade degree out_of failed_at left")


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


class ReasonFlag(str, aenum.Flag, settings=(aenum.AutoValue,)):

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


def res(name: str, kind="image") -> str:
    assert kind in ("image", "icon", "state")

    if kind == "image":
        return os.path.join(IMAGES_PATH, name)
    elif kind == "icon":
        if not getattr(sys, "frozen", False):
            return os.path.join('icos', name)
        return _rel_icon(name)
    else:
        return os.path.join(DATA_PATH, name)


def _init():
    req_files = [
        ("data.enc", "state"),
    ]
    for e in req_files:
        r = res(*e)
        if not os.path.isfile(r):
            with open(r, "w") as f:
                f.write("")


def _defer():
    if os.path.isfile("qt.conf"):
        os.remove("qt.conf")


def tab_repr(index: int, deleted=False) -> str:
    if index == 0:
        return "Details"
    if index == 1:
        return "Degrees"

    return "Q " + str(index - 1) + (" (Deleted)" if deleted else "")
