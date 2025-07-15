def get_main_style():
    """主窗口样式"""
    return """
    QMainWindow {
        background-color: #f5f5f5;
    }
    
    QToolBar {
        background-color: #ffffff;
        border: 1px solid #ddd;
        spacing: 5px;
        padding: 5px;
    }
    
    QPushButton {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
        font-weight: bold;
    }
    
    QPushButton:hover {
        background-color: #45a049;
    }
    
    QPushButton:pressed {
        background-color: #3d8b40;
    }
    
    QPushButton:disabled {
        background-color: #cccccc;
        color: #666666;
    }
    
    QListWidget {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 5px;
        font-size: 14px;
    }
    
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #eee;
    }
    
    QListWidget::item:selected {
        background-color: #e3f2fd;
        color: #1976d2;
    }
    
    QListWidget::item:hover {
        background-color: #f5f5f5;
    }
    
    QLabel {
        font-size: 14px;
        color: #333;
    }
    
    QLineEdit {
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
    }
    
    QProgressBar {
        border: 1px solid #ddd;
        border-radius: 4px;
        text-align: center;
        font-weight: bold;
    }
    
    QProgressBar::chunk {
        background-color: #4CAF50;
        border-radius: 3px;
    }
    
    QGroupBox {
        font-weight: bold;
        border: 2px solid #ddd;
        border-radius: 4px;
        margin-top: 10px;
        padding-top: 10px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }
    """

def get_category_button_style(selected=False):
    """类别按钮样式"""
    if selected:
        return """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: 2px solid #1976D2;
            padding: 10px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
        }
        """
    else:
        return """
        QPushButton {
            background-color: #f8f9fa;
            color: #333;
            border: 2px solid #dee2e6;
            padding: 10px;
            border-radius: 6px;
            font-size: 14px;
        }
        
        QPushButton:hover {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }
        """