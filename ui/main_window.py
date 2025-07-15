from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QSplitter, QToolBar, QStatusBar, QPushButton,
                             QLabel, QListWidget, QProgressBar, QFileDialog,
                             QMessageBox, QInputDialog, QGroupBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QIcon
import os
import json

from ui.image_viewer import ImageViewer  # 使用更新后的ImageViewer
from ui.category_manager import CategoryManager
from ui.styles import get_main_style
from utils.file_utils import get_image_files, load_annotations, save_annotations, get_annotation_stats
from utils.dataset_exporter import DatasetExporter
from config import Config


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.image_files = []
        self.current_image_index = -1
        self.annotations_data = load_annotations(Config.ANNOTATIONS_FILE)
        self.current_folder = ""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(30000)  # 每30秒自动保存

        self.init_ui()
        self.setup_shortcuts()
        self.update_ui_state()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"{Config.APP_NAME} v{Config.VERSION}")
        self.setGeometry(100, 100, Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
        self.setStyleSheet(get_main_style())

        # 创建主要组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧面板（图像列表和类别管理）
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 中间面板（图像查看器）
        middle_panel = self.create_middle_panel()
        splitter.addWidget(middle_panel)

        # 右侧面板（统计信息）
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)  # 左侧
        splitter.setStretchFactor(1, 3)  # 中间
        splitter.setStretchFactor(2, 1)  # 右侧

        main_layout.addWidget(splitter)

        # 创建状态栏
        self.create_status_bar()

        # 创建工具栏
        self.create_toolbar()

    def create_middle_panel(self):
        """创建中间面板"""
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)

        # 图像信息
        self.image_info_label = QLabel("请打开一个包含图像的文件夹")
        self.image_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #666;")
        middle_layout.addWidget(self.image_info_label)

        # 使用新的图像查看器
        self.image_viewer = ImageViewer()
        middle_layout.addWidget(self.image_viewer)

        # 导航按钮
        nav_layout = QHBoxLayout()

        self.prev_btn = QPushButton("⬅️ 上一张 (A)")
        self.prev_btn.clicked.connect(self.previous_image)
        self.prev_btn.setEnabled(False)

        self.next_btn = QPushButton("下一张 (D) ➡️")
        self.next_btn.clicked.connect(self.next_image)
        self.next_btn.setEnabled(False)

        # 添加缩放控制按钮
        zoom_in_btn = QPushButton("🔍+ 放大")
        zoom_in_btn.clicked.connect(self.image_viewer.zoom_in)

        zoom_out_btn = QPushButton("🔍- 缩小")
        zoom_out_btn.clicked.connect(self.image_viewer.zoom_out)

        fit_btn = QPushButton("📐 适应")
        fit_btn.clicked.connect(self.image_viewer.fit_to_window)

        reset_btn = QPushButton("🔄 重置")
        reset_btn.clicked.connect(self.image_viewer.reset_zoom)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(zoom_out_btn)
        nav_layout.addWidget(zoom_in_btn)
        nav_layout.addWidget(fit_btn)
        nav_layout.addWidget(reset_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)

        middle_layout.addLayout(nav_layout)

        return middle_widget

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 鼠标位置显示
        self.mouse_pos_label = QLabel("")
        self.status_bar.addWidget(self.mouse_pos_label)

        # 快捷键提示
        shortcut_label = QLabel("快捷键: A/D(导航) | 鼠标滚轮(缩放) | 拖拽(平移) | 1-9,0(选择类别) | Ctrl+S(保存)")
        self.status_bar.addPermanentWidget(shortcut_label)

    def update_mouse_status(self, text):
        """更新鼠标状态显示"""
        self.mouse_pos_label.setText(text)

    def load_current_image(self):
        """加载当前图像"""
        if 0 <= self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]

            # 高亮当前图像
            self.image_list.setCurrentRow(self.current_image_index)

            # 加载图像
            if self.image_viewer.load_image(image_path):
                filename = os.path.basename(image_path)
                self.current_image_label.setText(f"文件名: {filename}")

                # 获取图像尺寸信息
                width, height = self.image_viewer.get_image_size()

                # 更新图像信息
                self.image_info_label.setText(
                    f"图像 {self.current_image_index + 1} / {len(self.image_files)} | "
                    f"尺寸: {width} x {height} 像素"
                )

                # 显示当前标注
                self.update_current_annotation_display()

                # 更新进度
                self.update_progress()

    # 其他方法保持不变...
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # 打开文件夹
        open_action = QAction("📁 打开文件夹", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_folder)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        # 导航按钮
        prev_action = QAction("⬅️ 上一张", self)
        prev_action.setShortcut(QKeySequence.StandardKey.MoveToPreviousChar)
        prev_action.triggered.connect(self.previous_image)
        toolbar.addAction(prev_action)

        next_action = QAction("➡️ 下一张", self)
        next_action.setShortcut(QKeySequence.StandardKey.MoveToNextChar)
        next_action.triggered.connect(self.next_image)
        toolbar.addAction(next_action)

        toolbar.addSeparator()

        # 缩放控制
        zoom_in_action = QAction("🔍+ 放大", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.image_viewer.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("🔍- 缩小", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.image_viewer.zoom_out)
        toolbar.addAction(zoom_out_action)

        fit_action = QAction("📐 适应窗口", self)
        fit_action.triggered.connect(self.image_viewer.fit_to_window)
        toolbar.addAction(fit_action)

        reset_action = QAction("🔄 重置视图", self)
        reset_action.triggered.connect(self.image_viewer.reset_zoom)
        toolbar.addAction(reset_action)

        toolbar.addSeparator()

        # 保存和导出
        save_action = QAction("💾 保存标注", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_annotations)
        toolbar.addAction(save_action)

        export_action = QAction("📤 导出数据集", self)
        export_action.triggered.connect(self.export_dataset)
        toolbar.addAction(export_action)

    def create_left_panel(self):
        """创建左侧面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 图像列表
        image_group = QGroupBox("图像列表")
        image_layout = QVBoxLayout()

        self.image_list = QListWidget()
        self.image_list.currentRowChanged.connect(self.on_image_selected)
        image_layout.addWidget(self.image_list)

        image_group.setLayout(image_layout)
        left_layout.addWidget(image_group)

        # 类别管理器
        self.category_manager = CategoryManager()
        self.category_manager.category_selected.connect(self.on_category_selected)

        # 加载保存的类别
        if 'categories' in self.annotations_data:
            self.category_manager.set_categories(self.annotations_data['categories'])

        left_layout.addWidget(self.category_manager)

        return left_widget

    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 当前图像信息
        current_info_group = QGroupBox("当前图像")
        current_info_layout = QVBoxLayout()

        self.current_image_label = QLabel("文件名: 无")
        self.current_category_label = QLabel("类别: 未标注")
        self.current_category_label.setStyleSheet("font-weight: bold;")

        current_info_layout.addWidget(self.current_image_label)
        current_info_layout.addWidget(self.current_category_label)
        current_info_group.setLayout(current_info_layout)
        right_layout.addWidget(current_info_group)

        # 进度信息
        progress_group = QGroupBox("标注进度")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("0 / 0 (0.0%)")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        progress_group.setLayout(progress_layout)
        right_layout.addWidget(progress_group)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()

        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)

        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)

        right_layout.addStretch()

        return right_widget

    def setup_shortcuts(self):
        """设置快捷键"""
        # 导航快捷键
        QShortcut(Qt.Key.Key_A, self, self.previous_image)
        QShortcut(Qt.Key.Key_D, self, self.next_image)
        QShortcut(Qt.Key.Key_Left, self, self.previous_image)
        QShortcut(Qt.Key.Key_Right, self, self.next_image)

        # 类别选择快捷键
        for key, index in Config.SHORTCUTS.items():
            if key.isdigit():
                qt_key = getattr(Qt.Key, f'Key_{key}')
                QShortcut(qt_key, self, lambda idx=index: self.select_category_by_index(idx))

    def open_folder(self):
        """打开文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择包含图像的文件夹")
        if folder:
            self.current_folder = folder
            self.load_images_from_folder(folder)

    def load_images_from_folder(self, folder):
        """从文件夹加载图像"""
        self.status_label.setText("正在加载图像...")

        self.image_files = get_image_files(folder)

        if not self.image_files:
            QMessageBox.information(self, "信息", "所选文件夹中没有找到支持的图像文件。")
            self.status_label.setText("就绪")
            return

        # 更新图像列表
        self.image_list.clear()
        for image_path in self.image_files:
            filename = os.path.basename(image_path)
            self.image_list.addItem(filename)

        self.current_image_index = 0
        self.load_current_image()
        self.update_ui_state()
        self.update_statistics()

        self.status_label.setText(f"已加载 {len(self.image_files)} 张图像")

    def update_current_annotation_display(self):
        """更新当前标注显示"""
        if 0 <= self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]
            annotation = self.annotations_data.get('annotations', {}).get(image_path, {})

            category = annotation.get('category', '未标注')
            self.current_category_label.setText(f"类别: {category}")

            # 更新类别管理器选择
            categories = self.category_manager.get_categories()
            if category in categories:
                index = categories.index(category)
                self.category_manager.select_category(index)
            else:
                self.category_manager.selected_category = -1
                self.category_manager.update_selected_label()
                # 更新按钮样式
                for button in self.category_manager.category_buttons:
                    from ui.styles import get_category_button_style
                    button.setStyleSheet(get_category_button_style(False))

    def previous_image(self):
        """上一张图像"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()
            self.update_ui_state()

    def next_image(self):
        """下一张图像"""
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_current_image()
            self.update_ui_state()

    def on_image_selected(self, index):
        """图像列表选择事件"""
        if 0 <= index < len(self.image_files):
            self.current_image_index = index
            self.load_current_image()
            self.update_ui_state()

    def on_category_selected(self, category_index, category_name):
        """类别选择事件"""
        if 0 <= self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]

            # 更新标注数据
            if 'annotations' not in self.annotations_data:
                self.annotations_data['annotations'] = {}

            self.annotations_data['annotations'][image_path] = {
                'category': category_name,
                'category_index': category_index
            }

            # 更新显示
            self.current_category_label.setText(f"类别: {category_name}")
            self.current_category_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

            # 更新统计
            self.update_statistics()
            self.update_progress()

            self.status_label.setText(f"已标注: {category_name}")

    def select_category_by_index(self, index):
        """通过索引选择类别"""
        categories = self.category_manager.get_categories()
        if 0 <= index < len(categories):
            self.category_manager.select_category(index)

    def update_ui_state(self):
        """更新界面状态"""
        has_images = len(self.image_files) > 0

        self.prev_btn.setEnabled(has_images and self.current_image_index > 0)
        self.next_btn.setEnabled(has_images and self.current_image_index < len(self.image_files) - 1)

    def update_progress(self):
        """更新进度"""
        if not self.image_files:
            self.progress_bar.setValue(0)
            self.progress_label.setText("0 / 0 (0.0%)")
            return

        annotations = self.annotations_data.get('annotations', {})
        annotated_count = sum(1 for path in self.image_files if path in annotations)
        total_count = len(self.image_files)

        progress_percent = (annotated_count / total_count) * 100 if total_count > 0 else 0

        self.progress_bar.setMaximum(total_count)
        self.progress_bar.setValue(annotated_count)
        self.progress_label.setText(f"{annotated_count} / {total_count} ({progress_percent:.1f}%)")

    def update_statistics(self):
        """更新统计信息"""
        if not self.image_files:
            self.stats_text.clear()
            return

        annotations = self.annotations_data.get('annotations', {})

        # 过滤出当前文件夹的标注
        current_annotations = {}
        for path in self.image_files:
            if path in annotations:
                current_annotations[path] = annotations[path]

        stats, total = get_annotation_stats(current_annotations)

        stats_text = f"总图像数: {len(self.image_files)}\n"
        stats_text += f"已标注数: {total}\n"
        stats_text += f"未标注数: {len(self.image_files) - total}\n\n"

        if stats:
            stats_text += "各类别统计:\n"
            for category, count in sorted(stats.items()):
                if category != '未标注':
                    percentage = (count / len(self.image_files)) * 100
                    stats_text += f"  {category}: {count} ({percentage:.1f}%)\n"

        self.stats_text.setText(stats_text)

    def save_annotations(self):
        """保存标注"""
        # 更新类别列表
        self.annotations_data['categories'] = self.category_manager.get_categories()

        if save_annotations(Config.ANNOTATIONS_FILE, self.annotations_data):
            self.status_label.setText("标注已保存")
            QMessageBox.information(self, "成功", "标注文件已保存！")
        else:
            QMessageBox.critical(self, "错误", "保存标注文件失败！")

    def auto_save(self):
        """自动保存"""
        if self.annotations_data.get('annotations'):
            self.annotations_data['categories'] = self.category_manager.get_categories()
            save_annotations(Config.ANNOTATIONS_FILE, self.annotations_data)

    def export_dataset(self):
        """导出数据集"""
        if not self.annotations_data.get('annotations'):
            QMessageBox.warning(self, "警告", "没有标注数据可导出！")
            return

        # 选择导出目录
        output_dir = QFileDialog.getExistingDirectory(self, "选择数据集导出目录")
        if not output_dir:
            return

        # 询问是否复制图像文件
        reply = QMessageBox.question(
            self, "导出选项", "是否复制图像文件到导出目录？\n\n"
                              "是: 复制图像文件（推荐，便于训练）\n"
                              "否: 仅创建目录结构和索引文件",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        copy_images = reply == QMessageBox.StandardButton.Yes

        # 导出数据集
        exporter = DatasetExporter()
        success, result = exporter.export_dataset(self.annotations_data, output_dir, copy_images)

        if success:
            # 显示导出结果
            info_text = f"数据集导出成功！\n\n"
            info_text += f"导出位置: {output_dir}\n"
            info_text += f"总类别数: {result['num_classes']}\n"
            info_text += f"总图像数: {result['total_images']}\n"
            info_text += f"训练集: {result['train_images']} 张\n"
            info_text += f"验证集: {result['val_images']} 张\n\n"
            info_text += "各类别分布:\n"

            for category, stats in result['category_stats'].items():
                info_text += f"  {category}: {stats['total']} 张 (训练: {stats['train']}, 验证: {stats['val']})\n"

            QMessageBox.information(self, "导出成功", info_text)
            self.status_label.setText("数据集导出完成")
        else:
            QMessageBox.critical(self, "导出失败", f"数据集导出失败: {result}")

    def closeEvent(self, event):
        """关闭事件"""
        # 保存标注数据
        self.annotations_data['categories'] = self.category_manager.get_categories()
        save_annotations(Config.ANNOTATIONS_FILE, self.annotations_data)

        reply = QMessageBox.question(
            self, "确认退出", "确定要退出程序吗？标注数据已自动保存。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()