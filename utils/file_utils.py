import os
import json
from config import Config

def get_image_files(folder_path):
    """获取文件夹中的所有图像文件"""
    image_files = []
    
    if not os.path.exists(folder_path):
        return image_files
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in Config.SUPPORTED_FORMATS):
                image_files.append(os.path.join(root, file))
    
    return sorted(image_files)

def load_annotations(file_path):
    """加载标注数据"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载标注文件失败: {e}")
    
    return {
        "categories": Config.DEFAULT_CATEGORIES.copy(),
        "annotations": {},
        "version": "1.0"
    }

def save_annotations(file_path, data):
    """保存标注数据"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存标注文件失败: {e}")
        return False

def get_annotation_stats(annotations):
    """获取标注统计信息"""
    stats = {}
    total = len(annotations)
    
    for image_path, annotation in annotations.items():
        category = annotation.get('category', '未标注')
        stats[category] = stats.get(category, 0) + 1
    
    return stats, total