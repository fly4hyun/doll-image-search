###################################################################################################
###################################################################################################

import yaml
import os

from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt

###################################################################################################
###################################################################################################


def open_yaml(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return data





###################################################################################################

def category_folder_check(data_folder, category_yaml_path):
    category_list = open_yaml(category_yaml_path)
    
    if not os.path.isdir(data_folder):
        os.makedirs(data_folder)
    
    for category_name in category_list['category_list']:
        if not os.path.isdir(os.path.join(data_folder, category_name)):
            os.makedirs(os.path.join(data_folder, category_name))

###################################################################################################




def load_dolls_from_yaml(file_path):
    data = open_yaml(file_path)
    # 'dolls' 키가 없으면 빈 사전을 기본값으로 설정
    if data is None:
        data = {'dolls': {}}
        save_dolls_to_yaml(data, file_path)  # 전체 data를 저장하는 방식으로 변경
    if 'dolls' not in data:
        data['dolls'] = {}
        # 파일에 빈 'dolls' 사전을 저장하여 구조를 업데이트
        save_dolls_to_yaml(data, file_path)  # 전체 data를 저장하는 방식으로 변경
    return data


        
        
def save_dolls_to_yaml(dolls, file_path):
    
    # 변경된 전체 데이터를 다시 파일에 쓰기
    with open(file_path, 'w', encoding='utf-8') as file:
        yaml.safe_dump(dolls, file, allow_unicode=True)





def doll_list_remapping(data_folder, doll_list_path):
    
    doll_list = load_dolls_from_yaml(doll_list_path)
    
    def find_name_by_id(doll_list, doll_id):
        for doll in doll_list['dolls'].values():
            if doll['id'] == doll_id:
                return doll['name']
        return None  # ID가 목록에 없을 경우

    doll_dir = os.path.join(data_folder, 'dolls')
    doll_id_list = [os.path.splitext(f)[0] for f in os.listdir(doll_dir)]
    doll_list_temp = {'dolls': {}}
    for doll_id in doll_id_list:
        name = find_name_by_id(doll_list, doll_id)
        if name:
            doll_list_temp['dolls'][name] = {'name': name, 'id': doll_id}
        else:
            name = 'temp_' + doll_id
            doll_list_temp['dolls'][name] = {'name': name, 'id': doll_id}
            
    save_dolls_to_yaml(doll_list_temp, doll_list_path)
        
###################################################################################################

def check_detail_category(file_path, detail_category_list):
    
    if os.path.isfile(file_path):
        data = open_yaml(file_path)
        
        #### doll_category:
        ######## detail_category_list['detail_category_list'][0]: ....
        
        if data is None:
            data = {'doll_category': {}}
            for detail_category_name in detail_category_list['detail_category_list']:
                data['doll_category'][detail_category_name] = {}
            save_dolls_to_yaml(data, file_path)
        elif 'doll_category' not in data:
            data['doll_category'] = {}
            for detail_category_name in detail_category_list['detail_category_list']:
                data['doll_category'][detail_category_name] = {}
            save_dolls_to_yaml(data, file_path)
        else:
            for detail_category_name in detail_category_list['detail_category_list']:
                if detail_category_name not in data['doll_category']:
                    data['doll_category'][detail_category_name] = {}
            save_dolls_to_yaml(data, file_path)
    else:
        data = {'doll_category': {}}
        for detail_category_name in detail_category_list['detail_category_list']:
            data['doll_category'][detail_category_name] = {}
        save_dolls_to_yaml(data, file_path)

###################################################################################################

def doll_data_remapping(data_folder, doll_id, category_list, detail_category_list):
    doll_data = {'data': {}}
    for category_name in category_list['category_list']:
        if category_name == 'dolls':
            continue
        
        data_path = os.path.join(data_folder, category_name, doll_id)
        if not os.path.isdir(data_path):
            os.makedirs(data_path)
        if category_name == 'doll_detail_category':
            check_detail_category(os.path.join(data_path, 'doll_category.yaml'), detail_category_list)

        file_list = os.listdir(os.path.join(data_folder, category_name, doll_id))
        doll_data['data'][category_name] = file_list
        
    save_dolls_to_yaml(doll_data, os.path.join(data_folder, 'dolls', doll_id + '.yaml'))

###################################################################################################


def populate_tree_from_data(tree_widget, data, data_id, parent_item=None):
    """
    data: dictionary 형태의 YAML 데이터
    data_id: 데이터의 고유 식별자 등 (경로 구성에 사용)
    parent_item: None이면 tree_widget의 루트에 추가, 있으면 해당 아이템 아래에 추가
    """
    if parent_item is None:
        tree_widget.clear()  # 초기화
        for key, value in data.items():
            # 최상위 항목 생성 (예: 'data'라는 키)
            item = QTreeWidgetItem(tree_widget, [str(key)])
            # 예시로, 해당 항목의 첫 번째 열 데이터에 key 값을 저장
            item.setData(0, Qt.UserRole, {'path': str(key), 'id': data_id})
            if isinstance(value, dict) and value:
                populate_tree_from_data(tree_widget, value, data_id, item)
            elif isinstance(value, list) and value:
                # 리스트인 경우, 부모 항목은 key만 표시하고, 자식 항목으로 각 리스트 요소를 추가
                for elem in value:
                    child = QTreeWidgetItem(item, ["", str(elem)])
                    child.setData(0, Qt.UserRole, {'path': os.path.join(str(key), str(elem)), 'id': data_id})
            else:
                # 일반적인 값은 두 번째 열에 문자열로 설정
                item.setText(1, str(value))
    else:
        for key, value in data.items():
            parent_folder_path = parent_item.data(0, Qt.UserRole)['path']
            if data_id in parent_folder_path:
                folder_path = os.path.join(parent_folder_path, str(key))
            else:
                folder_path = os.path.join(parent_folder_path, str(key), data_id)
            
            if isinstance(value, dict) and value:
                item = QTreeWidgetItem(parent_item, [str(key)])
                item.setData(0, Qt.UserRole, {'path': folder_path, 'id': data_id})
                populate_tree_from_data(tree_widget, value, data_id, item)
            elif isinstance(value, list) and value:
                # 부모 항목 생성
                list_parent = QTreeWidgetItem(parent_item, [str(key)])
                list_parent.setData(0, Qt.UserRole, {'path': folder_path, 'id': data_id})
                # 리스트의 각 요소를 자식 항목으로 추가
                for elem in value:
                    child = QTreeWidgetItem(list_parent, ["", str(elem)])
                    child.setData(0, Qt.UserRole, {'path': os.path.join(folder_path, str(elem)), 'id': data_id})
            else:
                item = QTreeWidgetItem(parent_item, [str(key), str(value)])
                item.setData(0, Qt.UserRole, {'path': folder_path, 'id': data_id})
    
###################################################################################################


from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt

# def populate_tree_from_doll_detail(tree_widget, data):
#     # 데이터 구조에 따라 트리를 구성합니다.
#     first = True  # 첫 번째 노드 여부
#     for key, value in data.items():
#         # key가 None이면 건너뜁니다.
#         if key is None:
#             continue
#         parent_item = QTreeWidgetItem(tree_widget, [str(key)])
#         if first:
#             # 최상위 노드(첫 번째 노드)는 편집 비활성화
#             parent_item.setFlags(parent_item.flags() & ~Qt.ItemIsEditable)
#             first = False
#         else:
#             parent_item.setFlags(parent_item.flags() | Qt.ItemIsEditable)
#         process_value(parent_item, value)

# def process_value(parent_item, value):
#     if isinstance(value, dict):
#         # 값이 사전형일 때
#         for subkey, subvalue in value.items():
#             if subkey is None:
#                 subkey = "None"
#             child_item = QTreeWidgetItem(parent_item, [str(subkey)])
#             child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)
#             process_value(child_item, subvalue)
#     elif isinstance(value, list):
#         # 값이 리스트일 때
#         for item in value:
#             if isinstance(item, dict):
#                 # 리스트 내 아이템이 사전형일 때
#                 for key, val in item.items():
#                     list_item = QTreeWidgetItem(parent_item, [f"{key}: {val}"])
#                     list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
#                     if isinstance(val, list):
#                         # 리스트 내에 또 다른 리스트가 있는 경우
#                         add_sub_items(list_item, val)
#             else:
#                 list_item = QTreeWidgetItem(parent_item, [str(item)])
#                 list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
#     else:
#         # 단순 값 처리
#         item = QTreeWidgetItem(parent_item, [str(value)])
#         item.setFlags(item.flags() | Qt.ItemIsEditable)


# 두 열로 구성된 트리로 디테일 데이터를 표시하는 함수
def populate_tree_from_doll_detail(tree_widget, data, parent_item=None):
    """
    data를 2열 형태(QTreeWidgetItem[0]: 키, [1]: 값)로 변환하여 트리에 추가합니다.
    만약 value가 dict이고 비어있지 않다면, 값 열은 빈 문자열로 표시합니다.
    """
    if parent_item is None:
        tree_widget.clear()
        for key, value in data.items():
            if isinstance(value, dict) and value:
                item = QTreeWidgetItem(tree_widget, [str(key), ""])
            else:
                item = QTreeWidgetItem(tree_widget, [str(key), str(value)])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            if isinstance(value, dict) and value:
                populate_tree_from_doll_detail(tree_widget, value, item)
    else:
        for key, value in data.items():
            if isinstance(value, dict) and value:
                item = QTreeWidgetItem(parent_item, [str(key), ""])
            else:
                item = QTreeWidgetItem(parent_item, [str(key), str(value)])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            if isinstance(value, dict) and value:
                populate_tree_from_doll_detail(tree_widget, value, item)

def process_value(parent_item, value):
    # 값이 None이면 아무것도 추가하지 않습니다.
    if value is None:
        return
    if isinstance(value, dict):
        for subkey, subvalue in value.items():
            if subkey is None:
                continue
            child_item = QTreeWidgetItem(parent_item, [str(subkey)])
            if parent_item.parent() is None:
                child_item.setFlags(child_item.flags() & ~Qt.ItemIsEditable)
            else:
                child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)
            process_value(child_item, subvalue)
    elif isinstance(value, list):
        for item in value:
            # 만약 리스트 내 항목이 None이면 건너뜁니다.
            if item is None:
                continue
            if isinstance(item, dict):
                for key, val in item.items():
                    # key와 val을 분리해서 표시; val이 None이면 아무것도 추가하지 않습니다.
                    list_item = QTreeWidgetItem(parent_item, [f"{str(key)}: {'' if val is None else str(val)}"])
                    list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
                    # 만약 val이 None이면 자식 아이템을 생성하지 않습니다.
                    if val is not None and isinstance(val, list):
                        add_sub_items(list_item, val)
                    if val is None or not isinstance(val, (dict, list)):
                        list_item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
            else:
                list_item = QTreeWidgetItem(parent_item, [str(item)])
                list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
                list_item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
    else:
        # 단순 값 처리: 만약 value가 None이면 빈 아이템을 추가하지 않습니다.
        item = QTreeWidgetItem(parent_item, [str(value)])
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)

def add_sub_items(list_item, lst):
    for element in lst:
        if element is None:
            continue
        child = QTreeWidgetItem(list_item, [str(element) if element is not None else ""])
        child.setFlags(child.flags() | Qt.ItemIsEditable)





def add_sub_items(parent_item, items):
    for sub_item in items:
        if isinstance(sub_item, dict):
            for key, val in sub_item.items():
                child_item = QTreeWidgetItem(parent_item, [f"{key}: {str(val)}"])
                child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)
        else:
            child_item = QTreeWidgetItem(parent_item, [str(sub_item)])
            child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)






###################################################################################################


def get_unique_key(parent, base_key):
    """
    부모 노드의 자식들 중에서 base_key와 중복되지 않는 유일한 키를 반환합니다.
    공백 없이 base_key 뒤에 숫자를 붙입니다.
    """
    keys = set()
    for i in range(parent.childCount()):
        child = parent.child(i)
        keys.add(child.text(0))
    unique_key = base_key
    counter = 1
    while unique_key in keys:
        unique_key = f"{base_key}{counter}"
        counter += 1
    return unique_key


###################################################################################################
###################################################################################################