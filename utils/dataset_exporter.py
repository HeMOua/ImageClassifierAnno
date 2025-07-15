import os
import shutil
import json
from pathlib import Path
import random
from config import Config

class DatasetExporter:
    """数据集导出器"""
    
    def __init__(self):
        self.train_ratio = Config.TRAIN_RATIO
        self.val_ratio = Config.VAL_RATIO
    
    def export_dataset(self, annotations_data, output_dir, copy_images=True):
        """导出数据集"""
        try:
            # 创建输出目录结构
            output_path = Path(output_dir)
            train_dir = output_path / "train"
            val_dir = output_path / "val"
            
            # 清空并创建目录
            if output_path.exists():
                shutil.rmtree(output_path)
            
            output_path.mkdir(parents=True, exist_ok=True)
            train_dir.mkdir(exist_ok=True)
            val_dir.mkdir(exist_ok=True)
            
            categories = annotations_data.get("categories", [])
            annotations = annotations_data.get("annotations", {})
            
            # 为每个类别创建子目录
            for category in categories:
                (train_dir / category).mkdir(exist_ok=True)
                (val_dir / category).mkdir(exist_ok=True)
            
            # 按类别分组图像
            categorized_images = {}
            for image_path, annotation in annotations.items():
                if annotation.get('category') and annotation['category'] in categories:
                    category = annotation['category']
                    if category not in categorized_images:
                        categorized_images[category] = []
                    categorized_images[category].append(image_path)
            
            # 统计信息
            total_images = 0
            train_count = 0
            val_count = 0
            category_stats = {}
            
            # 为每个类别分割数据
            for category, image_paths in categorized_images.items():
                random.shuffle(image_paths)  # 随机打乱
                
                num_images = len(image_paths)
                num_train = int(num_images * self.train_ratio)
                
                train_images = image_paths[:num_train]
                val_images = image_paths[num_train:]
                
                # 复制训练集图像
                for image_path in train_images:
                    if os.path.exists(image_path):
                        dest_path = train_dir / category / os.path.basename(image_path)
                        if copy_images:
                            shutil.copy2(image_path, dest_path)
                        train_count += 1
                
                # 复制验证集图像
                for image_path in val_images:
                    if os.path.exists(image_path):
                        dest_path = val_dir / category / os.path.basename(image_path)
                        if copy_images:
                            shutil.copy2(image_path, dest_path)
                        val_count += 1
                
                category_stats[category] = {
                    'total': num_images,
                    'train': len(train_images),
                    'val': len(val_images)
                }
                total_images += num_images
            
            # 生成数据集信息文件
            dataset_info = {
                'name': 'Exported Dataset',
                'categories': categories,
                'num_classes': len(categories),
                'total_images': total_images,
                'train_images': train_count,
                'val_images': val_count,
                'split_ratio': {
                    'train': self.train_ratio,
                    'val': self.val_ratio
                },
                'category_stats': category_stats,
                'export_settings': {
                    'copy_images': copy_images,
                    'source_annotations': len(annotations)
                }
            }
            
            # 保存数据集信息
            with open(output_path / "dataset_info.json", 'w', encoding='utf-8') as f:
                json.dump(dataset_info, f, ensure_ascii=False, indent=2)
            
            # 创建类别索引文件
            class_indices = {category: idx for idx, category in enumerate(categories)}
            with open(output_path / "class_indices.json", 'w', encoding='utf-8') as f:
                json.dump(class_indices, f, ensure_ascii=False, indent=2)
            
            return True, dataset_info
            
        except Exception as e:
            print(f"导出数据集失败: {e}")
            return False, str(e)
    
    def export_annotations_only(self, annotations_data, output_file):
        """仅导出标注文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(annotations_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出标注文件失败: {e}")
            return False