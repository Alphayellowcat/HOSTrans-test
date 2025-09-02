from PyQt5.QtWidgets import (QApplication, QMainWindow, QSlider, QVBoxLayout,
                             QWidget, QLabel, QPushButton, QListWidget)
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt, QTimer
import pyautogui
import time
import sys
from translator import create_translator
from utils import window_exists, contains_korean, generate_random_string
import os
from memory_utils import read_string, get_process_id, get_process_handle, scan_memory_bytes, CloseHandle
import keyboard
from qss_style import list_widget_style, main_style, title_label_style

GAME_APP_NAME = 'HeroesOfTheStorm_x64.exe'


class GlobalHotkey(QObject):
    triggered = pyqtSignal()

    def __init__(self, hotkey):
        super().__init__()
        self.hotkey = hotkey
        keyboard.add_hotkey(hotkey, self._on_trigger)

    def _on_trigger(self):
        self.triggered.emit()

    def __del__(self):
        keyboard.remove_hotkey(self.hotkey)


class HotKey(object):
    def __init__(self, key):
        self.key = key

    def run(self):
        pyautogui.hotkey(self.key)
        time.sleep(0.4)


class TransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.register_hotkey()
        self.init_timer()

        self.count = 0
        self.my_last_msg = ''
        self.address = None
        self.pid = None
        self.init_state = False
        self.candidate_address = None
        self.hided = False
        self.msg_list = []

        self.old_pos = None
        self.handle = None
        self.encoding_format = 'utf-8'
        self.get_translator()
        self.target_lan = 'kor'

    def init_ui(self):
        # 设置窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint  # 置顶
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景
        self.opacity = 40

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        layout = QVBoxLayout()
        self.main_widget.setLayout(layout)

        self.title_label = QLabel("风暴翻译")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(title_label_style)

        # 添加QListWidget
        self.list_widget = QListWidget()
        self.list_widget.setWordWrap(True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(list_widget_style)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        layout.addWidget(self.title_label)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.close_btn)
        self.setStyleSheet(main_style)
        self.resize(300, 400)
        self.setGeometry(150, 150, 300, 400)

    def init_timer(self):
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.scan_memory)
        self.scan_timer.start(1000)

        self.hide_win_timer = QTimer(self)
        self.hide_win_timer.timeout.connect(self.hide_win)
        self.hide_win_timer.start(4500)

    def get_translator(self):
        self.trans = create_translator()

    def hide_win(self):
        if self.hided:
            return
        if self.init_state:
            self.hided = True
            self.hide()

    def reshow(self):
        if not self.hided:
            return
        self.hided = False
        self.show()
        self.hide_win_timer.start(4500)

    def register_hotkey(self):
        # 中译韩文
        hotkey = GlobalHotkey("ctrl+p")
        hotkey.triggered.connect(self.auto_trans)

        hotkey = GlobalHotkey("ctrl+l")
        hotkey.triggered.connect(self.switch_lan)

        hotkey = GlobalHotkey("ctrl+1")
        hotkey.triggered.connect(self.locate_memory_region)

        hotkey = GlobalHotkey("ctrl+tab")
        hotkey.triggered.connect(self.reshow)

    def set_opacity(self, value):
        self.opacity = value
        self.setWindowOpacity(value / 100)
        self.update()  # 触发重绘

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置背景颜色和透明度
        # color = QColor(50, 50, 50, int(255 * (self.opacity / 100)))
        color = QColor(100, 100, 200, int(255 * (self.opacity / 100)))
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.NoPen))

        # 绘制圆角矩形
        rect = self.rect()
        painter.drawRoundedRect(rect, 10, 10)

    def switch_lan(self):
        if self.target_lan == 'kor':
            self.target_lan = 'en'
            lan = '英语'
        else:
            self.target_lan = 'kor'
            lan = '韩语'
        self.add_msg(f'翻译模式:中译{lan}')

    def add_msg(self, msg):
        self.list_widget.addItem(msg)
        if self.list_widget.count() > 10:
            self.list_widget.takeItem(0)
        self.list_widget.scrollToBottom()

    def send_random_chat_msg(self):
        enter = HotKey('enter')
        paste = HotKey(('ctrl', 'v'))
        random_chat_msg = generate_random_string(12)
        enter.run()
        for char in random_chat_msg:
            hk = HotKey(char)
            hk.run()
        # paste.run()
        enter.run()
        time.sleep(1)
        return random_chat_msg

    def get_process_handle(self):
        if self.pid is None:
            self.pid = get_process_id(GAME_APP_NAME)
        if not self.handle:
            self.handle = get_process_handle(self.pid)
        self.add_msg('PID:{} Handle:{}'.format(self.pid, self.handle))

    def locate_memory_region(self):
        self.get_process_handle()
        encoding_formats = ['utf-8', 'utf-16le', 'utf-16']
        self.add_msg('初始化中，不要操作键鼠')
        for encoding_format in encoding_formats:
            candidate_address_list = []
            for _ in range(3):
                random_chat_msg = self.send_random_chat_msg()

                candidate_address = scan_memory_bytes(self.handle,
                                                      random_chat_msg.encode(encoding=encoding_format))  # 粗定位
                candidate_address_list.append(candidate_address)
            candidate_address_list = [set(v) for v in candidate_address_list]
            candidate_address = candidate_address_list[0] & candidate_address_list[1] & candidate_address_list[2]
            candidate_address = list(candidate_address)
            if len(candidate_address) == 1:
                self.address = candidate_address[0]
                self.encoding_format = encoding_format
                break
        if self.address is not None:
            self.hide_win_timer.start(4500)
            self.init_state = True
            self.add_msg('初始化成功, 监听地址{}'.format(hex(self.address)))
        else:
            self.add_msg('初始化失败，请尝试重启游戏和插件')

    def auto_trans(self):
        if not window_exists("《风暴英雄》"):
            return
        self.hide_win_timer.stop()
        select_all = HotKey(('ctrl', 'a'))
        copy = HotKey(('ctrl', 'c'))
        paste = HotKey(('ctrl', 'v'))
        for _ in range(2):
            select_all.run()
            time.sleep(0.01)
            copy.run()
            time.sleep(0.01)
        clipboard = QApplication.clipboard()
        chinese_text = clipboard.text()
        if not chinese_text:
            return
        foreign_text = self.trans.trans(chinese_text, toLang=self.target_lan, fromLang='zh')
        clipboard.setText(foreign_text)
        self.my_last_msg = foreign_text
        for _ in range(2):
            select_all.run()
            paste.run()
            time.sleep(0.01)

    def scan_memory(self):
        if not window_exists("《风暴英雄》"):
            self.add_msg('游戏未启动')
            self.reshow()
            return
        if not self.init_state:
            return
        text = read_string(self.handle, self.address, 200, self.encoding_format)
        if text is None:
            return
        sys_msgs = ['综合 한국어', '<c val="3184FF">[团队]:</c>', '浏览战利', '浏览收藏', '菜单']
        for sys_msg in sys_msgs:
            if sys_msg in text:
                return
        if contains_korean(text) and text != self.my_last_msg:
            if text in self.msg_list:
                return
            ch_text = self.trans.trans(text, toLang='zh')
            if len(text) == 0:
                return
            if '翻译失败' in ch_text:
                return
            # if text != self.my_last_msg:
            if True:
                self.add_msg(text)
                self.add_msg(ch_text)
                self.reshow()
                self.hide_win_timer.start(4500)  # 重置隐藏窗体倒计时
                self.msg_list.append(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = None

    def closeEvent(self, a0):
        if self.handle is not None:
            CloseHandle(self.handle)
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentWindow()
    window.show()
    sys.exit(app.exec_())
