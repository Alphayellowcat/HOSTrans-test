from PyQt5.QtWidgets import (QApplication, QMainWindow, QSlider, QVBoxLayout,
                             QWidget, QLabel, QPushButton, QListWidget)
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt, QTimer
import pyautogui
import time
import sys
from translator import BaiduTranslator
from utils import window_exists, contains_korean
import os
from memory_utils import read_string, get_process_id, get_process_handle, scan_memory_bytes, CloseHandle
import keyboard
import random
import string
from qss_style import list_widget_style, main_style, title_label_style

GAME_APP_NAME = 'HeroesOfTheStorm_x64.exe'


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for i in range(length))
    return random_string


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
        time.sleep(0.01)


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
        if os.path.exists('baiduAPI.txt'):
            with open('baiduAPI.txt', 'r') as f:
                lines = f.readlines()
                lines = [l.replace('\n', '') for l in lines]
                appid, secretkey = lines[:2]
        self.trans = BaiduTranslator(appid,
                                     secretkey)

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

    def add_msg(self, msg):
        self.list_widget.addItem(msg)
        if self.list_widget.count() > 10:
            self.list_widget.takeItem(0)
        self.list_widget.scrollToBottom()

    def send_random_chat_msg(self):
        enter = HotKey('enter')
        paste = HotKey(('ctrl', 'v'))
        random_chat_msg = generate_random_string(10)
        clipboard = QApplication.clipboard()
        clipboard.setText(random_chat_msg)
        enter.run()
        paste.run()
        enter.run()
        time.sleep(0.01)
        return random_chat_msg

    def get_process_handle(self):
        if self.pid is None:
            self.pid = get_process_id(GAME_APP_NAME)
        if not self.handle:
            self.handle = get_process_handle(self.pid)
        self.add_msg('PID:{} Handle:{}'.format(self.pid, self.handle))

    def locate_memory_region(self):
        self.get_process_handle()
        count = 1

        while True:
            if count > 3:
                self.encoding_format = 'utf-16'
            if count > 6:
                self.add_msg('六次初始化失败，请尝试重启游戏和插件'.format(count))
                break
            ok = False
            self.add_msg('第{}次尝试初始化，请不要操作键鼠'.format(count))
            QApplication.processEvents()
            random_chat_msg = self.send_random_chat_msg()

            candidate_address = scan_memory_bytes(self.handle, random_chat_msg.encode(encoding=self.encoding_format))  # 粗定位
            if not candidate_address:
                self.add_msg('第{}次初始化失败，将再次尝试'.format(count))
                count += 1
                continue
            self.add_msg('粗定位成功')
            QApplication.processEvents()
            while True:
                if ok:
                    break
                new_candidate_address = []
                for address in candidate_address:
                    random_chat_msg = self.send_random_chat_msg()
                    try:
                        data = read_string(self.handle, address, 30, self.encoding_format)
                        if data is None:
                            continue
                        if random_chat_msg in data:
                            new_candidate_address.append(address)
                    except Exception as e:
                        continue
                if len(new_candidate_address) > 1:  # 多个相关地址，需要继续排除
                    candidate_address = new_candidate_address
                    self.add_msg('多个相关地址，继续排除')
                    QApplication.processEvents()
                    continue
                elif len(new_candidate_address) == 1:  # 找到唯一地址
                    ok = True
                    self.address = new_candidate_address[0]
                    break
                else:  # 找不到任何相关地址， 重新初定位
                    self.add_msg('第{}次初始化失败，将再次尝试'.format(count))
                    QApplication.processEvents()
                    count += 1
                    break

            if ok:
                self.hide_win_timer.start(4500)
                self.init_state = True
                self.add_msg('初始化成功, 监听地址{}'.format(hex(self.address)))
                break
            time.sleep(0.1)

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
        korean_text = self.trans.trans(chinese_text, toLang='kor', fromLang='zh')
        clipboard.setText(korean_text)
        self.my_last_msg = korean_text
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
