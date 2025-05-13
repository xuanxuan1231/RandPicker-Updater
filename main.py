import sys
import time
import argparse

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStackedWidget, QVBoxLayout, QWidget, QSpacerItem, QSizePolicy
from qfluentwidgets import setTheme, Theme, TitleLabel, PrimaryPushButton, BodyLabel, PushButton, TextBrowser
from qframelesswindow import FramelessWindow, StandardTitleBar
import requests

from loguru import logger

# 适配高DPI缩放
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

window = None
latest = {}
is_latest = True
origin = 'github'

class PreparingPage(QWidget):
    nextPage = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.titleLabel = TitleLabel("请稍候......")
        self.contentLabel = BodyLabel("正在准备 RandPicker 更新助理。")
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.nextButton = PrimaryPushButton("Go to Page Two")
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.contentLabel)
        layout.addSpacerItem(self.spacer)
        layout.addWidget(self.nextButton)
        self.setLayout(layout)

    def prepare(self):
        global latest, origin
        
        if origin == 'oss':
            MANIFEST_URL = "https://oss.may.pp.ua/latest.json"
        else:
            MANIFEST_URL = "https://api.github.com/repos/xuanxuan1231/RandPicker/releases/latest"
        try:
            response = requests.get(MANIFEST_URL, timeout=5)
            response.raise_for_status()
            DOWNLOAD_URL = response.json().get('assets')[0].get('browser_download_url')

            latest = {
                'version': response.json().get('tag_name'),
                'url': DOWNLOAD_URL,
                'changelog': response.json().get('body')
            }
            
        except Exception as e:
            logger.error(f'检查更新时发生错误。{e}')
            latest = {
                'version': "0.0.0",
                'url': None,
                'changelog': f"出错了。{e}"
            }
        

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
        if not is_latest and latest['version'] != "0.0.0":
            self.titleLabel = TitleLabel("有新更新。")
            self.contentLabel = BodyLabel("有新版本待更新。")
            self.changelog = TextBrowser()
            self.changelog.setMarkdown(latest['changelog'])
            self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.nextButton = PrimaryPushButton("更新")
            self.nextButton.clicked.connect(lambda: self.nextPage.emit())
        elif latest['version'] == '0.0.0':
            self.titleLabel = TitleLabel("出错了。")
            self.contentLabel = BodyLabel("请退出 RandPicker 更新助理，然后再试一次。")
            self.changelog = TextBrowser()
            self.changelog.setMarkdown(latest['changelog'])
            self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.nextButton = PrimaryPushButton("退出 RandPicker 更新助理")
            self.nextButton.clicked.connect(lambda: QApplication.quit())
        else:
            self.titleLabel = TitleLabel("无可用更新。")
            self.contentLabel = BodyLabel("您的 RandPicker 已是最新版本。")
            self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.nextButton = PrimaryPushButton("退出 RandPicker 更新助理")
            self.nextButton.clicked.connect(lambda: QApplication.quit())
        buttonLayout.addWidget(self.nextButton)
        self.layout.addWidget(self.titleLabel)
        self.layout.addWidget(self.contentLabel)
        if not is_latest:
            self.layout.addWidget(self.changelog)
        self.layout.addSpacerItem(self.spacer)
        self.layout.addLayout(buttonLayout)
class MainWindow(FramelessWindow):
    prepare = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setTitleBar(StandardTitleBar(self))
        self.titleBar.raise_()
        self.setWindowTitle("RandPicker 更新助理")
        self.setWindowIcon(QIcon("./assets/Logo.png"))

        #self.setMinimumSize(400, 300)
        #self.setFixedSize(400, 300)
        self.resize(400, 300)
        self.setFixedSize(400, 300)  # 设置固定窗口大小，禁止调整大小
        self.titleBar.minBtn.setVisible(False)
        self.titleBar.maxBtn.setVisible(False)

        # 创建 QStackedWidget
        self.stacked_widget = QStackedWidget()

        # 创建页面
        self.page1 = PreparingPage()
        self.page2 = PreUpdatePage()

        # 将页面添加到 QStackedWidget
        self.stacked_widget.addWidget(self.page1)
        self.stacked_widget.addWidget(self.page2)

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
        self.page2.previousPage.connect(self.previous_page)

    def next_page(self):
        current_index = self.stacked_widget.currentIndex()
        eval(f"self.page{current_index + 2}.prepare()")
        if current_index < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(current_index + 1)
            logger.debug(f"从 {current_index} 切换到 {current_index + 1}。")
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
        "-o", "--origin", type=str, help="更新源", default="github",)
    argparser.add_argument("-l", "--latest", type=str, help="是否有最新版本", choices=["true", "false"], default="true")
    args = argparser.parse_args()
    is_latest = args.latest == "true"
    origin = 'github' if args.origin != 'oss' else 'oss'
    main()