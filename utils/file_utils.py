import os
import json
from pathlib import Path
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


def get_relative_path(file_path, base_path):
    """获取相对于基础路径的相对路径"""
    try:
        return os.path.relpath(file_path, base_path)
    except ValueError:
        # 如果在不同驱动器上（Windows），返回绝对路径
        return file_path


def get_absolute_path(relative_path, base_path):
    """根据相对路径和基础路径获取绝对路径"""
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(base_path, relative_path)


def load_annotations(file_path):
    """加载标注数据"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查版本并处理兼容性
            if "format_version" not in data:
                # 旧版本格式，需要转换
                print("检测到旧版本标注文件，正在升级格式...")
                data = upgrade_annotation_format(data)

            return data

        except Exception as e:
            print(f"加载标注文件失败: {e}")

    # 返回默认格式
    return {
        "format_version": Config.ANNOTATION_FORMAT_VERSION,
        "categories": Config.DEFAULT_CATEGORIES.copy(),
        "image_root": "",
        "annotations": {},
        "metadata": {
            "created_time": "",
            "last_modified": "",
            "total_images": 0,
            "annotated_images": 0
        }
    }


def upgrade_annotation_format(old_data):
    """将旧版本标注格式升级到新版本"""
    new_data = {
        "format_version": Config.ANNOTATION_FORMAT_VERSION,
        "categories": old_data.get("categories", Config.DEFAULT_CATEGORIES.copy()),
        "image_root": "",
        "annotations": {},
        "metadata": {
            "created_time": old_data.get("created_time", ""),
            "last_modified": "",
            "total_images": 0,
            "annotated_images": 0
        }
    }

    # 转换旧的标注数据
    old_annotations = old_data.get("annotations", {})
    if old_annotations:
        # 尝试推断公共根路径
        image_paths = list(old_annotations.keys())
        if image_paths:
            common_root = os.path.commonpath(image_paths)
            new_data["image_root"] = common_root

            # 转换为相对路径
            for abs_path, annotation in old_annotations.items():
                rel_path = get_relative_path(abs_path, common_root)
                new_data["annotations"][rel_path] = annotation

    return new_data


def save_annotations(file_path, data, image_root=None):
    """保存标注数据"""
    try:
        # 更新元数据
        import datetime
        now = datetime.datetime.now().isoformat()

        if "metadata" not in data:
            data["metadata"] = {}

        data["metadata"]["last_modified"] = now
        if not data["metadata"].get("created_time"):
            data["metadata"]["created_time"] = now

        # 更新统计信息
        annotations = data.get("annotations", {})
        data["metadata"]["total_images"] = len(annotations)
        data["metadata"]["annotated_images"] = len([a for a in annotations.values() if a.get("category")])

        # 更新格式版本
        data["format_version"] = Config.ANNOTATION_FORMAT_VERSION

        # 更新图片根路径
        if image_root:
            data["image_root"] = image_root

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


def migrate_annotations_to_new_folder(annotations_data, old_root, new_root):
    """迁移标注数据到新文件夹"""
    if not annotations_data.get("annotations"):
        return annotations_data

    # 更新图片根路径
    annotations_data["image_root"] = new_root

    # 检查并更新不存在的图片路径
    updated_annotations = {}
    missing_files = []

    for rel_path, annotation in annotations_data["annotations"].items():
        old_abs_path = get_absolute_path(rel_path, old_root)
        new_abs_path = get_absolute_path(rel_path, new_root)

        if os.path.exists(new_abs_path):
            # 图片存在于新位置
            updated_annotations[rel_path] = annotation
        elif os.path.exists(old_abs_path):
            # 图片仍在旧位置，需要用户手动移动
            missing_files.append((rel_path, old_abs_path, new_abs_path))
            updated_annotations[rel_path] = annotation
        else:
            # 图片完全找不到
            missing_files.append((rel_path, "不存在", new_abs_path))

    annotations_data["annotations"] = updated_annotations

    return annotations_data, missing_files


def validate_image_paths(annotations_data):
    """验证图片路径的有效性"""
    image_root = annotations_data.get("image_root", "")
    annotations = annotations_data.get("annotations", {})

    valid_images = []
    missing_images = []

    for rel_path, annotation in annotations.items():
        abs_path = get_absolute_path(rel_path, image_root)
        if os.path.exists(abs_path):
            valid_images.append((rel_path, abs_path))
        else:
            missing_images.append((rel_path, abs_path))

    return valid_images, missing_images