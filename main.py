import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow
from config import Config


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)

    # 设置应用程序属性
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.VERSION)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 创建数据目录
    os.makedirs("data", exist_ok=True)

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()