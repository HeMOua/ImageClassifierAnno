from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QSplitter, QToolBar, QStatusBar, QPushButton,
                             QLabel, QListWidget, QProgressBar, QFileDialog,
                             QMessageBox, QInputDialog, QGroupBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QIcon
import os
import json
from pathlib import Path

from ui.image_viewer import ImageViewer
from ui.category_manager import CategoryManager
from ui.styles import get_main_style
from utils.file_utils import (get_image_files, load_annotations, save_annotations,
                              get_annotation_stats, get_relative_path, get_absolute_path,
                              validate_image_paths, migrate_annotations_to_new_folder)
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

        # 如果有保存的图片根路径，尝试验证
        if self.annotations_data.get("image_root"):
            self.validate_saved_annotations()

    def validate_saved_annotations(self):
        """验证保存的标注数据"""
        image_root = self.annotations_data.get("image_root", "")
        if not image_root or not os.path.exists(image_root):
            return

        valid_images, missing_images = validate_image_paths(self.annotations_data)

        if missing_images:
            missing_count = len(missing_images)
            total_count = len(valid_images) + missing_count

            msg = f"发现 {missing_count}/{total_count} 张图片文件缺失。\n\n"
            msg += f"上次使用的图片根目录: {image_root}\n\n"
            msg += "选择操作:\n"
            msg += "• 是: 重新选择图片文件夹\n"
            msg += "• 否: 继续使用当前标注数据（缺失的图片将被忽略）\n"
            msg += "• 取消: 清空标注数据重新开始"

            reply = QMessageBox.question(
                self, "图片文件验证", msg,
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.relocate_image_folder()
            elif reply == QMessageBox.StandardButton.Cancel:
                self.annotations_data = load_annotations("")  # 加载默认空数据
        else:
            # 所有图片都存在，自动加载
            self.load_images_from_folder(image_root)

    def relocate_image_folder(self):
        """重新定位图片文件夹"""
        new_folder = QFileDialog.getExistingDirectory(self, "选择新的图片文件夹位置")
        if new_folder:
            old_root = self.annotations_data.get("image_root", "")
            updated_data, missing_files = migrate_annotations_to_new_folder(
                self.annotations_data, old_root, new_folder
            )

            self.annotations_data = updated_data
            self.current_folder = new_folder
            self.load_images_from_folder(new_folder)

            if missing_files:
                msg = f"迁移完成，但仍有 {len(missing_files)} 个文件未找到:\n\n"
                for rel_path, old_path, new_path in missing_files[:10]:  # 只显示前10个
                    msg += f"• {rel_path}\n"
                if len(missing_files) > 10:
                    msg += f"... 还有 {len(missing_files) - 10} 个文件"

                QMessageBox.information(self, "迁移结果", msg)

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

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # 打开文件夹
        open_action = QAction("📁 打开文件夹", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_folder)
        toolbar.addAction(open_action)

        # 重新定位文件夹
        relocate_action = QAction("📂 重新定位文件夹", self)
        relocate_action.triggered.connect(self.relocate_image_folder)
        toolbar.addAction(relocate_action)

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

        # 快速定位功能
        toolbar.addSeparator()
        goto_first_unlabeled_action = QAction("🎯 跳转到未标注", self)
        goto_first_unlabeled_action.setShortcut(QKeySequence("Ctrl+U"))
        goto_first_unlabeled_action.triggered.connect(self.goto_first_unlabeled_image)
        toolbar.addAction(goto_first_unlabeled_action)

        goto_next_unlabeled_action = QAction("⏭️ 下一个未标注", self)
        goto_next_unlabeled_action.setShortcut(QKeySequence("Shift+U"))
        goto_next_unlabeled_action.triggered.connect(self.goto_next_unlabeled_image)
        toolbar.addAction(goto_next_unlabeled_action)

        goto_prev_unlabeled_action = QAction("⏮️ 上一个未标注", self)
        goto_prev_unlabeled_action.setShortcut(QKeySequence("Shift+Ctrl+U"))
        goto_prev_unlabeled_action.triggered.connect(self.goto_prev_unlabeled_image)
        toolbar.addAction(goto_prev_unlabeled_action)

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

        # 添加快速定位按钮
        quick_nav_layout = QHBoxLayout()

        self.goto_first_btn = QPushButton("🎯 首个未标注")
        self.goto_first_btn.setToolTip("跳转到第一张未标注的图片 (Ctrl+U)")
        self.goto_first_btn.clicked.connect(self.goto_first_unlabeled_image)
        self.goto_first_btn.setEnabled(False)

        self.goto_next_btn = QPushButton("⏭️ 下个未标注")
        self.goto_next_btn.setToolTip("跳转到下一张未标注的图片 (Shift+U)")
        self.goto_next_btn.clicked.connect(self.goto_next_unlabeled_image)
        self.goto_next_btn.setEnabled(False)

        quick_nav_layout.addWidget(self.goto_first_btn)
        quick_nav_layout.addWidget(self.goto_next_btn)
        image_layout.addLayout(quick_nav_layout)

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
        self.current_path_label = QLabel("路径: 无")
        self.current_path_label.setWordWrap(True)
        self.current_path_label.setStyleSheet("font-size: 12px; color: #666;")

        current_info_layout.addWidget(self.current_image_label)
        current_info_layout.addWidget(self.current_category_label)
        current_info_layout.addWidget(self.current_path_label)
        current_info_group.setLayout(current_info_layout)
        right_layout.addWidget(current_info_group)

        # 进度信息
        progress_group = QGroupBox("标注进度")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("0 / 0 (0.0%)")

        # 添加未标注数量显示
        self.unlabeled_count_label = QLabel("未标注: 0 张")
        self.unlabeled_count_label.setStyleSheet("color: #f44336; font-weight: bold;")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.unlabeled_count_label)
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

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 鼠标位置显示
        self.mouse_pos_label = QLabel("")
        self.status_bar.addWidget(self.mouse_pos_label)

        # 图片根目录显示
        self.root_path_label = QLabel("")
        self.status_bar.addWidget(self.root_path_label)

        # 快捷键提示
        shortcut_label = QLabel(
            "快捷键: A/D(导航) | Ctrl+U(首个未标注) | Shift+U(下个未标注) | 1-9,0(选择类别) | Ctrl+S(保存)")
        self.status_bar.addPermanentWidget(shortcut_label)

    def update_root_path_display(self):
        """更新根路径显示"""
        image_root = self.annotations_data.get("image_root", "")
        if image_root:
            self.root_path_label.setText(f"根目录: {image_root}")
        else:
            self.root_path_label.setText("")

    def setup_shortcuts(self):
        """设置快捷键"""
        # 导航快捷键
        QShortcut(Qt.Key.Key_A, self, self.previous_image)
        QShortcut(Qt.Key.Key_D, self, self.next_image)
        QShortcut(Qt.Key.Key_Left, self, self.previous_image)
        QShortcut(Qt.Key.Key_Right, self, self.next_image)

        # 快速定位快捷键
        QShortcut(QKeySequence("Ctrl+U"), self, self.goto_first_unlabeled_image)
        QShortcut(QKeySequence("Shift+U"), self, self.goto_next_unlabeled_image)
        QShortcut(QKeySequence("Shift+Ctrl+U"), self, self.goto_prev_unlabeled_image)

        # 类别选择快捷键
        for key, index in Config.SHORTCUTS.items():
            if key.isdigit():
                qt_key = getattr(Qt.Key, f'Key_{key}')
                QShortcut(qt_key, self, lambda idx=index: self.select_category_by_index(idx))

    def get_unlabeled_images(self):
        """获取未标注的图片索引列表"""
        if not self.image_files:
            return []

        image_root = self.annotations_data.get("image_root", "")
        annotations = self.annotations_data.get('annotations', {})

        unlabeled_indices = []
        for i, image_path in enumerate(self.image_files):
            rel_path = get_relative_path(image_path, image_root) if image_root else image_path
            if rel_path not in annotations or not annotations[rel_path].get('category'):
                unlabeled_indices.append(i)

        return unlabeled_indices

    def goto_first_unlabeled_image(self):
        """跳转到第一张未标注的图片"""
        unlabeled_indices = self.get_unlabeled_images()

        if not unlabeled_indices:
            QMessageBox.information(self, "信息", "所有图片都已标注完成！🎉")
            return

        first_unlabeled = unlabeled_indices[0]
        self.current_image_index = first_unlabeled
        self.load_current_image()
        self.update_ui_state()

        self.status_label.setText(f"已跳转到第一张未标注图片 ({first_unlabeled + 1}/{len(self.image_files)})")

    def goto_next_unlabeled_image(self):
        """跳转到下一张未标注的图片"""
        unlabeled_indices = self.get_unlabeled_images()

        if not unlabeled_indices:
            QMessageBox.information(self, "信息", "所有图片都已标注完成！🎉")
            return

        # 查找当前位置之后的未标注图片
        next_unlabeled = None
        for index in unlabeled_indices:
            if index > self.current_image_index:
                next_unlabeled = index
                break

        # 如果没找到，从头开始
        if next_unlabeled is None:
            next_unlabeled = unlabeled_indices[0]
            if next_unlabeled == self.current_image_index:
                QMessageBox.information(self, "信息", "这是唯一一张未标注的图片！")
                return

        self.current_image_index = next_unlabeled
        self.load_current_image()
        self.update_ui_state()

        self.status_label.setText(f"已跳转到下一张未标注图片 ({next_unlabeled + 1}/{len(self.image_files)})")

    def goto_prev_unlabeled_image(self):
        """跳转到上一张未标注的图片"""
        unlabeled_indices = self.get_unlabeled_images()

        if not unlabeled_indices:
            QMessageBox.information(self, "信息", "所有图片都已标注完成！🎉")
            return

        # 查找当前位置之前的未标注图片
        prev_unlabeled = None
        for index in reversed(unlabeled_indices):
            if index < self.current_image_index:
                prev_unlabeled = index
                break

        # 如果没找到，从最后开始
        if prev_unlabeled is None:
            prev_unlabeled = unlabeled_indices[-1]
            if prev_unlabeled == self.current_image_index:
                QMessageBox.information(self, "信息", "这是唯一一张未标注的图片！")
                return

        self.current_image_index = prev_unlabeled
        self.load_current_image()
        self.update_ui_state()

        self.status_label.setText(f"已跳转到上一张未标注图片 ({prev_unlabeled + 1}/{len(self.image_files)})")

    def highlight_unlabeled_in_list(self):
        """在图片列表中高亮显示未标注的图片"""
        if not self.image_files:
            return

        unlabeled_indices = set(self.get_unlabeled_images())

        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if i in unlabeled_indices:
                # 在文件名前添加标记
                if not item.text().startswith("⚠️"):
                    filename = os.path.basename(self.image_files[i])
                    item.setText(f"⚠️ {filename}")
            else:
                # 移除警告标记
                if item.text().startswith("⚠️"):
                    filename = os.path.basename(self.image_files[i])
                    item.setText(f"✅ {filename}")
                elif not item.text().startswith("✅"):
                    filename = os.path.basename(self.image_files[i])
                    item.setText(f"✅ {filename}")

    def open_folder(self):
        """打开文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择包含图像的文件夹")
        if folder:
            self.current_folder = folder

            # 检查是否需要迁移现有标注
            if self.annotations_data.get("annotations"):
                old_root = self.annotations_data.get("image_root", "")
                if old_root and old_root != folder:
                    reply = QMessageBox.question(
                        self, "标注数据迁移",
                        f"检测到现有标注数据。\n\n"
                        f"旧根目录: {old_root}\n"
                        f"新根目录: {folder}\n\n"
                        f"是否要迁移标注数据到新目录？\n\n"
                        f"是: 迁移现有标注数据\n"
                        f"否: 清空标注数据重新开始",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.No:
                        self.annotations_data = load_annotations("")  # 加载默认空数据

            self.load_images_from_folder(folder)

    def load_images_from_folder(self, folder):
        """从文件夹加载图像"""
        self.status_label.setText("正在加载图像...")

        self.image_files = get_image_files(folder)

        if not self.image_files:
            QMessageBox.information(self, "信息", "所选文件夹中没有找到支持的图像文件。")
            self.status_label.setText("就绪")
            return

        # 更新标注数据的根路径
        self.annotations_data["image_root"] = folder

        # 更新图像列表
        self.image_list.clear()
        for image_path in self.image_files:
            filename = os.path.basename(image_path)
            self.image_list.addItem(filename)

        # 高亮显示未标注的图片
        self.highlight_unlabeled_in_list()

        self.current_image_index = 0
        self.load_current_image()
        self.update_ui_state()
        self.update_statistics()
        self.update_root_path_display()

        self.status_label.setText(f"已加载 {len(self.image_files)} 张图像")

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

                # 显示相对路径
                image_root = self.annotations_data.get("image_root", "")
                if image_root:
                    rel_path = get_relative_path(image_path, image_root)
                    self.current_path_label.setText(f"相对路径: {rel_path}")
                else:
                    self.current_path_label.setText(f"绝对路径: {image_path}")

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

    def update_current_annotation_display(self):
        """更新当前标注显示"""
        if 0 <= self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]
            image_root = self.annotations_data.get("image_root", "")

            # 获取相对路径作为键
            rel_path = get_relative_path(image_path, image_root) if image_root else image_path
            annotation = self.annotations_data.get('annotations', {}).get(rel_path, {})

            category = annotation.get('category', '未标注')
            self.current_category_label.setText(f"类别: {category}")

            # 根据标注状态设置样式
            if category == '未标注':
                self.current_category_label.setStyleSheet("font-weight: bold; color: #f44336;")
            else:
                self.current_category_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

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

    def on_category_selected(self, category_index, category_name):
        """类别选择事件"""
        if 0 <= self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]
            image_root = self.annotations_data.get("image_root", "")

            # 使用相对路径作为键
            rel_path = get_relative_path(image_path, image_root) if image_root else image_path

            # 更新标注数据
            if 'annotations' not in self.annotations_data:
                self.annotations_data['annotations'] = {}

            self.annotations_data['annotations'][rel_path] = {
                'category': category_name,
                'category_index': category_index,
                'timestamp': self.get_current_timestamp()
            }

            # 更新显示
            self.current_category_label.setText(f"类别: {category_name}")
            self.current_category_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

            # 更新图片列表中的标记
            self.highlight_unlabeled_in_list()

            # 更新统计
            self.update_statistics()
            self.update_progress()

            self.status_label.setText(f"已标注: {category_name}")

    def get_current_timestamp(self):
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()

    def update_mouse_status(self, text):
        """更新鼠标状态显示"""
        self.mouse_pos_label.setText(text)

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

    def select_category_by_index(self, index):
        """通过索引选择类别"""
        categories = self.category_manager.get_categories()
        if 0 <= index < len(categories):
            self.category_manager.select_category(index)

    def update_ui_state(self):
        """更新界面状态"""
        has_images = len(self.image_files) > 0
        unlabeled_count = len(self.get_unlabeled_images())

        self.prev_btn.setEnabled(has_images and self.current_image_index > 0)
        self.next_btn.setEnabled(has_images and self.current_image_index < len(self.image_files) - 1)

        # 更新快速定位按钮状态
        self.goto_first_btn.setEnabled(has_images and unlabeled_count > 0)
        self.goto_next_btn.setEnabled(has_images and unlabeled_count > 0)

    def update_progress(self):
        """更新进度"""
        if not self.image_files:
            self.progress_bar.setValue(0)
            self.progress_label.setText("0 / 0 (0.0%)")
            self.unlabeled_count_label.setText("未标注: 0 张")
            return

        image_root = self.annotations_data.get("image_root", "")
        annotations = self.annotations_data.get('annotations', {})

        # 计算当前文件夹的标注数量
        annotated_count = 0
        for image_path in self.image_files:
            rel_path = get_relative_path(image_path, image_root) if image_root else image_path
            if rel_path in annotations and annotations[rel_path].get('category'):
                annotated_count += 1

        total_count = len(self.image_files)
        unlabeled_count = total_count - annotated_count
        progress_percent = (annotated_count / total_count) * 100 if total_count > 0 else 0

        self.progress_bar.setMaximum(total_count)
        self.progress_bar.setValue(annotated_count)
        self.progress_label.setText(f"{annotated_count} / {total_count} ({progress_percent:.1f}%)")
        self.unlabeled_count_label.setText(f"未标注: {unlabeled_count} 张")

        # 更新按钮状态
        self.update_ui_state()

    def update_statistics(self):
        """更新统计信息"""
        if not self.image_files:
            self.stats_text.clear()
            return

        image_root = self.annotations_data.get("image_root", "")
        annotations = self.annotations_data.get('annotations', {})

        # 过滤出当前文件夹的标注
        current_annotations = {}
        for image_path in self.image_files:
            rel_path = get_relative_path(image_path, image_root) if image_root else image_path
            if rel_path in annotations:
                current_annotations[rel_path] = annotations[rel_path]

        stats, total = get_annotation_stats(current_annotations)
        unlabeled_count = len(self.image_files) - total

        stats_text = f"当前文件夹: {os.path.basename(self.current_folder) if self.current_folder else '未设置'}\n"
        stats_text += f"总图像数: {len(self.image_files)}\n"
        stats_text += f"已标注数: {total}\n"
        stats_text += f"未标注数: {unlabeled_count}\n"

        if unlabeled_count > 0:
            stats_text += f"完成度: {(total / len(self.image_files) * 100):.1f}%\n\n"
        else:
            stats_text += f"完成度: 100% 🎉\n\n"

        if stats:
            stats_text += "各类别统计:\n"
            for category, count in sorted(stats.items()):
                if category != '未标注':
                    percentage = (count / len(self.image_files)) * 100
                    stats_text += f"  {category}: {count} ({percentage:.1f}%)\n"

        # 显示标注格式版本
        format_version = self.annotations_data.get("format_version", "未知")
        stats_text += f"\n标注格式版本: {format_version}"

        self.stats_text.setText(stats_text)

        # 更新图片列表高亮
        self.highlight_unlabeled_in_list()

    def save_annotations(self):
        """保存标注"""
        # 更新类别列表
        self.annotations_data['categories'] = self.category_manager.get_categories()

        if save_annotations(Config.ANNOTATIONS_FILE, self.annotations_data, self.current_folder):
            self.status_label.setText("标注已保存")
            QMessageBox.information(self, "成功", "标注文件已保存！")
        else:
            QMessageBox.critical(self, "错误", "保存标注文件失败！")

    def auto_save(self):
        """自动保存"""
        if self.annotations_data.get('annotations'):
            self.annotations_data['categories'] = self.category_manager.get_categories()
            save_annotations(Config.ANNOTATIONS_FILE, self.annotations_data, self.current_folder)

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
            info_text += f"验证集: {result['val_images']} 张\n"

            if result.get('missing_files', 0) > 0:
                info_text += f"缺失文件: {result['missing_files']} 张\n"

            info_text += "\n各类别分布:\n"

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
        save_annotations(Config.ANNOTATIONS_FILE, self.annotations_data, self.current_folder)

        reply = QMessageBox.question(
            self, "确认退出", "确定要退出程序吗？标注数据已自动保存。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()