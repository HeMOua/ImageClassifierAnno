import os

class Config:
    # 应用配置
    APP_NAME = "图像分类标注工具"
    VERSION = "1.0.0"
    
    # 界面配置
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    
    # 支持的图像格式
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    # 默认类别
    DEFAULT_CATEGORIES = [
        "类别1",
        "类别2", 
        "类别3",
        "类别4",
        "类别5"
    ]
    
    # 文件路径
    ANNOTATIONS_FILE = "data/annotations.json"
    
    # 导出配置
    TRAIN_RATIO = 0.8  # 训练集比例
    VAL_RATIO = 0.2    # 验证集比例
    
    # 快捷键
    SHORTCUTS = {
        '1': 0,  # 数字键1对应第1个类别
        '2': 1,  # 数字键2对应第2个类别
        '3': 2,
        '4': 3,
        '5': 4,
        '6': 5,
        '7': 6,
        '8': 7,
        '9': 8,
        '0': 9
    }