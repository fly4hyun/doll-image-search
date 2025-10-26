###################################################################################################
###################################################################################################

import os
import json

from collections import OrderedDict

import pandas as pd
import copy

from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt

###################################################################################################
###################################################################################################

def clean_dict(d):
    cleaned = {}
    for key, value in d.items():
        if isinstance(value, str):
            cleaned[key] = value.strip()
        else:
            cleaned[key] = str(value)
    return cleaned

###################################################################################################
###################################################################################################

pd.set_option('future.no_silent_downcasting', True)

###################################################################################################
###################################################################################################

def open_json(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("{}")
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=str)

###################################################################################################
###################################################################################################

def doll_detail_json_gen(category_name, target_file):
    category_mapping = {1: '원자재', 2: '부자재', 3: '충진자재'}
    
    base_path = os.path.dirname(target_file.replace(category_name, 'doll_detail_category'))
    box_label_path = os.path.dirname(target_file.replace(category_name, 'BoxClass'))
    json_file_path = os.path.join(base_path, 'doll_category.json')
    json_box_label_file_path = os.path.join(box_label_path, 'classes.json')
    if not os.path.exists(json_file_path):
        with open(json_file_path, "w", encoding="utf-8") as f:
            f.write("{}")
    
    box_label_dict = {}
    
    data = open_json(json_file_path)
    # 강제 OrderedDict를 사용하여 순서를 보장
    data["doll_category"] = OrderedDict([
        ("product", data.get("doll_category", {}).get("product", {})),
        ("header", data.get("doll_category", {}).get("header", {})),
        ("원자재", {}),
        ("부자재", {}),
        ("충진자재", {})
    ])
    
    df_data = pd.read_excel(target_file, engine='openpyxl', dtype=object)
    df_data.fillna('', inplace=True)
    df_data = df_data.infer_objects()
    
    for idx in range(len(df_data)):
        category_num = df_data.loc[idx, 'Category']
        part_name = df_data.loc[idx, 'PartName']
        detail_info = df_data.iloc[idx].to_dict()
        detail_info = clean_dict(detail_info)
        
        cat_key = category_mapping.get(category_num)
        if not cat_key:
            continue
        
        if part_name in data["doll_category"][cat_key]:
            data["doll_category"][cat_key][part_name].append(detail_info)
        else:
            data["doll_category"][cat_key][part_name] = [detail_info]

    PartName_list = []
    for PartName in list(data["doll_category"]["원자재"].keys()):
        PartName_list.append('1_' + PartName)
        box_label_dict["원자재"] = PartName_list
    PartName_list = []
    for PartName in list(data["doll_category"]["부자재"].keys()):
        PartName_list.append('1_' + PartName)
        box_label_dict["부자재"] = PartName_list
        
    save_json(box_label_dict, json_box_label_file_path)
    save_json(data, json_file_path)

###################################################################################################
###################################################################################################

def doll_header_json_gen(category_name, target_file):
    base_path = os.path.dirname(target_file.replace(category_name, 'doll_detail_category'))
    json_file_path = os.path.join(base_path, 'doll_category.json')
    if not os.path.exists(json_file_path):
        with open(json_file_path, "w", encoding="utf-8") as f:
            f.write("{}")
    
    data = open_json(json_file_path)
    data["doll_category"] = OrderedDict([
        ("product", data.get("doll_category", {}).get("product", {})),
        ("header", {}),
        ("원자재", data.get("doll_category", {}).get("원자재", {})),
        ("부자재", data.get("doll_category", {}).get("부자재", {})),
        ("충진자재", data.get("doll_category", {}).get("충진자재", {}))
    ])
    
    df_data = pd.read_excel(target_file, engine='openpyxl', dtype=object)
    df_data.fillna('', inplace=True)
    df_data = df_data.infer_objects()

    detail_info = df_data.iloc[0].to_dict()
    detail_info = clean_dict(detail_info)
    
    data["doll_category"]["header"] = copy.deepcopy(detail_info)
    
    save_json(data, json_file_path)

###################################################################################################
###################################################################################################

def doll_product_json_gen(category_name, target_file):
    base_path = os.path.dirname(target_file.replace(category_name, 'doll_detail_category'))
    json_file_path = os.path.join(base_path, 'doll_category.json')
    if not os.path.exists(json_file_path):
        with open(json_file_path, "w", encoding="utf-8") as f:
            f.write("{}")
    
    data = open_json(json_file_path)
    data["doll_category"] = OrderedDict([
        ("product", {}),
        ("header", data.get("doll_category", {}).get("header", {})),
        ("원자재", data.get("doll_category", {}).get("원자재", {})),
        ("부자재", data.get("doll_category", {}).get("부자재", {})),
        ("충진자재", data.get("doll_category", {}).get("충진자재", {}))
    ])
    
    df_data = pd.read_excel(target_file, engine='openpyxl', dtype=object)
    df_data.fillna('', inplace=True)
    df_data = df_data.infer_objects()
    
    detail_info = df_data.iloc[0].to_dict()
    detail_info = clean_dict(detail_info)
    
    data["doll_category"]["product"] = detail_info
    
    save_json(data, json_file_path)

###################################################################################################
###################################################################################################

def ensure_doll_category_json_exists(data_folder, doll_id):
    json_path = os.path.join(data_folder, 'doll_detail_category', doll_id, 'doll_category.json')
    folder = os.path.dirname(json_path)
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    if not os.path.exists(json_path):
        with open(json_path, "w", encoding="utf-8") as f:
            f.write("{}")
            
###################################################################################################
###################################################################################################
            
def populate_tree_from_doll_detail(tree_widget, data, parent_item=None):
    if parent_item is None:
        tree_widget.clear()
        for key, value in data.items():
            if isinstance(value, dict) or isinstance(value, list):
                item = QTreeWidgetItem(tree_widget, [str(key), ""])
            else:
                item = QTreeWidgetItem(tree_widget, [str(key), str(value)])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(0, Qt.UserRole, value)
            if isinstance(value, dict):
                populate_tree_from_doll_detail(tree_widget, value, item)
            elif isinstance(value, list):
                if len(value) == 0:
                    child = QTreeWidgetItem(item, ["(빈 리스트)", ""])
                    child.setFlags(child.flags() | Qt.ItemIsEditable)
                    child.setData(0, Qt.UserRole, "")
                else:
                    for idx, element in enumerate(value):
                        if isinstance(element, dict):
                            child = QTreeWidgetItem(item, [f"{idx+1}.", ""])
                            child.setFlags(child.flags() | Qt.ItemIsEditable)
                            child.setData(0, Qt.UserRole, element)
                            populate_tree_from_doll_detail(tree_widget, element, child)
                        else:
                            child = QTreeWidgetItem(item, [f"{idx+1}.", str(element)])
                            child.setFlags(child.flags() | Qt.ItemIsEditable)
                            child.setData(0, Qt.UserRole, element)
    else:
        for key, value in data.items():
            if isinstance(value, dict) or isinstance(value, list):
                item = QTreeWidgetItem(parent_item, [str(key), ""])
            else:
                item = QTreeWidgetItem(parent_item, [str(key), str(value)])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(0, Qt.UserRole, value)
            if isinstance(value, dict):
                populate_tree_from_doll_detail(tree_widget, value, item)
            elif isinstance(value, list):
                if len(value) == 0:
                    child = QTreeWidgetItem(item, ["(빈 리스트)", ""])
                    child.setFlags(child.flags() | Qt.ItemIsEditable)
                    child.setData(0, Qt.UserRole, "")
                else:
                    for idx, element in enumerate(value):
                        if isinstance(element, dict):
                            child = QTreeWidgetItem(item, [f"{idx+1}.", ""])
                            child.setFlags(child.flags() | Qt.ItemIsEditable)
                            child.setData(0, Qt.UserRole, element)
                            populate_tree_from_doll_detail(tree_widget, element, child)
                        else:
                            child = QTreeWidgetItem(item, [f"{idx+1}.", str(element)])
                            child.setFlags(child.flags() | Qt.ItemIsEditable)
                            child.setData(0, Qt.UserRole, element)
                            
###################################################################################################
###################################################################################################