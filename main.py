import sys
import argparse
import os
import shutil
import zipfile

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSpacerItem,
    QSizePolicy,
)
from qfluentwidgets import (
    setTheme,
    Theme,
    TitleLabel,
    PrimaryPushButton,
    BodyLabel,
    PushButton,
    TextBrowser,
    CaptionLabel,
    ProgressBar,
    IndeterminateProgressBar,
)
from qframelesswindow import FramelessWindow, StandardTitleBar
import requests

from loguru import logger

# 适配高DPI缩放
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

window = None
latest = {}
is_latest = True
origin = "github"


class PreparingPage(QWidget):
    nextPage = pyqtSignal()

    class PrepareWorker(QThread):
        finished = pyqtSignal(dict)
        error = pyqtSignal(str)

        def __init__(self, origin):
            super().__init__()
            self.origin = origin

        def run(self):
            import requests

            try:
                if self.origin == "oss":
                    MANIFEST_URL = "https://oss.may.pp.ua/latest.json"
                else:
                    MANIFEST_URL = "https://api.github.com/repos/xuanxuan1231/RandPicker/releases/latest"
                response = requests.get(MANIFEST_URL, timeout=5)
                response.raise_for_status()
                data = response.json()
                if self.origin == "oss":
                    # oss接口结构兼容处理
                    latest = {
                        "version": data.get("tag_name", data.get("version", "0.0.0")),
                        "url": data.get("assets", [{}])[0].get(
                            "browser_download_url", data.get("url")
                        ),
                        "changelog": data.get("body", data.get("changelog", "")),
                    }
                else:
                    latest = {
                        "version": data.get("tag_name"),
                        "url": data.get("assets")[0].get("browser_download_url"),
                        "changelog": data.get("body"),
                    }
                self.finished.emit(latest)
            except Exception as e:
                self.error.emit(str(e))

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.titleLabel = TitleLabel("请稍候......")
        self.contentLabel = BodyLabel("正在准备 RandPicker 更新助理。")
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.bar = IndeterminateProgressBar(start=True)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.contentLabel)
        layout.addSpacerItem(self.spacer)
        layout.addWidget(self.bar)
        self.setLayout(layout)
        self.worker = None

    def prepare(self):
        global latest, origin
        self.bar.start()
        self.worker = self.PrepareWorker(origin)
        self.worker.finished.connect(self.on_prepare_finished)
        self.worker.error.connect(self.on_prepare_error)
        self.worker.start()

    def on_prepare_finished(self, result):
        global latest
        latest = result
        self.bar.stop()
        self.nextPage.emit()

    def on_prepare_error(self, err):
        global latest
        logger.error(f"检查更新时发生错误。{err}")
        latest = {"version": "0.0.0", "url": None, "changelog": f"出错了。{err}"}
        self.bar.stop()
        self.nextPage.emit()


class PreUpdatePage(QWidget):
    nextPage = pyqtSignal()
    previousPage = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

    def prepare(self):
        buttonLayout = QVBoxLayout()
        global latest, is_latest
        print(latest)
        if not is_latest and latest["version"] != "0.0.0":
            self.titleLabel = TitleLabel("有新更新。")
            self.contentLabel = BodyLabel("有新版本待更新。")
            self.changelog = TextBrowser()
            self.changelog.setMarkdown(latest["changelog"])
            self.spacer = QSpacerItem(
                20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.nextButton = PrimaryPushButton("更新")
            self.nextButton.clicked.connect(lambda: self.nextPage.emit())
        elif latest["version"] == "0.0.0":
            self.titleLabel = TitleLabel("出错了。")
            self.contentLabel = BodyLabel("请退出 RandPicker 更新助理，然后再试一次。")
            self.changelog = TextBrowser()
            self.changelog.setMarkdown(latest["changelog"])
            self.spacer = QSpacerItem(
                20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.nextButton = PrimaryPushButton("退出 RandPicker 更新助理")
            self.nextButton.clicked.connect(lambda: QApplication.quit())
        else:
            self.titleLabel = TitleLabel("无可用更新。")
            self.contentLabel = BodyLabel("您的 RandPicker 已是最新版本。")
            self.spacer = QSpacerItem(
                20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.nextButton = PrimaryPushButton("退出 RandPicker 更新助理")
            self.nextButton.clicked.connect(lambda: QApplication.quit())
        buttonLayout.addWidget(self.nextButton)
        self.layout.addWidget(self.titleLabel)
        self.layout.addWidget(self.contentLabel)
        if not is_latest or latest["version"] == "0.0.0":
            self.layout.addWidget(self.changelog)
        self.layout.addSpacerItem(self.spacer)
        self.layout.addLayout(buttonLayout)


class ConfirmPage(QWidget):
    nextPage = pyqtSignal()
    previousPage = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.titleLabel = TitleLabel("确认更新")
        self.contentLabel = BodyLabel("请确认您要更新 RandPicker 吗？")
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.nextButton = PrimaryPushButton("更新")
        self.previousButton = PushButton("上一页")
        self.nextButton.clicked.connect(lambda: self.nextPage.emit())
        self.previousButton.clicked.connect(lambda: self.previousPage.emit())
        self.layout.addWidget(self.titleLabel)
        self.layout.addWidget(self.contentLabel)
        self.layout.addSpacerItem(self.spacer)
        self.layout.addWidget(self.nextButton)
        self.layout.addWidget(self.previousButton)


class UpdatePage(QWidget):
    nextPage = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.titleLabel = TitleLabel("正在更新 RandPicker")
        self.contentLabel = BodyLabel("请稍候......")
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.captionLabel = CaptionLabel("正在准备更新")
        self.progressBar = ProgressBar()
        self.progressBar.setRange(0, 100)
        self.layout.addWidget(self.titleLabel)
        self.layout.addWidget(self.contentLabel)
        self.layout.addSpacerItem(self.spacer)
        self.layout.addWidget(self.captionLabel)
        self.layout.addWidget(self.progressBar)

    def prepare(self):
        global latest
        DOWNLOAD_URL = latest["url"]
        BACKUP_URLS = [
            f"https://ghfast.top/{DOWNLOAD_URL}",
            f"https://gh-proxy.com/{DOWNLOAD_URL}",
            f"https://github.moeyy.xyz/{DOWNLOAD_URL}",
        ]

        try:
            # 备份旧版本
            logger.info("开始备份旧版本。")
            self.captionLabel.setText("备份旧版本文件。")
            backup_folder = "backup"
            if not os.path.exists(backup_folder):
                os.makedirs(backup_folder)
            for file_name in os.listdir("."):
                if file_name not in [
                    "config.ini",
                    "students.json",
                    "Updater.exe",
                ] and os.path.isfile(file_name):
                    shutil.move(file_name, os.path.join(backup_folder, file_name))
                if file_name not in ["backup"] and os.path.isdir(file_name):
                    shutil.move(file_name, os.path.join(backup_folder, file_name))

            self.progressBar.setValue(15)
            logger.info("旧版本备份完成。")

            # 下载更新
            def download_with_url(url):
                self.captionLabel.setText(f"正在下载更新文件：{url}")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0
                with open("update.zip", "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                            downloaded_size += len(chunk)
                            progress = int((downloaded_size / total_size) * 60)
                            self.progressBar.setValue(progress + 15)
                            QApplication.processEvents()
                logger.info("文件下载完成。")
                self.captionLabel.setText("更新文件下载完成。")

            download_success = False
            if DOWNLOAD_URL:
                logger.info(f"准备从 {DOWNLOAD_URL} 下载更新。")
                try:
                    download_with_url(DOWNLOAD_URL)
                    download_success = True
                except Exception as e:
                    logger.error(f"下载更新时发生错误: {e}")
                    self.captionLabel.setText("主下载源失败，尝试备用下载源……")
                    QApplication.processEvents()
                    for backup_url in BACKUP_URLS:
                        try:
                            download_with_url(backup_url)
                            download_success = True
                            break
                        except Exception as e2:
                            logger.error(f"备用下载源 {backup_url} 失败: {e2}")
                            self.captionLabel.setText("备用下载源失败，尝试下一个……")
                            QApplication.processEvents()
            if not download_success:
                self.captionLabel.setText("下载更新时发生错误。")
                return

            # 解压更新
            if os.path.exists("update.zip"):
                update_file = zipfile.ZipFile("update.zip")
                self.captionLabel.setText("正在解压更新文件。")
                total_files = len(update_file.namelist())
                for index, file in enumerate(update_file.namelist()):
                    update_file.extract(file)
                    progress = int(((index + 1) / total_files) * 18)
                    self.progressBar.setValue(progress + 75)
                    QApplication.processEvents()
                update_file.close()
                logger.info("解压完成。")
                self.captionLabel.setText("更新文件解压完成。")

            # 移动更新文件
            if os.path.exists("RandPicker"):
                total_files = len(os.listdir("RandPicker"))
                self.captionLabel.setText("正在移动更新文件。")
                for index, file in enumerate(os.listdir("RandPicker")):
                    shutil.move(
                        os.path.join("RandPicker", file), os.path.join(".", file)
                    )
                    progress = int(((index + 1) / total_files) * 14)
                    self.progressBar.setValue(progress + 83)
                    QApplication.processEvents()
                shutil.rmtree("RandPicker")
                logger.info("移动完成。")
                self.captionLabel.setText("更新文件移动完成。")

            # 清理文件
            if os.path.exists("update.zip"):
                self.captionLabel.setText("正在清理更新文件。")
                os.remove("update.zip")
                QApplication.processEvents()
                self.progressBar.setValue(100)
                logger.info("清理完成。")

            self.nextPage.emit()

        except Exception as e:
            logger.error(f"更新时发生错误: {e}")
            self.captionLabel.setText("更新时发生错误。")
            return


class FinishPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.buttonLayout = QHBoxLayout()
        self.setLayout(self.layout)
        self.titleLabel = TitleLabel("更新完成")
        self.contentLabel = BodyLabel("RandPicker 更新助理已完成更新。")
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.nextButton = PrimaryPushButton("退出更新助理")
        self.nextButton.clicked.connect(lambda: QApplication.quit())
        self.openNewButton = PushButton("启动 RandPicker")
        self.openNewButton.clicked.connect(self.open_new_version)
        self.buttonLayout.addWidget(self.openNewButton)
        self.buttonLayout.addWidget(self.nextButton)
        self.layout.addWidget(self.titleLabel)
        self.layout.addWidget(self.contentLabel)
        self.layout.addSpacerItem(self.spacer)
        self.layout.addWidget(self.nextButton)
        self.layout.addLayout(self.buttonLayout)

    def open_new_version(self):
        if os.path.exists("RandPicker.exe"):
            os.system("start RandPicker.exe")

        QApplication.quit()


class MainWindow(FramelessWindow):
    prepare = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setTitleBar(StandardTitleBar(self))
        self.titleBar.raise_()
        self.setWindowTitle("RandPicker 更新助理")
        self.setWindowIcon(QIcon("./assets/Logo.png"))

        self.setMinimumSize(400, 300)  # 设置最小窗口大小
        self.setFixedSize(400, 300)  # 设置固定窗口大小，禁止调整大小
        self.titleBar.minBtn.setVisible(False)
        self.titleBar.maxBtn.setVisible(False)

        # 创建 QStackedWidget
        self.stacked_widget = QStackedWidget()

        # 创建页面
        self.page1 = PreparingPage()
        self.page2 = PreUpdatePage()
        self.page3 = ConfirmPage()
        self.page4 = UpdatePage()
        self.page5 = FinishPage()

        # 将页面添加到 QStackedWidget
        self.stacked_widget.addWidget(self.page1)
        self.stacked_widget.addWidget(self.page2)
        self.stacked_widget.addWidget(self.page3)
        self.stacked_widget.addWidget(self.page4)
        self.stacked_widget.addWidget(self.page5)

        # 布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(9, 32, 9, 9)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        # 设置初始页面
        self.stacked_widget.setCurrentIndex(0)

        # 连接按钮信号到切换页面的槽函数
        self.prepare.connect(lambda: self.page1.prepare())
        self.page1.nextPage.connect(self.next_page)
        self.page2.nextPage.connect(self.next_page)
        self.page3.nextPage.connect(self.next_page)
        self.page4.nextPage.connect(self.next_page)
        self.page5.nextPage.connect(self.next_page)
        self.page2.previousPage.connect(self.previous_page)
        self.page3.previousPage.connect(self.previous_page)

    def next_page(self):
        current_index = self.stacked_widget.currentIndex()
        if current_index < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(current_index + 1)
            logger.debug(f"从 {current_index} 切换到 {current_index + 1}。")
            next_page = getattr(self, f"page{current_index + 2}", None)
            if getattr(next_page, "prepare", None) is not None:
                next_page.prepare()
            return
        logger.debug("已到达最后一页。没有切换。")

    def previous_page(self):
        current_index = self.stacked_widget.currentIndex()
        if current_index > 0:
            self.stacked_widget.setCurrentIndex(current_index - 1)
            logger.debug(f"从 {current_index} 切换到 {current_index - 1}。")
            return
        logger.debug("已到达第一页。没有切换。")


def main():
    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)
    window = MainWindow()
    window.show()
    window.prepare.emit()
    logger.info("应用程序已启动。")
    sys.exit(app.exec())


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="RandPicker 更新助理")
    argparser.add_argument(
        "-o",
        "--origin",
        type=str,
        help="更新源",
        default="github",
    )
    argparser.add_argument(
        "-l",
        "--latest",
        type=str,
        help="是否有最新版本",
        choices=["true", "false"],
        default="true",
    )
    args = argparser.parse_args()
    is_latest = args.latest == "true"
    origin = "github" if args.origin != "oss" else "oss"
    main()
