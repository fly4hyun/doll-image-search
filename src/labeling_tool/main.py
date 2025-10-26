import sys
import os
import shutil
import argparse


from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox,
                             QPushButton, QLabel, QVBoxLayout, QWidget, 
                             QSplitter, QListWidget, QHBoxLayout, 
                             QGraphicsScene, QGraphicsView, QComboBox, QTableWidget, 
                             QInputDialog, QTreeWidget, QTreeWidgetItem, QScrollArea, 
                             QDialog, QDialogButtonBox, QLineEdit, QStyledItemDelegate, 
                             QCheckBox, QTableWidgetItem)
from PyQt5.QtGui import QPainter, QPixmap, QTransform, QColor, QPen
from PyQt5.QtCore import Qt, QRectF, QEvent
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsTextItem  # 추가된 부분

from utils.utils_yaml import *
from utils.utils_math import *
from utils.utils_json import *   # 여기에는 open_json, save_json 등 JSON 전용 함수들이 있음

###################################################################################################
###################################################################################################

def parse_opt():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--category_list', type=str, default='yaml/category_list.yaml')
    parser.add_argument('--detail_category_list', type=str, default='yaml/detail_category_list.yaml')
    parser.add_argument('--doll_list', type=str, default='yaml/doll_list.yaml')
    
    ### data 폴더 경로
    parser.add_argument('--data_folder', type=str, default='data')
    
    opt = parser.parse_args()
    return opt

# 새로 추가: 고유 키를 생성하는 함수
def get_uniqueKey(parent_item, key_prefix):
    # 부모 항목이나 기타 정보를 고려하지 않고 접두어 뒤에 6자리 UUID 값을 붙여 반환합니다.
    return f"{key_prefix}_{uuid.uuid4().hex[:6]}"
###################################################################################################
###################################################################################################

# =====================================================================
# 수정: doll_detail_json_gen
# JSON 파일이 없으면 자동 생성하고, 최상위가 "doll_category"이며
# 하위 키가 반드시 아래 순서대로 ("product", "header", "원자재", "부자재", "충진자재") 나오도록 함.
# =====================================================================

# =====================================================================
# 수정: doll_header_json_gen
# =====================================================================

# =====================================================================
# 수정: doll_product_json_gen
# =====================================================================

###################################################################################################
###################################################################################################

def tree_to_dict(self, item):
    result = {}
    for i in range(item.childCount()):
        child = item.child(i)
        if child.childCount() > 0:
            result[child.text(0)] = self.tree_to_dict(child)
        else:
            result[child.text(0)] = child.text(1)
    return result

def get_expanded_paths(tree_widget):
    expanded = []
    def recurse(item, path):
        if item.isExpanded():
            expanded.append(path)
        for i in range(item.childCount()):
            child = item.child(i)
            recurse(child, path + [child.text(0)])
    for i in range(tree_widget.topLevelItemCount()):
        top = tree_widget.topLevelItem(i)
        recurse(top, [top.text(0)])
    return expanded

def restore_expanded_paths(tree_widget, expanded_paths):
    def recurse(item, path):
        if path in expanded_paths:
            item.setExpanded(True)
        for i in range(item.childCount()):
            child = item.child(i)
            recurse(child, path + [child.text(0)])
    for i in range(tree_widget.topLevelItemCount()):
        top = tree_widget.topLevelItem(i)
        recurse(top, [top.text(0)])

from PyQt5.QtWidgets import QStyledItemDelegate
class NoEditDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 0:
            return None
        return super().createEditor(parent, option, index)

class DIDatabaseManagementWindow(QMainWindow):
    def __init__(self, opt):
        super().__init__()
        
        ###########################################################################################
        ###########################################################################################
        ### 사용 변수 설정
        category_list_yaml_path = opt.category_list
        detail_category_list_yaml_path = opt.detail_category_list
        self.category_list = open_yaml(category_list_yaml_path)
        self.detail_category_list = open_yaml(detail_category_list_yaml_path)
        self.doll_list_yaml_path = opt.doll_list
        doll_list_remapping(opt.data_folder, opt.doll_list)
        
        self.current_doll_index = -1
        self.check_tree_item_folder = None
        self.check_tree_item_id = None
        
        self.doll_name = None
        self.doll_id = None
        
        self.image_data = {}
        
        ###########################################################################################
        
        ### 윈도우 설정
        self.setWindowTitle("DI Database Management System")
        self.setGeometry(100, 100, 2048, 1152)
        
        self.dolls = load_dolls_from_yaml(self.doll_list_yaml_path)
        if 'dolls' not in self.dolls:
            self.dolls['dolls'] = {}
        self.generated_random_variables = set()
        for doll_info in self.dolls['dolls'].values():
            self.generated_random_variables.add(doll_info.get('id', ''))
        
        ### 인형 이미지 선택 콤보 박스
        self.doll_image_list = QComboBox()
        
        self.box_table = QTableWidget()
        self.box_table.setColumnCount(7)
        self.box_table.setHorizontalHeaderLabels(["선택", "분류", "Part Name", "x_center_norm", "y_center_norm", "w_norm", "h_norm"])
        self.box_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.box_table.itemSelectionChanged.connect(self.update_box_selection_color)
        self.del_box_button = QPushButton("선택 박스 삭제")
        self.del_box_button.clicked.connect(self.delete_box)
        self.add_box_row_button = QPushButton("박스 항목 추가")
        self.add_box_row_button.clicked.connect(self.add_box_row)
        self.del_box_row_button = QPushButton("박스 항목 삭제")
        self.del_box_row_button.clicked.connect(self.del_box_row)
        
        ###########################################################################################
        ###########################################################################################
        ### 마우스로 박스 그리기 관련 변수 추가
        self.is_drawing = False
        self.drawing_box = None
        self.start_point = None
        self.view_mouse_enabled = True  # 필요 시 마우스 기능 제어
        
        ###########################################################################################
        ###########################################################################################
        ### 화면 레이아웃 설정
        self.splitter = QSplitter()
        
        ###########################################################################################
        ###########################################################################################
        ### 왼쪽 레이아웃 (데이터 목록 레이아웃)
        self.left_layout = QVBoxLayout()
        self.doll_list = QListWidget()
        self.left_layout.addWidget(QLabel("아이템(인형) 목록"))
        self.left_layout.addWidget(self.doll_list)
        self.page_control_layout = QHBoxLayout()
        self.add_button = QPushButton("인형 추가")
        self.del_button = QPushButton("인형 삭제")
        self.change_button = QPushButton("이름 변경")
        self.page_control_layout.addWidget(self.add_button)
        self.page_control_layout.addWidget(self.del_button)
        self.page_control_layout.addWidget(self.change_button)
        self.left_layout.addLayout(self.page_control_layout)
        self.add_button.clicked.connect(self.add_doll_item)
        self.del_button.clicked.connect(self.del_doll_item)
        self.change_button.clicked.connect(self.change_doll_name)
        left_widget = QWidget()
        self.left_layout.setContentsMargins(5, 5, 5, 5)
        left_widget.setLayout(self.left_layout)
        
        ###########################################################################################
        ###########################################################################################
        ### 가운데 좌측 레이아웃 (데이터 상세)
        ###########################################################################################
        ### 이미지 표시 레이아웃 (가운데 상단)
        self.right_top_splitter = QSplitter()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.viewport().installEventFilter(self)
        self.right_top_right_layout = QVBoxLayout()
        self.right_top_right_layout.addWidget(QLabel("인형 이미지"))
        self.right_top_right_layout.addWidget(self.view)
        # self.image_label_btn = QPushButton("이미지 라벨링")
        # self.right_top_right_layout.addWidget(self.image_label_btn)
        right_top_right_widget = QWidget()
        self.right_top_right_layout.setContentsMargins(5, 5, 5, 5)
        right_top_right_widget.setLayout(self.right_top_right_layout)
        
        
        
        self.right_top_left_layout = QVBoxLayout()
        self.right_top_left_layout.addWidget(QLabel("박스 목록"))
        self.right_top_left_layout.addWidget(self.box_table)
        
        self.right_top_left_layout.addWidget(self.del_box_button)
        self.right_top_left_layout.addWidget(self.add_box_row_button)
        self.right_top_left_layout.addWidget(self.del_box_row_button)
        
        right_top_left_widget = QWidget()
        self.right_top_left_layout.setContentsMargins(5, 5, 5, 5)
        right_top_left_widget.setLayout(self.right_top_left_layout)
        
        self.right_top_splitter.addWidget(right_top_right_widget)
        self.right_top_splitter.addWidget(right_top_left_widget)
        self.right_top_splitter.setSizes([700,300])
        self.setCentralWidget(self.right_top_splitter)
        
        ###########################################################################################
        ### 인형 데이터 표시 레이아웃 (가운데 하단)
        self.center_left_widget = QWidget()
        self.center_left_layout = QVBoxLayout(self.center_left_widget)
        self.selected_doll_name = QLabel("현재 인형: (none)")
        self.doll_data_tree = QTreeWidget()
        self.doll_data_tree.setHeaderLabels(["인형 데이터 항목", "파일 이름"])
        self.doll_data_tree.setStyleSheet(
            """
            QTreeWidget::item:selected { background-color: #cceeff; color: black; }
            QTreeWidget::item { padding: 4px; border-bottom: 1px solid #ccc; }
            """
        )
        self.doll_data_tree.setColumnWidth(0, 400)
        self.center_left_layout.addWidget(self.selected_doll_name)
        self.center_left_layout.addWidget(self.doll_data_tree)
        self.data_page_control_layout = QHBoxLayout()
        self.data_add_button = QPushButton("데이터 추가")
        self.data_del_button = QPushButton("데이터 삭제")
        self.data_change_button = QPushButton("데이터 변경")
        self.data_page_control_layout.addWidget(self.data_add_button)
        self.data_page_control_layout.addWidget(self.data_del_button)
        self.data_page_control_layout.addWidget(self.data_change_button)
        self.center_left_layout.addLayout(self.data_page_control_layout)
        self.data_add_button.clicked.connect(self.add_data_item)
        self.data_del_button.clicked.connect(self.del_data_item)
        self.data_change_button.clicked.connect(self.change_data_name)
        self.center_left_widget.setLayout(self.center_left_layout)
        self.center_left_scroll = QScrollArea()
        self.center_left_scroll.setWidgetResizable(True)
        self.center_left_scroll.setWidget(self.center_left_widget)
        
        ###########################################################################################
        ### 가운데 레이아웃 통합
        self.center_layout = QVBoxLayout()
        self.center_layout.addWidget(self.right_top_splitter, 7)
        self.center_layout.addWidget(QLabel("인형 이미지 선택"))
        self.center_layout.addWidget(self.doll_image_list)
        self.center_layout.addStretch(0)
        self.center_layout.addWidget(self.center_left_scroll, 3)
        center_widget = QWidget()
        self.center_layout.setContentsMargins(5, 5, 5, 5)
        center_widget.setLayout(self.center_layout)
        
        ###########################################################################################
        ###########################################################################################
        ### 우측 레이아웃 (카테고리 입력)
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget)
        self.selected_detail_doll_name = QLabel("현재 인형: (none)")
        self.doll_detail_category_tree = QTreeWidget()
        # 수정: 헤더를 2열("인형 데이터 세부 항목", "값")으로 설정하고, 0열은 편집 불가 delegate 할당
        self.doll_detail_category_tree.setHeaderLabels(["인형 데이터 세부 항목", "값"])
        self.doll_detail_category_tree.setColumnWidth(0, 250)
        self.doll_detail_category_tree.setStyleSheet("""
            QTreeWidget::item:selected { background-color: #cceeff; color: black; }
            QTreeWidget::item { padding: 4px; border-bottom: 1px solid #ccc; }
            """)
        self.left_layout.addWidget(self.selected_detail_doll_name)
        self.left_layout.addWidget(self.doll_detail_category_tree)
        self.left_widget.setLayout(self.left_layout)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_widget)
        
        ###########################################################################################
        ###########################################################################################
        ### 레이아웃 화면 비율 설정
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.addWidget(self.left_scroll)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 6)
        self.splitter.setStretchFactor(2, 3)
        self.setCentralWidget(self.splitter)
        
        ###########################################################################################
        ###########################################################################################
        
        ###########################################################################################
        ### 인형 아이템 로드
        self.load_dolls_to_list()
        self.doll_list.itemClicked.connect(self.doll_item_clicked)
        self.doll_list.itemClicked.connect(self.doll_item_clicked_image)
        self.doll_list.itemClicked.connect(self.doll_item_clicked_category)
        
        ###########################################################################################
        self.doll_data_tree.itemClicked.connect(self.tree_item_clicked)
        # 수정: 트리 항목 클릭 시, 두 열의 내용은 그대로 유지하도록 함 (편집 전 미리보기)
        self.doll_detail_category_tree.itemClicked.connect(self.update_value_display_in_item)
                                
        ###########################################################################################
        self.doll_image_list.currentTextChanged.connect(self.load_image)
        ###########################################################################################
        # self.image_label_btn.clicked.connect(self.label_image)
        
        # 수정: 0열(키)은 편집 불가 delegate 할당
        self.doll_detail_category_tree.setItemDelegate(NoEditDelegate())
                                
    ###########################################################################################
    ###########################################################################################
    def load_dolls_to_list(self):
        self.doll_list.clear()
        self.doll_list.setSortingEnabled(True)
        for doll in self.dolls['dolls']:
            self.doll_list.addItem(doll)
    
    def add_doll_item(self):
        while True:
            name, ok = QInputDialog.getText(self, '인형 이름 입력', '인형의 이름을 입력하세요:')
            if ok and name:
                if name in self.dolls['dolls']:
                    QMessageBox.warning(self, '중복된 이름', '이미 존재하는 인형 이름입니다. 다른 이름을 입력해주세요.', QMessageBox.Ok)
                    continue
                random_variable = generate_random_variable()
                if random_variable in self.generated_random_variables:
                    continue
                self.doll_list.addItem(name)
                self.dolls['dolls'][name] = {'name': name, 'id': random_variable}
                self.generated_random_variables.add(random_variable)
                save_dolls_to_yaml(self.dolls, self.doll_list_yaml_path)
                for category_name in self.category_list['category_list']:
                    if category_name == 'dolls':
                        category_name_temp = {}
                        for category_name_ in self.category_list['category_list']:
                            if category_name_ == 'dolls':
                                continue
                            category_name_temp[category_name_] = {}
                        data_temp = {'data': category_name_temp}
                        save_dolls_to_yaml(data_temp, os.path.join(opt.data_folder, category_name, random_variable + '.yaml'))
                    elif not os.path.isdir(os.path.join(opt.data_folder, category_name, random_variable)):
                        os.makedirs(os.path.join(opt.data_folder, category_name, random_variable))
                print(f"[INFO] {name} 인형 아이템 추가 완료")
                ensure_doll_category_json_exists(opt.data_folder, random_variable)
                break
            elif not name and ok:
                QMessageBox.warning(self, '입력 오류', '인형의 이름을 입력하지 않았습니다. 다시 시도해주세요.', QMessageBox.Ok)
                continue
            else:
                break
    
    def del_doll_item(self):
        selected_row = self.doll_list.currentRow()
        if selected_row >= 0:
            reply = QMessageBox.question(self, '아이템 삭제 확인', '선택한 인형을 정말로 삭제하시겠습니까?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                selected_item = self.doll_list.item(selected_row)
                doll_name = selected_item.text()
                self.doll_list.takeItem(selected_row)
                for category_name in self.category_list['category_list']:
                    if category_name == 'dolls':
                        os.remove(os.path.join(opt.data_folder, category_name, self.dolls['dolls'][doll_name]['id'] + '.yaml'))
                    elif os.path.isdir(os.path.join(opt.data_folder, category_name, self.dolls['dolls'][doll_name]['id'])):
                        shutil.rmtree(os.path.join(opt.data_folder, category_name, self.dolls['dolls'][doll_name]['id']))
                del self.dolls['dolls'][doll_name]
                save_dolls_to_yaml(self.dolls, self.doll_list_yaml_path)
                print(f"[INFO] {doll_name} 인형 아이템 삭제 완료")
        else:
            QMessageBox.warning(self, '선택된 인형 없음', '삭제할 인형이 선택되지 않았습니다.', QMessageBox.Ok)
    
    def change_doll_name(self):
        selected_row = self.doll_list.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "선택 오류", "변경할 인형이 선택되지 않았습니다.")
            return
        selected_item = self.doll_list.item(selected_row)
        if not selected_item:
            QMessageBox.warning(self, "오류", "선택한 인형을 찾을 수 없습니다.")
            return
        current_name = selected_item.text()
        new_name, ok = QInputDialog.getText(self, '인형 이름 변경', '새로운 인형 이름을 입력하세요:', text=current_name)
        if ok and new_name:
            if new_name in self.dolls['dolls']:
                QMessageBox.warning(self, "중복된 이름", "이미 존재하는 인형 이름입니다. 다른 이름을 입력해주세요.")
                return
            if current_name not in self.dolls['dolls']:
                QMessageBox.warning(self, "오류", f"{current_name} 인형은 목록에 없습니다.")
                return
            print(current_name)
            doll_info = self.dolls['dolls'].pop(current_name)
            doll_info['name'] = new_name
            self.dolls['dolls'][new_name] = doll_info
            selected_item.setText(f"{new_name}")
            save_dolls_to_yaml(self.dolls, self.doll_list_yaml_path)
            QMessageBox.information(self, "변경 완료", f"{current_name} 인형의 이름이 {new_name}으로 변경되었습니다.")
        elif not new_name:
            QMessageBox.warning(self, "입력 오류", "인형의 이름을 입력하지 않았습니다. 다시 시도해주세요.")
    
    def doll_item_clicked(self):
        selected_row = self.doll_list.currentRow()
        if selected_row == -1:
            return
        doll_name = self.doll_list.item(selected_row).text()
        self.doll_name = doll_name
        print(f"[INFO] {doll_name} 인형 선택")
        doll_id = self.dolls['dolls'][doll_name]['id']
        self.doll_id = doll_id
        doll_data_remapping(opt.data_folder, doll_id, self.category_list, self.detail_category_list)
        doll_data = open_yaml(os.path.join(opt.data_folder, 'dolls', doll_id + '.yaml'))
        self.selected_doll_name.setText(f"현재 인형: {doll_name}")
        self.selected_detail_doll_name.setText(f"현재 인형: {doll_name}")
        self.doll_item_view_tree(doll_data, doll_id)
        self.check_tree_item_folder = None
        self.check_tree_item_id = None
        self.loadClassesJson()
    
    def doll_item_view_tree(self, doll_data, doll_id):
        self.doll_data_tree.clear()
        populate_tree_from_data(self.doll_data_tree, doll_data, doll_id)
        self.doll_data_tree.expandAll()
    
    def tree_item_clicked(self, item, column):
        self.check_tree_item_folder = item.data(0, Qt.UserRole)['path']
        self.check_tree_item_id = item.data(0, Qt.UserRole)['id']
    
    def refresh_tree_view(self):
        doll_data = open_yaml(os.path.join(opt.data_folder, 'dolls', self.check_tree_item_id + '.yaml'))
        self.doll_data_tree.clear()
        populate_tree_from_data(self.doll_data_tree, doll_data, self.check_tree_item_id)
        self.doll_data_tree.expandAll()
    
    def add_data_item(self):
        if self.check_tree_item_folder is None or self.check_tree_item_id is None:
            return
        if self.check_tree_item_folder == 'data':
            QMessageBox.warning(self, "항목 선택 오류", "항목을 선택하지 않았습니다.")
            return
        category_name = self.check_tree_item_folder.split("\\")[1]
        if not os.path.isdir(self.check_tree_item_folder):
            self.check_tree_item_folder = os.path.dirname(self.check_tree_item_folder)
        dialog = UploadDataDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            file_path = dialog.selected_file
            if file_path:
                file_name = os.path.basename(file_path)
                target_file = os.path.join(self.check_tree_item_folder, file_name)
                if category_name in ['RequirementDetail', 'RequirementHeader', 'ProductsSample']:
                    if file_name.split('.')[-1] != 'xlsx':
                        QMessageBox.information(self, "업로드 취소", "xlsx 형식인지 확인바랍니다.")
                        return
                    if not os.path.exists(target_file) and len(os.listdir(os.path.dirname(target_file))) > 0:
                        QMessageBox.information(self, "업로드 취소", "해당 데이터 파일이 이미 존재합니다. (최대 파일 1개만 가능)")
                        return
                if os.path.exists(target_file):
                    if category_name == 'RequirementDetail':
                        reply = QMessageBox.question(self, "파일 덮어쓰기 확인",
                                                    "데이터가 이미 같은 이름으로 있습니다. 바꾸시겠습니까? (기존 박스 라벨링 데이터도 삭제됩니다.)",
                                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        
                        remove_path_1 = os.path.dirname(target_file.replace(category_name, 'BoxCheck'))
                        remove_path_2 = os.path.dirname(target_file.replace(category_name, 'BoxClass'))
                        remove_path_3 = os.path.dirname(target_file.replace(category_name, 'BoxLabel'))
                        
                        for remove_path in [remove_path_1, remove_path_2, remove_path_3]:
                            if os.path.exists(remove_path):
                                for filename in os.listdir(remove_path):
                                    remove_file_path = os.path.join(remove_path, filename)
                                    if os.path.isfile(remove_file_path):
                                        os.remove(remove_file_path)
                        
                    else:
                        reply = QMessageBox.question(self, "파일 덮어쓰기 확인",
                                                    "데이터가 이미 같은 이름으로 있습니다. 바꾸시겠습니까?",
                                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply != QMessageBox.Yes:
                        QMessageBox.information(self, "업로드 취소", "업로드가 취소되었습니다.")
                        return
                shutil.copy(file_path, target_file)
                QMessageBox.information(self, "업로드 완료", f"{os.path.basename(file_path)} 파일이 업로드되었습니다.")
                print(f"[INFO] 데이터 추가 완료")
                doll_data_remapping(opt.data_folder, self.check_tree_item_id, self.category_list, self.detail_category_list)
                self.refresh_tree_view()
                
                if category_name == 'RequirementDetail':
                    doll_detail_json_gen(category_name, target_file)
                if category_name == 'RequirementHeader':
                    doll_header_json_gen(category_name, target_file)
                if category_name == 'ProductsSample':
                    doll_product_json_gen(category_name, target_file)
                self.loadClassesJson()
                self.doll_image_list_name()
                self.load_image()
                
            else:
                QMessageBox.warning(self, "업로드 취소", "파일이 선택되지 않았습니다.")
        else:
            QMessageBox.information(self, "업로드 취소", "업로드가 취소되었습니다.")
    
    def del_data_item(self):
        if self.check_tree_item_folder is None or self.check_tree_item_id is None:
            return
        category_name = self.check_tree_item_folder.split("\\")[1]
        if os.path.isfile(self.check_tree_item_folder):
            if category_name == 'RequirementDetail':
                reply = QMessageBox.question(self, '데이터 삭제 확인', '선택한 데이터를 정말로 삭제하시겠습니까? (기존 박스 라벨링 데이터도 삭제됩니다.)',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            else:
                reply = QMessageBox.question(self, '데이터 삭제 확인', '선택한 데이터를 정말로 삭제하시겠습니까?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                os.remove(self.check_tree_item_folder)
                
                if category_name == 'RequirementDetail':
                    remove_path_1 = os.path.dirname(self.check_tree_item_folder.replace(category_name, 'BoxCheck'))
                    remove_path_2 = os.path.dirname(self.check_tree_item_folder.replace(category_name, 'BoxClass'))
                    remove_path_3 = os.path.dirname(self.check_tree_item_folder.replace(category_name, 'BoxLabel'))
                    
                    for remove_path in [remove_path_1, remove_path_2, remove_path_3]:
                        if os.path.exists(remove_path):
                            for filename in os.listdir(remove_path):
                                file_path = os.path.join(remove_path, filename)
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                
                if 'doll_artwork' in self.check_tree_item_folder:
                    path_pic = '\\'.join(self.check_tree_item_folder.split('\\')[:-1])
                    pic_name = self.check_tree_item_folder.split('\\')[-1]
                    pic_name = '.'.join(pic_name.split('.')[:-1])
                    
                    path_pic = path_pic.replace('doll_artwork', 'BoxLabel')
                    box_label_list = os.listdir(path_pic)
                    for box_label_name in box_label_list:
                        if 'ArtWork' in box_label_name and '_' + pic_name + '_' in box_label_name:
                            os.remove(os.path.join(path_pic, box_label_name))
                    
                    path_pic = path_pic.replace('BoxLabel', 'BoxCheck')
                    box_label_list = os.listdir(path_pic)
                    for box_label_name in box_label_list:
                        if 'ArtWork' in box_label_name and '_' + pic_name + '_' in box_label_name:
                            os.remove(os.path.join(path_pic, box_label_name))
                            
                if 'doll_picture' in self.check_tree_item_folder:
                    path_pic = '\\'.join(self.check_tree_item_folder.split('\\')[:-1])
                    pic_name = self.check_tree_item_folder.split('\\')[-1]
                    pic_name = '.'.join(pic_name.split('.')[:-1])
                    
                    path_pic = path_pic.replace('doll_picture', 'BoxLabel')
                    box_label_list = os.listdir(path_pic)
                    for box_label_name in box_label_list:
                        if 'Picture' in box_label_name and '_' + pic_name + '_' in box_label_name:
                            os.remove(os.path.join(path_pic, box_label_name))
                    
                    path_pic = path_pic.replace('BoxLabel', 'BoxCheck')
                    box_label_list = os.listdir(path_pic)
                    for box_label_name in box_label_list:
                        if 'Picture' in box_label_name and '_' + pic_name + '_' in box_label_name:
                            os.remove(os.path.join(path_pic, box_label_name))

                
                print(f"[INFO] 데이터 삭제 완료")
                doll_data_remapping(opt.data_folder, self.check_tree_item_id, self.category_list, self.detail_category_list)
                self.refresh_tree_view()
                self.loadClassesJson()
                self.doll_image_list_name()
                self.load_image()

                
                
        else:
            QMessageBox.warning(self, "항목 선택 오류", "파일을 선택하십시오.")
            return
    
    def change_data_name(self):
        if self.check_tree_item_folder is None or self.check_tree_item_id is None:
            return
        if os.path.isfile(self.check_tree_item_folder):
            current_name = os.path.basename(self.check_tree_item_folder)
            current_ext = os.path.splitext(current_name)[1]
            new_name_base, ok = QInputDialog.getText(self, "데이터 이름 변경", "새로운 데이터 이름을 입력하세요:", text=os.path.splitext(current_name)[0])
            if ok and new_name_base:
                new_name = new_name_base + current_ext
                if new_name != current_name:
                    parent_folder = os.path.dirname(self.check_tree_item_folder)
                    new_file_path = os.path.join(parent_folder, new_name)
                    if os.path.exists(new_file_path):
                        reply = QMessageBox.question(self, "이름 중복 확인",
                                                    f"{new_name} 파일이 이미 존재합니다. 덮어쓰시겠습니까?",
                                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if reply != QMessageBox.Yes:
                            QMessageBox.information(self, "변경 취소", "데이터 이름 변경이 취소되었습니다.")
                            return
                    try:
                        os.rename(self.check_tree_item_folder, new_file_path)
                        old_name = self.check_tree_item_folder.split('\\')[-1]
                        old_name = '.'.join(old_name.split('.')[:-1])
                        self.check_tree_item_folder = new_file_path
                        
                        
                        ### 이름 변경 시 박스랑 박스 이름도 같이 변경
                        
                        
                        
                        
                        if 'doll_artwork' in self.check_tree_item_folder:
                            path_pic = '\\'.join(self.check_tree_item_folder.split('\\')[:-1])
                            pic_name = self.check_tree_item_folder.split('\\')[-1]
                            pic_name = '.'.join(pic_name.split('.')[:-1])
                            
                            path_pic = path_pic.replace('doll_artwork', 'BoxLabel')
                            box_label_list = os.listdir(path_pic)
                            for box_label_name in box_label_list:
                                if 'ArtWork' in box_label_name and '_' + old_name + '_' in box_label_name:
                                    new_box_label_name = box_label_name.replace('_' + old_name + '_', '_' + pic_name + '_')
                                    os.rename(os.path.join(path_pic, box_label_name), os.path.join(path_pic, new_box_label_name))
                            
                            path_pic = path_pic.replace('BoxLabel', 'BoxCheck')
                            box_label_list = os.listdir(path_pic)
                            for box_label_name in box_label_list:
                                if 'ArtWork' in box_label_name and '_' + old_name + '_' in box_label_name:
                                    new_box_label_name = box_label_name.replace('_' + old_name + '_', '_' + pic_name + '_')
                                    os.rename(os.path.join(path_pic, box_label_name), os.path.join(path_pic, new_box_label_name))
                                    
                        if 'doll_picture' in self.check_tree_item_folder:
                            path_pic = '\\'.join(self.check_tree_item_folder.split('\\')[:-1])
                            pic_name = self.check_tree_item_folder.split('\\')[-1]
                            pic_name = '.'.join(pic_name.split('.')[:-1])
                            
                            path_pic = path_pic.replace('doll_picture', 'BoxLabel')
                            box_label_list = os.listdir(path_pic)
                            for box_label_name in box_label_list:
                                if 'Picture' in box_label_name and '_' + old_name + '_' in box_label_name:
                                    new_box_label_name = box_label_name.replace('_' + old_name + '_', '_' + pic_name + '_')
                                    os.rename(os.path.join(path_pic, box_label_name), os.path.join(path_pic, new_box_label_name))
                            
                            path_pic = path_pic.replace('BoxLabel', 'BoxCheck')
                            box_label_list = os.listdir(path_pic)
                            for box_label_name in box_label_list:
                                if 'Picture' in box_label_name and '_' + old_name + '_' in box_label_name:
                                    new_box_label_name = box_label_name.replace('_' + old_name + '_', '_' + pic_name + '_')
                                    os.rename(os.path.join(path_pic, box_label_name), os.path.join(path_pic, new_box_label_name))
                        
                        
                        
                        
                        
                        
                        QMessageBox.information(self, "변경 완료", f"데이터 이름이 {new_name}으로 변경되었습니다.")
                        doll_data_remapping(opt.data_folder, self.check_tree_item_id, self.category_list, self.detail_category_list)
                        self.refresh_tree_view()
                    except Exception as e:
                        QMessageBox.critical(self, "오류", f"이름 변경 중 오류 발생:\n{e}")
                else:
                    QMessageBox.information(self, "변경 취소", "데이터 이름 변경이 취소되었습니다.")
        else:
            QMessageBox.warning(self, "항목 선택 오류", "파일을 선택하십시오.")
            return
    

    

    
    def load_image(self):
        image_name = self.doll_image_list.currentText()
        print(f"[INFO] {image_name} 이미지 선택")
        self.scene.clear()
        if image_name is None or image_name == '' or image_name not in self.image_data.keys():
            return
        real_image_name = ")".join(image_name.split(")")[1:])[1:]
        pixmap = QPixmap(self.image_data[image_name])
        if pixmap.isNull():
            print(f"[오류] 이미지를 열 수 없습니다: {self.image_data[image_name]}")
            return
        self.iw = pixmap.width()
        self.ih = pixmap.height()
        pixmap_item = self.scene.addPixmap(pixmap)
        scale_factor = min(self.view.viewport().width() / self.iw,
                           self.view.viewport().height() / self.ih)
        if scale_factor > 1:
            pixmap_item.setTransformationMode(Qt.FastTransformation)
        else:
            pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.scene.setSceneRect(0, 0, self.iw, self.ih)
        self.view.setTransform(QTransform().scale(scale_factor, scale_factor))
        # 이미지 로드시, 해당 이미지에 저장된 박스 데이터만 업데이트하도록 load_box_data() 호출
        self.load_box_data()
        # 새로 추가: 해당 이미지에 저장된 체크박스 상태도 불러옵니다.
        self.load_box_check_status()
    
    def load_box_data(self):
        # 모든 항목(클래스.json의 내용)은 그대로 유지되지만,
        # 각 행마다 현재 선택된 이미지에 해당하는 라벨 파일(예: Picture_f_원자재_MOUTH.txt)이 존재하면
        # 그 파일의 첫 번째 줄의 좌표 데이터를 읽어 업데이트하고 박스를 그립니다.
        file_name_dict = {}
        
        for row in range(self.box_table.rowCount()):
            category = self.box_table.item(row, 1).text()
            part = self.box_table.item(row, 2).text()
            current_image = self.doll_image_list.currentText()
            if current_image.startswith('(ArtWork)'):
                image_type = "ArtWork"
                image_file = current_image[len('(ArtWork) '):].strip()
            elif current_image.startswith('(Picture)'):
                image_type = "Picture"
                image_file = current_image[len('(Picture) '):].strip()
            else:
                image_type = current_image
                image_file = current_image
            file_dir = os.path.join('data', 'BoxLabel', self.doll_id)
            file_name = f"{image_type}_{image_file}_{category}_{part}.txt"
            file_path = os.path.join(file_dir, file_name)
            if not os.path.exists(file_path):
                self.box_table.item(row, 3).setText("")
                self.box_table.item(row, 4).setText("")
                self.box_table.item(row, 5).setText("")
                self.box_table.item(row, 6).setText("")
                existing = self.box_table.item(row,3).data(Qt.UserRole)
                if existing is not None:
                    try:
                        self.scene.removeItem(existing[0])
                        self.scene.removeItem(existing[1])
                        self.scene.removeItem(existing[2])
                    except Exception:
                        pass
                continue
            
            if file_name in list(file_name_dict.keys()):
                line_num = file_name_dict[file_name]
                file_name_dict[file_name] += 1
            else:
                line_num = 0
                file_name_dict[file_name] = 1
            
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                if line_num < len(lines):
                    line = lines[line_num].strip()  # 첫 번째 줄만 사용
                    parts_line = line.split()
                    if len(parts_line) == 5:
                        _, x_str, y_str, w_str, h_str = parts_line
                        try:
                            x = float(x_str)
                            y = float(y_str)
                            w = float(w_str)
                            h = float(h_str)
                        except:
                            continue
                        self.box_table.item(row, 3).setText(f"{x:.6f}")
                        self.box_table.item(row, 4).setText(f"{y:.6f}")
                        self.box_table.item(row, 5).setText(f"{w:.6f}")
                        self.box_table.item(row, 6).setText(f"{h:.6f}")
                        self.drawBoxAtRow(row, x, y, w, h)
    
    def drawBoxAtRow(self, row, x, y, w, h):
        rect_x = (x - w/2) * self.iw
        rect_y = (y - h/2) * self.ih
        rect_w = w * self.iw
        rect_h = h * self.ih
        category = self.box_table.item(row, 1).text()
        selected_rows = [index.row() for index in self.box_table.selectionModel().selectedRows()]
        if row in selected_rows:
            pen = QPen(Qt.red, 5)
        else:
            if category == "부자재":
                pen = QPen(QColor("gray"), 1)
            else:
                pen = QPen(QColor("blue"), 1)
        new_box_item = QGraphicsRectItem(rect_x, rect_y, rect_w, rect_h)
        new_box_item.setPen(pen)
        seq_text = QGraphicsTextItem(str(row+1))
        seq_text.setDefaultTextColor(pen.color())
        seq_text.setPos(rect_x + rect_w - 20, rect_y + rect_h - 20)
        part_text = QGraphicsTextItem(self.box_table.item(row,2).text())
        part_text.setDefaultTextColor(pen.color())
        part_text.setPos(rect_x + 2, rect_y + 2)
        self.scene.addItem(new_box_item)
        self.scene.addItem(seq_text)
        self.scene.addItem(part_text)
        self.box_table.item(row,3).setData(Qt.UserRole, (new_box_item, seq_text, part_text))
    

    


    

    
    


    
    def doll_item_clicked_image(self):
        self.doll_image_list_name()
        self.load_image()
    
    def doll_image_list_name(self):
        load_concept_image_path = os.path.join(opt.data_folder, 'doll_artwork', self.doll_id)
        load_picture_image_path = os.path.join(opt.data_folder, 'doll_picture', self.doll_id)
        if os.path.isdir(load_picture_image_path):
            load_picture_image_path = os.listdir(load_picture_image_path)
        else:
            load_picture_image_path = []
        self.image_data = {}
        for image_file in os.listdir(load_concept_image_path):
            pdf_name, exe_ = os.path.splitext(os.path.basename(image_file))
            pdf_name = '(ArtWork) ' + pdf_name
            if exe_.lower() not in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                continue
            self.image_data[pdf_name] = os.path.join(load_concept_image_path, image_file)
        for image_file in os.listdir(os.path.join(opt.data_folder, 'doll_picture', self.doll_id)):
            pdf_name, exe_ = os.path.splitext(os.path.basename(image_file))
            pdf_name = '(Picture) ' + pdf_name
            if exe_.lower() not in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                continue
            self.image_data[pdf_name] = os.path.join(opt.data_folder, 'doll_picture', self.doll_id, image_file)
        self.doll_image_list.clear()
        self.doll_image_list.addItems(list(self.image_data.keys()))
    
    def doll_item_clicked_category(self):
        selected_row = self.doll_list.currentRow()
        if selected_row == -1:
            return
        doll_name = self.doll_list.item(selected_row).text()
        doll_id = self.dolls['dolls'][doll_name]['id']
        self.doll_id = doll_id
        doll_category_path = os.path.join(opt.data_folder, 'doll_detail_category', doll_id, 'doll_category.json')
        doll_detail_data = open_json(doll_category_path)
        self.doll_detail_category_view_tree(doll_detail_data, doll_category_path)
    
    def doll_detail_category_view_tree(self, doll_detail_data, doll_category_path):
        self.doll_detail_category_tree.clear()
        populate_tree_from_doll_detail(self.doll_detail_category_tree, doll_detail_data)
        self.doll_detail_category_tree.itemChanged.connect(
            lambda item, column: self.edit_item(item, column, doll_category_path)
        )
        self.doll_detail_category_tree.itemDoubleClicked.connect(
            lambda item, column: self.start_edit(item, column)
        )
        self.doll_detail_category_tree.itemClicked.connect(self.handle_item_clicked)
        self.doll_detail_category_tree.itemClicked.connect(self.update_value_display_in_item)
    
    def handle_item_clicked(self, item, column):
        print(self.doll_detail_category_tree.currentItem())
        print(f"Clicked value: {item.text(column)}")
        print(column)
    
    def update_value_display_in_item(self, item, column):
        pass
    
    def detail_category_tree_save(self):
        doll_category_path = os.path.join(opt.data_folder, 'doll_detail_category', self.doll_id, 'doll_category.json')
        data = self.tree_to_dict(self.doll_detail_category_tree.invisibleRootItem())
        save_json(data, doll_category_path)
        self.refresh_tree_detail_view(doll_category_path)
    
    def add_detail_data_item(self):
        selected_item = self.doll_detail_category_tree.currentItem()
        if not selected_item:
            print("No item selected.")
            return
        parent = selected_item.parent()
        if not parent:
            print("Top-level item cannot be added to.")
            return
        new_key = get_uniqueKey(parent, "NewKey")
        new_item = QTreeWidgetItem([new_key, ""])
        parent.addChild(new_item)
        self.detail_category_tree_save()
    
    def add_detail_data_subitem(self):
        import os
        selected_item = self.doll_detail_category_tree.currentItem()
        if not selected_item:
            print("선택된 항목이 없습니다.")
            return
        path = []
        item = selected_item
        while item and item != self.doll_detail_category_tree.invisibleRootItem():
            path.insert(0, item.text(0))
            item = item.parent()
        doll_category_path = os.path.join(opt.data_folder, 'doll_detail_category', self.doll_id, 'doll_category.json')
        data = open_json(doll_category_path)
        base = data
        curr = base
        for key in path[:-1]:
            if isinstance(curr, dict) and key in [str(k) for k in curr.keys()]:
                for k in curr.keys():
                    if str(k) == key:
                        curr = curr[k]
                        break
            else:
                print("경로를 찾지 못했습니다:", key)
                return
        parent_container = curr
        target_key = path[-1]
        if isinstance(parent_container, dict) and target_key in [str(k) for k in parent_container.keys()]:
            for k in parent_container.keys():
                if str(k) == target_key:
                    current_value = parent_container[k]
                    break
        else:
            print("대상 노드를 찾지 못했습니다:", target_key)
            return
        if current_value is None:
            parent_container[target_key] = {}
            current_value = parent_container[target_key]
        new_key = get_uniqueKey(selected_item, "NewKey")
        current_value[new_key] = {}
        save_json(data, doll_category_path)
        self.refresh_tree_detail_view(doll_category_path)
    
    def del_detail_data_item(self):
        selected_item = self.doll_detail_category_tree.currentItem()
        if selected_item:
            parent = selected_item.parent()
            if parent:
                parent.removeChild(selected_item)
            else:
                index = self.doll_detail_category_tree.indexOfTopLevelItem(selected_item)
                self.doll_detail_category_tree.takeTopLevelItem(index)
        self.detail_category_tree_save()
    
    def start_edit(self, item, column):
        if column == 0:
            return
        if item.parent() is None or item.parent() == self.doll_detail_category_tree.topLevelItem(0):
            return
        else:
            item.old_text = item.text(column)
            self.doll_detail_category_tree.editItem(item, column)
    
    def rename_json_key_in_place(self, parent_container, old_key_str, new_key_str):
        if not isinstance(parent_container, dict):
            print("parent_container is not a dict. Current value:", parent_container)
            return False
        original_key = None
        for k in parent_container.keys():
            if str(k) == old_key_str:
                original_key = k
                break
        if original_key is None:
            return False
        value = parent_container.pop(original_key)
        parent_container[new_key_str] = value
        return True
    
    def edit_item(self, item, column, doll_category_path):
        if column == 0:
            return
        if item.parent() is None or item.parent() == self.doll_detail_category_tree.topLevelItem(0):
            return
        new_text = item.text(column)
        if not hasattr(item, 'old_text') or new_text == item.old_text:
            return
        import os
        doll_category_path = os.path.join(opt.data_folder, 'doll_detail_category', self.doll_id, 'doll_category.json')
        data = open_json(doll_category_path)
        parent_container = data
        path = []
        cur = item
        while cur and cur != self.doll_detail_category_tree.invisibleRootItem():
            path.insert(0, cur.text(0))
            cur = cur.parent()
        for key in path[:-1]:
            if isinstance(parent_container, dict):
                if any(str(k) == key for k in parent_container.keys()):
                    for k in parent_container.keys():
                        if str(k) == key:
                            parent_container = parent_container[k]
                            break
                else:
                    print("경로를 찾지 못했습니다:", key)
                    return
            elif isinstance(parent_container, list):
                try:
                    idx = int(key.replace(".", "")) - 1
                    parent_container = parent_container[idx]
                except Exception as e:
                    print("경로를 찾지 못했습니다 (리스트 인덱스 변환 실패):", key, e)
                    return
            else:
                print("부모 컨테이너가 dict나 list가 아닙니다. 현재 값:", parent_container)
                return
        target_key = path[-1]
        if isinstance(parent_container, dict):
            parent_container[target_key] = new_text
        elif isinstance(parent_container, list):
            try:
                idx = int(target_key.replace(".", "")) - 1
                parent_container[idx] = new_text
            except Exception as e:
                print("최종 대상 인덱스 변환 실패:", target_key, e)
                return
        else:
            print("타겟 부모 컨테이너가 dict나 list가 아닙니다:", parent_container)
            return
        save_json(data, doll_category_path)
        self.refresh_tree_detail_view(doll_category_path)
        item.old_text = new_text
    
    def tree_to_dict(self, item):
        result = {}
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() > 0:
                result[child.text(0)] = self.tree_to_dict(child)
            else:
                txt = child.text(0)
                if " : " in txt:
                    result[child.text(0).split(" : ")[0]] = child.text(1)
                else:
                    result[child.text(0)] = child.text(1)
        return result
    
    def refresh_tree_detail_view(self, doll_category_path):
        expanded = get_expanded_paths(self.doll_detail_category_tree)
        doll_detail_data = open_json(doll_category_path)
        self.doll_detail_category_tree.clear()
        populate_tree_from_doll_detail(self.doll_detail_category_tree, doll_detail_data)
        restore_expanded_paths(self.doll_detail_category_tree, expanded)
    
    def search_detail_category(self):
        pass
    def group_detail_category(self):
        pass
    def label_image(self):
        selected_row = self.box_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "선택 오류", "박스를 선택하지 않았습니다.")
            return
        text, ok = QInputDialog.getText(self, "박스 입력", "0~1 사이의 x y w h 값을 입력하세요 (공백 구분):")
        if not ok or not text:
            return
        parts = text.split()
        if len(parts) != 4:
            QMessageBox.warning(self, "입력 오류", "정확히 4개의 값을 입력하세요.")
            return
        try:
            x, y, w, h = map(float, parts)
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "숫자 형식으로 입력하세요.")
            return
        if not(0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
            QMessageBox.warning(self, "입력 오류", "모든 값은 0과 1 사이여야 합니다.")
            return
        new_box_str = f"{x} {y} {w} {h}"
        self.update_box_label(selected_row, new_box_str)
        if hasattr(self, "iw") and hasattr(self, "ih"):
            rect_x = (x - w/2) * self.iw
            rect_y = (y - h/2) * self.ih
            rect_w = w * self.iw
            rect_h = h * self.ih
            from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
            pen = QPen(Qt.red)
            rect_item = QGraphicsRectItem(rect_x, rect_y, rect_w, rect_h)
            rect_item.setPen(pen)
            self.scene.addItem(rect_item)
            part_name = self.box_table.item(selected_row, 2).text()
            text_item = QGraphicsTextItem(part_name)
            text_item.setDefaultTextColor(Qt.red)
            text_item.setPos(rect_x, rect_y - 20)
            self.scene.addItem(text_item)
    
    def update_box_label(self, row, new_box_str):
        try:
            x_val, y_val, w_val, h_val = map(float, new_box_str.split())
        except Exception:
            return
        self.box_table.item(row, 3).setText(f"{x_val:.6f}")
        self.box_table.item(row, 4).setText(f"{y_val:.6f}")
        self.box_table.item(row, 5).setText(f"{w_val:.6f}")
        self.box_table.item(row, 6).setText(f"{h_val:.6f}")
        category = self.box_table.item(row, 1).text()
        part = self.box_table.item(row, 2).text()
        file_dir = os.path.join('data', 'BoxLabel', self.doll_id)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        current_image = self.doll_image_list.currentText()
        if current_image.startswith('(ArtWork)'):
            image_type = "ArtWork"
            image_file = current_image[len('(ArtWork) '):].strip()
        elif current_image.startswith('(Picture)'):
            image_type = "Picture"
            image_file = current_image[len('(Picture) '):].strip()
        else:
            image_type = current_image
            image_file = current_image
        file_name = f"{image_type}_{image_file}_{category}_{part}.txt"
        file_path = os.path.join(file_dir, file_name)
        group_rows = []
        for i in range(self.box_table.rowCount()):
            if (self.box_table.item(i,1).text() == category and
                self.box_table.item(i,2).text() == part):
                group_rows.append(i)
        group_rows.sort()
        try:
            seq_index = group_rows.index(row)
        except ValueError:
            seq_index = 0
        seq = seq_index + 1
        new_line = f"{seq} {x_val:.6f} {y_val:.6f} {w_val:.6f} {h_val:.6f}\n"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = []
        if len(lines) < len(group_rows):
            for _ in range(len(group_rows) - len(lines)):
                lines.append("\n")
        lines[seq_index] = new_line
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        # 새로 추가: 현재 박스의 체크박스 상태도 저장 (전체 상태를 JSON 배열로)
        self.save_box_check_status()
    
    def delete_box(self):
        selected_row = self.box_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "선택 오류", "삭제할 박스를 선택하세요.")
            return
        data = self.box_table.item(selected_row,3).data(Qt.UserRole)
        if data is not None:
            try:
                self.scene.removeItem(data[0])
                self.scene.removeItem(data[1])
                self.scene.removeItem(data[2])
            except Exception:
                pass
        category = self.box_table.item(selected_row, 1).text()
        part = self.box_table.item(selected_row, 2).text()
        current_image = self.doll_image_list.currentText()
        if current_image.startswith('(ArtWork)'):
            image_type = "ArtWork"
            image_file = current_image[len('(ArtWork) '):].strip()
        elif current_image.startswith('(Picture)'):
            image_type = "Picture"
            image_file = current_image[len('(Picture) '):].strip()
        else:
            image_type = current_image
            image_file = current_image
        file_name = f"{image_type}_{image_file}_{category}_{part}.txt"
        file_path = os.path.join('data', 'BoxLabel', self.doll_id, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        for col in range(3, 7):
            self.box_table.item(selected_row, col).setText("")
        # 새로 추가: 삭제 시 체크박스 상태 저장
        self.save_box_check_status()
        self.loadClassesJson()
        self.load_image()
        
        # 새로 추가된 행 선택
        self.box_table.selectRow(selected_row)
        self.box_table.scrollToItem(self.box_table.item(selected_row, 0))

    def add_box_row(self):
        selected_row = self.box_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "선택 오류", "기준이 될 박스를 선택하세요.")
            return
        
        category = self.box_table.item(selected_row, 1).text()
        part = self.box_table.item(selected_row, 2).text()
        
        json_path = os.path.join('data', 'BoxClass', self.doll_id, 'classes.json')
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("JSON 파일 로드 실패:", e)
            return

        i = selected_row
        if category == '부자재':
            i = i - len(data['원자재'])
        while i < len(data[category]):
            part_name = data[category][i]
            if '_' in part_name:
                part_name = '_'.join(part_name.split('_')[1:])
            if part == part_name:
                data[category] = data[category][:i+1] + ['2_' + part] + data[category][i+1:]
                print(i)
                break
            i += 1
                
        save_json(data, json_path)
        
        json_check_path = os.path.join('data', 'Boxcheck', self.doll_id)
        json_check_list = os.listdir(json_check_path)
        for check_name in json_check_list:
            json_file_path = os.path.join(json_check_path, check_name)
            
            try:
                with open(json_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print("JSON 파일 로드 실패:", e)
                return
            
            data.insert(selected_row + 1, False)
            save_json(data, json_file_path)

        self.loadClassesJson()
        #self.doll_image_list_name()
        self.load_image()
        
        # 새로 추가된 행 선택
        self.box_table.selectRow(selected_row + 1)
        self.box_table.scrollToItem(self.box_table.item(selected_row + 1, 0))

        
    def del_box_row(self):
        selected_row = self.box_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "선택 오류", "기준이 될 박스를 선택하세요.")
            return
        
        category = self.box_table.item(selected_row, 1).text()
        part = self.box_table.item(selected_row, 2).text()
        
        json_path = os.path.join('data', 'BoxClass', self.doll_id, 'classes.json')
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("JSON 파일 로드 실패:", e)
            return

        remove_check = False
        i = selected_row
        if category == '부자재':
            i = i - len(data['원자재'])
        while i < len(data[category]):
            part_name = data[category][i]
            if '_' in part_name:
                part_num = part_name.split('_')[0]
                part_name = '_'.join(part_name.split('_')[1:])
                
            if part == part_name:
                print(part_num, part)
                if part_num != '1':
                    ### 지우기
                    remove_check = True
                    data[category] = data[category][:i] + data[category][i+1:]
                    print(i)
                    break
            i += 1
            
        if remove_check == False:
            QMessageBox.warning(self, "선택 오류", "초기 Part Name은 제거할 수 없습니다.")
            return
                
        save_json(data, json_path)
        
        
        json_check_path = os.path.join('data', 'Boxcheck', self.doll_id)
        json_check_list = os.listdir(json_check_path)
        for check_name in json_check_list:
            json_file_path = os.path.join(json_check_path, check_name)
            
            try:
                with open(json_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print("JSON 파일 로드 실패:", e)
                return
            
            del data[selected_row]
            save_json(data, json_file_path)

        self.loadClassesJson()
        #self.doll_image_list_name()
        self.load_image()
        
        # 새로 추가된 행 선택
        self.box_table.selectRow(selected_row - 1)
        self.box_table.scrollToItem(self.box_table.item(selected_row - 1, 0))

    def update_box_selection_color(self):
        selected_rows = set()
        for item in self.box_table.selectedItems():
            selected_rows.add(item.row())
        for i in range(self.box_table.rowCount()):
            for j in range(self.box_table.columnCount()):
                item = self.box_table.item(i, j)
                if item:
                    if i in selected_rows:
                        item.setBackground(Qt.red)
                    else:
                        item.setBackground(Qt.white)
            data = self.box_table.item(i,3).data(Qt.UserRole)
            if data is not None:
                rect_item, seq_item, part_item = data
                try:
                    if i in selected_rows:
                        rect_item.setPen(QPen(Qt.red, 5))
                        seq_item.setDefaultTextColor(Qt.red)
                        part_item.setDefaultTextColor(Qt.red)
                    else:
                        category = self.box_table.item(i, 1).text()
                        if category == "부자재":
                            rect_item.setPen(QPen(QColor("gray"), 1))
                            seq_item.setDefaultTextColor(QColor("gray"))
                            part_item.setDefaultTextColor(QColor("gray"))
                        else:
                            rect_item.setPen(QPen(QColor("blue"), 1))
                            seq_item.setDefaultTextColor(QColor("blue"))
                            part_item.setDefaultTextColor(QColor("blue"))
                except RuntimeError:
                    continue
    
    ###########################################################################################
    ### 박스 목록 작성
    def loadClassesJson(self):
        self.box_table.clearContents()
        self.box_table.setRowCount(0)
        
        json_path = os.path.join('data', 'BoxClass', self.doll_id, 'classes.json')
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("JSON 파일 로드 실패:", e)
            return
        
        for category, part_list in data.items():
            for part in part_list:
                row_position = self.box_table.rowCount()
                self.box_table.insertRow(row_position)
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(lambda state, r=row_position: self.save_box_check_status())
                self.box_table.setCellWidget(row_position, 0, checkbox)
                category_item = QTableWidgetItem(category)
                category_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.box_table.setItem(row_position, 1, category_item)
                if '_' in part:
                    part = '_'.join(part.split('_')[1:])
                part_item = QTableWidgetItem(part)
                part_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.box_table.setItem(row_position, 2, part_item)
                x_item = QTableWidgetItem("")
                y_item = QTableWidgetItem("")
                w_item = QTableWidgetItem("")
                h_item = QTableWidgetItem("")
                self.box_table.setItem(row_position, 3, x_item)
                self.box_table.setItem(row_position, 4, y_item)
                self.box_table.setItem(row_position, 5, w_item)
                self.box_table.setItem(row_position, 6, h_item)
        
        self.box_table.resizeColumnsToContents()
    
    ###########################################################################################
    ### 마우스로 박스 그리기 이벤트 처리 (이미지 뷰의 뷰포트에서 발생)
    def eventFilter(self, source, event):
        image_name = self.doll_image_list.currentText()
        if image_name is None or image_name == '' or image_name not in self.image_data.keys():
            return False
        if source == self.view.viewport():
            if event.type() == QEvent.MouseButtonPress:
                self.start_point = self.view.mapToScene(event.pos())
                self.is_drawing = True
                self.drawing_box = QGraphicsRectItem()
                self.drawing_box.setPen(QPen(Qt.red, 2))
                self.scene.addItem(self.drawing_box)
                return True
            elif event.type() == QEvent.MouseMove and self.is_drawing and self.drawing_box:
                end_point = self.view.mapToScene(event.pos())
                rect = QRectF(self.start_point, end_point).normalized()
                self.drawing_box.setRect(rect)
                return True
            elif event.type() == QEvent.MouseButtonRelease and self.is_drawing and self.drawing_box:
                self.is_drawing = False
                rect = self.drawing_box.rect()
                self.scene.removeItem(self.drawing_box)
                self.drawing_box = None
                if rect.width() >= 5 and rect.height() >= 5:
                    x_center_norm = (rect.x() + rect.width()/2) / self.iw
                    y_center_norm = (rect.y() + rect.height()/2) / self.ih
                    w_norm = rect.width() / self.iw
                    h_norm = rect.height() / self.ih
                    self.addBoxDrawing(x_center_norm, y_center_norm, w_norm, h_norm)
                return True
        return super().eventFilter(source, event)
    
    def addBoxDrawing(self, x_center_norm, y_center_norm, w_norm, h_norm):
        row = self.box_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 오류", "박스 목록에서 행을 선택하세요.")
            return
        self.box_table.item(row, 3).setText(f"{x_center_norm:.6f}")
        self.box_table.item(row, 4).setText(f"{y_center_norm:.6f}")
        self.box_table.item(row, 5).setText(f"{w_norm:.6f}")
        self.box_table.item(row, 6).setText(f"{h_norm:.6f}")
        self.update_box_label(row, f"{x_center_norm} {y_center_norm} {w_norm} {h_norm}")
        rect_x = (x_center_norm - w_norm/2) * self.iw
        rect_y = (y_center_norm - h_norm/2) * self.ih
        rect_w = w_norm * self.iw
        rect_h = h_norm * self.ih
        if self.box_table.item(row,1).text() == "부자재":
            pen = QPen(QColor("gray"), 1)
        else:
            pen = QPen(QColor("blue"), 1)
        new_box_item = QGraphicsRectItem(rect_x, rect_y, rect_w, rect_h)
        new_box_item.setPen(pen)
        existing = self.box_table.item(row,3).data(Qt.UserRole)
        if existing is not None:
            try:
                self.scene.removeItem(existing[0])
                self.scene.removeItem(existing[1])
                self.scene.removeItem(existing[2])
            except Exception:
                pass
        seq_text = QGraphicsTextItem(str(row+1))
        seq_text.setDefaultTextColor(pen.color())
        seq_text.setPos(rect_x + rect_w - 20, rect_y + rect_h - 20)
        part_text = QGraphicsTextItem(self.box_table.item(row,2).text())
        part_text.setDefaultTextColor(pen.color())
        part_text.setPos(rect_x + 2, rect_y + 2)
        self.scene.addItem(new_box_item)
        self.scene.addItem(seq_text)
        self.scene.addItem(part_text)
        self.box_table.item(row,3).setData(Qt.UserRole, (new_box_item, seq_text, part_text))
    

    
    # 새로 추가: 체크박스 상태 저장/불러오기 함수 (하나의 이미지에 대해 전체 상태를 JSON 배열로 저장)
    def save_box_check_status(self):
        current_image = self.doll_image_list.currentText()
        if current_image.startswith('(ArtWork)'):
            image_type = "ArtWork"
            image_file = current_image[len('(ArtWork) '):].strip()
        elif current_image.startswith('(Picture)'):
            image_type = "Picture"
            image_file = current_image[len('(Picture) '):].strip()
        else:
            image_type = current_image
            image_file = current_image
        check_dir = os.path.join("data", "BoxCheck", self.doll_id)
        if not os.path.exists(check_dir):
            os.makedirs(check_dir)
        check_file = os.path.join(check_dir, f"{image_type}_{image_file}_check.json")
        status_list = []
        for row in range(self.box_table.rowCount()):
            checkbox = self.box_table.cellWidget(row, 0)
            if checkbox is not None:
                status_list.append(checkbox.isChecked())
            else:
                status_list.append(False)
        import json
        with open(check_file, "w", encoding="utf-8") as f:
            json.dump(status_list, f)
    
    def load_box_check_status(self):
        current_image = self.doll_image_list.currentText()
        if current_image.startswith('(ArtWork)'):
            image_type = "ArtWork"
            image_file = current_image[len('(ArtWork) '):].strip()
        elif current_image.startswith('(Picture)'):
            image_type = "Picture"
            image_file = current_image[len('(Picture) '):].strip()
        else:
            image_type = current_image
            image_file = current_image
        check_dir = os.path.join("data", "BoxCheck", self.doll_id)
        check_file = os.path.join(check_dir, f"{image_type}_{image_file}_check.json")
        if os.path.exists(check_file):
            import json
            with open(check_file, "r", encoding="utf-8") as f:
                status_list = json.load(f)
            for row in range(min(self.box_table.rowCount(), len(status_list))):
                checkbox = self.box_table.cellWidget(row, 0)
                if checkbox is not None:
                    checkbox.setChecked(status_list[row])
        else:
            # 체크박스 파일이 없을 경우에만 모든 행의 체크 상태를 false로 초기화
            for row in range(self.box_table.rowCount()):
                checkbox = self.box_table.cellWidget(row, 0)
                if checkbox is not None:
                    checkbox.setChecked(False)

# UploadDataDialog 클래스는 원본 그대로 유지됨
class UploadDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        if self.parent() is not None:
            path = self.parent().check_tree_item_folder
            if os.path.isdir(path):
                self.check_tree_item_folder = path
            else:
                self.check_tree_item_folder = os.path.dirname(path)
        self.setWindowTitle("데이터 업로드")
        self.resize(400, 200)
        layout = QVBoxLayout(self)
        self.folder_text = QLabel(f"업로드될 폴더: {self.check_tree_item_folder}")
        layout.addWidget(self.folder_text)
        self.label = QLabel("업로드할 파일을 선택하세요:")
        layout.addWidget(self.label)
        self.upload_button = QPushButton("파일 선택")
        layout.addWidget(self.upload_button)
        self.upload_button.clicked.connect(self.select_file)
        self.selected_label = QLabel("선택된 파일: 없음")
        layout.addWidget(self.selected_label)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.selected_file = None
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", "All Files (*)")
        if file_path:
            self.selected_file = file_path
            self.selected_label.setText(f"선택된 파일: {os.path.basename(file_path)}")
                
###################################################################################################
###################################################################################################
    
def main(opt):
    app = QApplication(sys.argv)
    window = DIDatabaseManagementWindow(opt)
    window.show()
    sys.exit(app.exec_())
    
###################################################################################################
###################################################################################################
    
if __name__ == "__main__":
    opt = parse_opt()
    category_folder_check(opt.data_folder, opt.category_list)
    main(opt)
    
###################################################################################################
###################################################################################################
