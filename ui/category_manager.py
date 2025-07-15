from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QListWidget, QLabel, QMessageBox, 
                             QInputDialog, QGroupBox)
from PyQt6.QtCore import pyqtSignal, Qt
from ui.styles import get_category_button_style

class CategoryManager(QWidget):
    """类别管理器"""
    
    category_selected = pyqtSignal(int, str)  # 发送选中的类别索引和名称
    
    def __init__(self):
        super().__init__()
        self.categories = []
        self.selected_category = -1
        self.category_buttons = []
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 类别管理组
        category_group = QGroupBox("类别管理")
        category_layout = QVBoxLayout()
        
        # 添加类别
        add_layout = QHBoxLayout()
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("输入新类别名称...")
        self.category_input.returnPressed.connect(self.add_category)
        
        add_btn = QPushButton("添加类别")
        add_btn.clicked.connect(self.add_category)
        
        add_layout.addWidget(self.category_input)
        add_layout.addWidget(add_btn)
        category_layout.addLayout(add_layout)
        
        # 类别列表和操作按钮
        list_layout = QHBoxLayout()
        
        # 类别列表
        self.category_list = QListWidget()
        self.category_list.itemDoubleClicked.connect(self.edit_category)
        list_layout.addWidget(self.category_list)
        
        # 操作按钮
        btn_layout = QVBoxLayout()
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_category)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_category)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_categories)
        
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        
        list_layout.addLayout(btn_layout)
        category_layout.addLayout(list_layout)
        
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # 快速选择组
        selection_group = QGroupBox("快速选择 (快捷键: 1-9,0)")
        self.selection_layout = QVBoxLayout()
        selection_group.setLayout(self.selection_layout)
        layout.addWidget(selection_group)
        
        # 当前选择
        self.selected_label = QLabel("当前选择: 无")
        self.selected_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        layout.addWidget(self.selected_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def add_category(self):
        """添加类别"""
        category_name = self.category_input.text().strip()
        if category_name and category_name not in self.categories:
            self.categories.append(category_name)
            self.category_list.addItem(category_name)
            self.category_input.clear()
            self.update_category_buttons()
        elif category_name in self.categories:
            QMessageBox.warning(self, "警告", "类别名称已存在！")
    
    def edit_category(self):
        """编辑类别"""
        current_item = self.category_list.currentItem()
        if current_item:
            current_index = self.category_list.currentRow()
            old_name = current_item.text()
            
            new_name, ok = QInputDialog.getText(
                self, "编辑类别", "新的类别名称:", text=old_name
            )
            
            if ok and new_name.strip() and new_name.strip() != old_name:
                if new_name.strip() not in self.categories:
                    self.categories[current_index] = new_name.strip()
                    current_item.setText(new_name.strip())
                    self.update_category_buttons()
                else:
                    QMessageBox.warning(self, "警告", "类别名称已存在！")
    
    def delete_category(self):
        """删除类别"""
        current_item = self.category_list.currentItem()
        if current_item:
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除类别 '{current_item.text()}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                current_index = self.category_list.currentRow()
                self.categories.pop(current_index)
                self.category_list.takeItem(current_index)
                
                # 重置选择
                if self.selected_category >= len(self.categories):
                    self.selected_category = -1
                
                self.update_category_buttons()
                self.update_selected_label()
    
    def clear_categories(self):
        """清空所有类别"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有类别吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.categories.clear()
            self.category_list.clear()
            self.selected_category = -1
            self.update_category_buttons()
            self.update_selected_label()
    
    def update_category_buttons(self):
        """更新类别按钮"""
        # 清除旧按钮
        for button in self.category_buttons:
            button.deleteLater()
        self.category_buttons.clear()
        
        # 创建新按钮
        rows = []
        current_row = QHBoxLayout()
        
        for i, category in enumerate(self.categories):
            button = QPushButton(f"{i+1}. {category}")
            button.clicked.connect(lambda checked, idx=i: self.select_category(idx))
            button.setStyleSheet(get_category_button_style(i == self.selected_category))
            
            self.category_buttons.append(button)
            current_row.addWidget(button)
            
            # 每行最多3个按钮
            if (i + 1) % 3 == 0 or i == len(self.categories) - 1:
                rows.append(current_row)
                current_row = QHBoxLayout()
        
        # 添加到布局
        for row in rows:
            self.selection_layout.addLayout(row)
    
    def select_category(self, index):
        """选择类别"""
        if 0 <= index < len(self.categories):
            old_selected = self.selected_category
            self.selected_category = index
            
            # 更新按钮样式
            if old_selected >= 0 and old_selected < len(self.category_buttons):
                self.category_buttons[old_selected].setStyleSheet(get_category_button_style(False))
            
            if index < len(self.category_buttons):
                self.category_buttons[index].setStyleSheet(get_category_button_style(True))
            
            self.update_selected_label()
            self.category_selected.emit(index, self.categories[index])
    
    def update_selected_label(self):
        """更新选择标签"""
        if self.selected_category >= 0:
            category_name = self.categories[self.selected_category]
            self.selected_label.setText(f"当前选择: {category_name}")
        else:
            self.selected_label.setText("当前选择: 无")
    
    def set_categories(self, categories):
        """设置类别列表"""
        self.categories = categories.copy()
        self.category_list.clear()
        for category in self.categories:
            self.category_list.addItem(category)
        self.selected_category = -1
        self.update_category_buttons()
        self.update_selected_label()
    
    def get_categories(self):
        """获取类别列表"""
        return self.categories.copy()
    
    def get_selected_category(self):
        """获取当前选中的类别"""
        if self.selected_category >= 0:
            return self.selected_category, self.categories[self.selected_category]
        return -1, None