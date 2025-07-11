import base64
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from io import BytesIO

import requests
from PIL import Image
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QListWidget, QPushButton, QTextEdit, QVBoxLayout, \
    QLineEdit, QHBoxLayout, QMessageBox

import ddddocr

ocr = ddddocr.DdddOcr()
ca_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "captcha")
if os.path.isdir(ca_path):
    shutil.rmtree(ca_path)
os.makedirs(ca_path)

home_dir = os.path.expanduser("~")
data_folder = os.path.join(home_dir, "whiteoutRedemption")
# 确保目录存在
os.makedirs(data_folder, exist_ok=True)
data_file = os.path.join(data_folder, "data.json")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/133.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded"
}


def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"fids": [], "cdks": [], "window": {"x": 100, "y": 100, "width": 600, "height": 500}}


def save_data(fids, cdks, window_geometry):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({"fids": fids, "cdks": cdks, "window": window_geometry}, f, ensure_ascii=False, indent=4)


def generate_sign(data):
    sorted_keys = sorted(data.keys())
    query_string = '&'.join(
        f"{key}={json.dumps(data[key]) if isinstance(data[key], (dict, list)) else data[key]}" for key in sorted_keys)
    fixed_string = "Uiv#87#SPan.ECsp"
    sign_string = query_string + fixed_string
    md5_hash = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    return {'sign': md5_hash, **data}


def login_fid(headers, fid):
    timestamp_ms = int(datetime.now().timestamp() * 1000)
    data = generate_sign({"fid": fid, "time": str(timestamp_ms)})
    url_login = "https://wjdr-giftcode-api.campfiregames.cn/api/player"
    response = requests.post(url_login, headers=headers, data=data)
    return response.json() if response.status_code == 200 else {"msg": "Login Failed"}


def redeem_code(headers, fid, cdk):
    timestamp_ms = int(datetime.now().timestamp() * 1000)
    data = generate_sign(
        {"fid": fid, "cdk": cdk, "time": str(timestamp_ms),
         "captcha_code": get_captcha_code(headers, fid, timestamp_ms), })
    url_gift = "https://wjdr-giftcode-api.campfiregames.cn/api/gift_code"
    response = requests.post(url_gift, headers=headers, data=data)
    return response.json() if response.status_code == 200 else {"msg": "Request Failed"}


def get_captcha_code(headers, fid, timestamp_ms):
    data = {
        "fid": fid,
        "time": str(timestamp_ms),
        "init": 0,
    }

    data = generate_sign(data)
    # print(f"[POST]\n{data}")

    url_captcha = "https://wjdr-giftcode-api.campfiregames.cn/api/captcha"
    response = requests.post(
        url_captcha,
        headers=headers,
        data=data
    )
    # print(response.headers)
    response_data = response.json() if response.status_code == 200 else {"msg": ""}

    captcha_img_base64 = response_data['data']['img']
    # print(captcha_img)
    captcha_img_base64 = captcha_img_base64[len("data:image/jpeg;base64"):]
    captcha_img_bytes = base64.b64decode(captcha_img_base64)
    # print(len(captcha_img_bytes))
    captcha_img = Image.open(BytesIO(captcha_img_bytes))
    result = ocr.classification(captcha_img)
    captcha_img.save(os.path.join(ca_path, result + ".jpeg"))
    return result


class GiftRedeemApp(QWidget):
    def __init__(self):
        super().__init__()
        self.data = load_data()
        self.show_welcome_message()
        self.initUI()

    def show_welcome_message(self):
        msg = QMessageBox()
        msg.setWindowTitle("欢迎使用")
        msg.setText("欢迎使用《无尽冬日》礼包兑换工具！\n\n该程序由 1533区 菜狗 友情提供\n欢迎大佬们移民到1533区\n\n"
                    "📌 请确保您的网络连接正常。\n"
                    "📌 正确填写玩家 ID 与礼包码。\n"
                    "📌 兑换后请检查游戏内邮件是否到账。")
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)

        # 调整窗口大小（通过添加一个 "详细信息" 的方式撑开窗口）
        msg.setDetailedText("此工具仅供学习交流使用，禁止任何商业用途。")
        msg.exec_()

    def initUI(self):
        self.setWindowTitle("无尽冬日 - 礼包兑换")
        self.resize(self.data["window"]["width"], self.data["window"]["height"])
        self.move(self.data["window"]["x"], self.data["window"]["y"])

        self.label_fid = QLabel("玩家 ID 列表:")
        self.list_fid = QListWidget()
        for fid in self.data["fids"]:
            self.list_fid.addItem(fid)

        self.input_fid = QLineEdit()
        self.input_fid.setPlaceholderText("玩家 FID")
        self.btn_add_fid = QPushButton("添加玩家")
        self.btn_add_fid.clicked.connect(self.add_fid)
        self.btn_remove_fid = QPushButton("删除选中")
        self.btn_remove_fid.clicked.connect(self.remove_fid)

        fid_layout = QHBoxLayout()
        fid_layout.addWidget(self.input_fid)
        fid_layout.addWidget(self.btn_add_fid)
        fid_layout.addWidget(self.btn_remove_fid)

        self.label_cdk = QLabel("礼包码列表:")
        self.list_cdk = QListWidget()
        for cdk in self.data["cdks"]:
            self.list_cdk.addItem(cdk)

        self.input_cdk = QLineEdit()
        self.input_cdk.setPlaceholderText("礼包码")
        self.btn_add_cdk = QPushButton("添加礼包码")
        self.btn_add_cdk.clicked.connect(self.add_cdk)
        self.btn_remove_cdk = QPushButton("删除选中")
        self.btn_remove_cdk.clicked.connect(self.remove_cdk)

        cdk_layout = QHBoxLayout()
        cdk_layout.addWidget(self.input_cdk)
        cdk_layout.addWidget(self.btn_add_cdk)
        cdk_layout.addWidget(self.btn_remove_cdk)

        self.btn_redeem = QPushButton("兑换")
        self.btn_redeem.clicked.connect(self.start_redeem)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.label_fid)
        layout.addWidget(self.list_fid)
        layout.addLayout(fid_layout)
        layout.addWidget(self.label_cdk)
        layout.addWidget(self.list_cdk)
        layout.addLayout(cdk_layout)
        layout.addWidget(self.btn_redeem)
        layout.addWidget(self.result_text)

        self.setLayout(layout)

    def closeEvent(self, event):
        window_geometry = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height()
        }
        save_data(self.data["fids"], self.data["cdks"], window_geometry)
        event.accept()

    def add_fid(self):
        fid = self.input_fid.text().strip()
        if fid:
            self.btn_add_fid.setEnabled(False)  # 禁用兑换按钮
            self.login_thread = LoginThread(fid)
            self.login_thread.response_signal.connect(self.add_fid_cb)
            self.login_thread.start()
            self.input_fid.clear()

    def add_fid_cb(self, login_response):
        fid = login_response["fid"]
        if login_response.get("msg") != "success":
            self.result_text.append(f"[登录失败] 玩家 {fid}: {login_response}")
        else:
            nick_name = login_response['data']['nickname']
            entry = f"{nick_name} ({fid})"
            self.result_text.append(f"[登录成功][{entry}]")
            self.list_fid.addItem(entry)
            self.data["fids"].append(entry)
            save_data(self.data["fids"], self.data["cdks"], self.get_window_geometry())
        self.btn_add_fid.setEnabled(True)

    def remove_fid(self):
        for item in self.list_fid.selectedItems():
            self.data["fids"].remove(item.text())
            self.list_fid.takeItem(self.list_fid.row(item))
        save_data(self.data["fids"], self.data["cdks"], self.get_window_geometry())

    def add_cdk(self):
        cdk = self.input_cdk.text().strip()
        if cdk:
            self.list_cdk.addItem(cdk)
            self.data["cdks"].append(cdk)
            save_data(self.data["fids"], self.data["cdks"], self.get_window_geometry())
            self.input_cdk.clear()

    def remove_cdk(self):
        for item in self.list_cdk.selectedItems():
            self.data["cdks"].remove(item.text())
            self.list_cdk.takeItem(self.list_cdk.row(item))
        save_data(self.data["fids"], self.data["cdks"], self.get_window_geometry())

    def start_redeem(self):
        fids = [self.list_fid.item(i).text() for i in range(self.list_fid.count())]
        cdks = [self.list_cdk.item(i).text() for i in range(self.list_cdk.count())]

        if not fids or not cdks:
            self.result_text.append("[错误] 请至少添加一个玩家和礼包码")
            return

        self.btn_redeem.setEnabled(False)  # 禁用兑换按钮
        self.result_text.append("开始兑换...\n")

        self.redeem_thread = RedeemThread(fids, cdks)
        self.redeem_thread.update_signal.connect(self.result_text.append)
        self.redeem_thread.finished_signal.connect(self.on_redeem_finished)
        self.redeem_thread.start()

    def on_redeem_finished(self):
        self.btn_redeem.setEnabled(True)  # 兑换完成后恢复按钮
        self.result_text.append("\n兑换完成！")

    def get_window_geometry(self):
        return {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height()
        }


class RedeemThread(QThread):
    update_signal = pyqtSignal(str)  # 用于更新 UI 的信号
    finished_signal = pyqtSignal()  # 兑换完成信号

    def __init__(self, fids, cdks):
        super().__init__()
        self.fids = fids
        self.cdks = cdks

    def run(self):
        retry_time = 10
        for i, fid_entry in enumerate(self.fids):
            fid = fid_entry.split(" (")[1][:-1]
            # 登录重试逻辑
            for attempt in range(1, retry_time + 1):
                login_response = login_fid(headers, fid)
                if login_response.get("msg") == "success":
                    break
                elif attempt < retry_time:
                    self.update_signal.emit(f"[登录重试] 玩家 {fid} 第 {attempt} 次失败，重试中...")
                    time.sleep(1)
                else:
                    self.update_signal.emit(f"[登录失败] 玩家 {fid}: {login_response}\n")
                    break
            else:
                continue  # 跳过当前 fid，进行下一个

            nick_name = login_response['data']['nickname']
            kid = login_response['data']['kid']
            new_entry = f"{nick_name} ({fid})"
            self.fids[i] = new_entry  # 更新 FID 名字
            self.update_signal.emit(f"[登录成功] 玩家 [{kid}区][{nick_name}]({fid})")
            time.sleep(2)
            for cdk in self.cdks:
                # 兑换重试逻辑
                for attempt in range(1, retry_time + 1):
                    try:
                        redeem_response = redeem_code(headers, fid, cdk)
                        msg = redeem_response.get("msg", "")
                        if msg == "SUCCESS":
                            self.update_signal.emit(f"[兑换] 玩家 {nick_name} 礼包 {cdk} 成功")
                            break
                        elif msg == "RECEIVED.":
                            self.update_signal.emit(f"[兑换] 玩家 {nick_name} 礼包 {cdk} 重复兑换")
                            break
                        elif msg == "CAPTCHA CHECK ERROR.":
                            self.update_signal.emit(
                                f"[兑换] 玩家 {nick_name} 礼包 {cdk} 验证码校验失败， 第 {attempt} 次失败，重试中...")
                            time.sleep(5)
                        elif attempt < retry_time:
                            self.update_signal.emit(
                                f"[兑换重试] 玩家 {nick_name} 礼包 {cdk} 第 {attempt} 次失败，重试中...")
                            time.sleep(5)
                        else:
                            self.update_signal.emit(f"[兑换] 玩家 {nick_name} 礼包 {cdk} 兑换失败: {redeem_response}")
                    except Exception as e:
                        pass
                self.update_signal.emit("")
                time.sleep(4)

        self.finished_signal.emit()  # 兑换完成，通知主线程


class LoginThread(QThread):
    response_signal = pyqtSignal(dict)  # 用于更新 UI 的信号

    def __init__(self, fid):
        super().__init__()
        self.fid = fid

    def run(self):
        login_response = login_fid(headers, self.fid)
        login_response["fid"] = self.fid
        self.response_signal.emit(login_response)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GiftRedeemApp()
    window.show()
    sys.exit(app.exec_())
