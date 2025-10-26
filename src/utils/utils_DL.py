import os
import re
import shutil
import pdfplumber
import streamlit as st
from pdf2image import convert_from_bytes
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io, base64, pickle, math
import torch
import torchvision.transforms as transforms
import faiss
import numpy as np

########################################
# 유틸리티 함수들
########################################




def image_to_base64(img):
    """PIL 이미지 객체를 Base64 문자열로 변환"""
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()



########################################
# 후처리 알고리즘 함수들
########################################
def boxes_overlap(box1, box2, iou_threshold=0.00001):
    def calc_iou(a, b):
        x1, y1, x2, y2 = a
        ox1, oy1, ox2, oy2 = b
        inter_x1 = max(x1, ox1)
        inter_y1 = max(y1, oy1)
        inter_x2 = min(x2, ox2)
        inter_y2 = min(y2, oy2)
        iw = max(0, inter_x2 - inter_x1)
        ih = max(0, inter_y2 - inter_y1)
        inter_area = iw * ih
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (ox2 - ox1) * (oy2 - oy1)
        union_area = area1 + area2 - inter_area
        if union_area == 0:
            return 0.0
        return inter_area / union_area
    return calc_iou(box1, box2) > iou_threshold

def boxes_overlap_iom(box1, box2, iou_threshold=0.5):
    def calc_iom(a, b):
        x1, y1, x2, y2 = a
        ox1, oy1, ox2, oy2 = b
        inter_x1 = max(x1, ox1)
        inter_y1 = max(y1, oy1)
        inter_x2 = min(x2, ox2)
        inter_y2 = min(y2, oy2)
        iw = max(0, inter_x2 - inter_x1)
        ih = max(0, inter_y2 - inter_y1)
        inter_area = iw * ih
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (ox2 - ox1) * (oy2 - oy1)
        union_area = min(area1, area2)
        if union_area == 0:
            return 0.0
        return inter_area / union_area
    return calc_iom(box1, box2) > iou_threshold

def is_same_line(box1, box2, overlap_threshold=0.5):
    x1, y1, x2, y2 = box1
    ox1, oy1, ox2, oy2 = box2
    h1 = y2 - y1
    h2 = oy2 - oy1
    inter_top = max(y1, oy1)
    inter_bottom = min(y2, oy2)
    overlap_h = inter_bottom - inter_top
    if overlap_h <= 0:
        return False
    min_h = min(h1, h2)
    ratio = overlap_h / float(min_h)
    return ratio >= overlap_threshold

def box_in(parent_box, child_box):
    px1, py1, px2, py2 = parent_box
    cx1, cy1, cx2, cy2 = child_box
    return (cx1 >= px1) and (cy1 >= py1) and (cx2 <= px2) and (cy2 <= py2)

def merge_overlapping_boxes_ext(boxes_ext):
    merged = []
    for (x1, y1, x2, y2, cls_, ocrs, _) in boxes_ext:
        found = False
        for i, (mx1, my1, mx2, my2, mcls, mocrs, _) in enumerate(merged):
            if cls_ == mcls and boxes_overlap((x1, y1, x2, y2), (mx1, my1, mx2, my2)):
                nx1, ny1 = min(x1, mx1), min(y1, my1)
                nx2, ny2 = max(x2, mx2), max(y2, my2)
                merged[i] = (nx1, ny1, nx2, ny2, cls_, mocrs + ocrs, '')
                found = True
                break
        if not found:
            merged.append((x1, y1, x2, y2, cls_, ocrs, ''))
    return merged

def expand_section_box(boxes_ext):
    target = 1
    inc = [2, 3, 4, 5, 6, 7, 8, 10]
    out = []
    for i, (x1, y1, x2, y2, cls_, ocrs, _) in enumerate(boxes_ext):
        if cls_ != target:
            out.append((x1, y1, x2, y2, cls_, ocrs, ''))
            continue
        for j, (ox1, oy1, ox2, oy2, ocls, _, _) in enumerate(boxes_ext):
            if i == j: continue
            if ocls in inc and boxes_overlap((x1, y1, x2, y2), (ox1, oy1, ox2, oy2)):
                x1, y1 = min(x1, ox1), min(y1, oy1)
                x2, y2 = max(x2, ox2), max(y2, oy2)
        out.append((x1, y1, x2, y2, cls_, ocrs, ''))
    return out

def expand_image_table_box(boxes_ext):
    target = 5
    inc = [2, 3, 4, 6, 7, 8, 10]
    res = []
    for i, (x1, y1, x2, y2, cls_, ocrs, _) in enumerate(boxes_ext):
        if cls_ != target:
            res.append((x1, y1, x2, y2, cls_, ocrs, ''))
            continue
        for j, (ox1, oy1, ox2, oy2, ocls, _, _) in enumerate(boxes_ext):
            if i == j: continue
            if ocls in inc and boxes_overlap((x1, y1, x2, y2), (ox1, oy1, ox2, oy2)):
                x1, y1 = min(x1, ox1), min(y1, oy1)
                x2, y2 = max(x2, ox2), max(y2, oy2)
        res.append((x1, y1, x2, y2, cls_, ocrs, ''))
    return res

def postprocess_boxes(boxes_ext):
    for _ in range(2):
        boxes_ext = merge_overlapping_boxes_ext(boxes_ext)
    boxes_ext = expand_section_box(boxes_ext)
    boxes_ext = expand_image_table_box(boxes_ext)
    return boxes_ext

def expand_boxes_with_ocr(raw_boxes, ocr_data):
    exclude_cls = [6, 7, 8, 10]
    line_sens = [2, 3, 4]
    out = []
    for (rx1, ry1, rx2, ry2, rcls) in raw_boxes:
        x1, y1, x2, y2 = float(rx1), float(ry1), float(rx2), float(ry2)
        c = int(rcls)
        out.append([x1, y1, x2, y2, c, [], ''])
    for idx, (x1, y1, x2, y2, cls_, ocrs, _) in enumerate(out):
        if cls_ in exclude_cls:
            continue
        if cls_ == 0:
            for (ox1, oy1, ox2, oy2, txt, conf) in ocr_data:
                if box_in((x1, y1, x2, y2), (ox1, oy1, ox2, oy2)):
                    ocrs.append(str(txt))
            continue
        if cls_ in line_sens:
            new_x1, new_y1, new_x2, new_y2 = x1, y1, x2, y2
            for (ox1, oy1, ox2, oy2, txt, conf) in ocr_data:
                if boxes_overlap((new_x1, new_y1, new_x2, new_y2), (ox1, oy1, ox2, oy2)):
                    if is_same_line((new_x1, new_y1, new_x2, new_y2), (ox1, oy1, ox2, oy2)):
                        new_x1 = min(new_x1, ox1)
                        new_x2 = max(new_x2, ox2)
                        ocrs.append(str(txt))
            out[idx][0] = new_x1
            out[idx][1] = new_y1
            out[idx][2] = new_x2
            out[idx][3] = new_y2
        else:
            new_x1, new_y1, new_x2, new_y2 = x1, y1, x2, y2
            for (ox1, oy1, ox2, oy2, txt, conf) in ocr_data:
                if boxes_overlap((new_x1, new_y1, new_x2, new_y2), (ox1, oy1, ox2, oy2)):
                    new_x1 = min(new_x1, ox1)
                    new_y1 = min(new_y1, oy1)
                    new_x2 = max(new_x2, ox2)
                    new_y2 = max(new_y2, oy2)
                    ocrs.append(str(txt))
            out[idx][0] = new_x1
            out[idx][1] = new_y1
            out[idx][2] = new_x2
            out[idx][3] = new_y2
    return out

def sort_and_enumerate_boxes(final_boxes):
    if not final_boxes:
        return []
    page_boxes = [list(b) for b in final_boxes if b[4] == 9]
    other_boxes = [list(b) for b in final_boxes if b[4] != 9]
    xs = [x for b in other_boxes for x in (b[0], b[2])]
    midx = (min(xs) + max(xs)) / 2.0 if xs else 0
    def refine_sorting(boxes):
        n = len(boxes)
        i = 0
        while i < n - 1:
            if boxes[i][0] > boxes[i + 1][2] and boxes[i][3] > boxes[i + 1][1]:
                boxes[i], boxes[i + 1] = boxes[i + 1], boxes[i]
                i = max(i - 1, 0)
            else:
                i += 1
        return boxes
    def sort_boxes(boxes):
        sorted_boxes = []
        current_group = []
        current_type = None
        for box in sorted(boxes, key=lambda b: b[1]):
            x1, x2 = box[0], box[2]
            if x2 < midx:
                column_type = 'two_column'
            elif x1 > midx:
                column_type = 'two_column'
            else:
                column_type = 'single'
            if column_type != current_type and current_group:
                if current_type == 'single':
                    sorted_boxes.extend(sorted(current_group, key=lambda b: b[1]))
                    sorted_boxes = refine_sorting(sorted_boxes)
                else:
                    left_part = [b for b in current_group if b[2] < midx]
                    right_part = [b for b in current_group if b[0] > midx]
                    left_part.sort(key=lambda b: b[1])
                    right_part.sort(key=lambda b: b[1])
                    left_part = refine_sorting(left_part)
                    right_part = refine_sorting(right_part)
                    sorted_boxes.extend(left_part + right_part)
                current_group = []
            current_group.append(box)
            current_type = column_type
        if current_group:
            if current_type == 'single':
                sorted_boxes.extend(sorted(current_group, key=lambda b: b[1]))
                sorted_boxes = refine_sorting(sorted_boxes)
            else:
                left_part = [b for b in current_group if b[2] < midx]
                right_part = [b for b in current_group if b[0] > midx]
                left_part.sort(key=lambda b: b[1])
                right_part.sort(key=lambda b: b[1])
                left_part = refine_sorting(left_part)
                right_part = refine_sorting(right_part)
                sorted_boxes.extend(left_part + right_part)
        return sorted_boxes
    sorted_other_boxes = sort_boxes(other_boxes)
    page_list = sorted(page_boxes, key=lambda b: b[1])
    sorted_boxes = sorted_other_boxes + page_list
    processed_boxes = []
    for i, box in enumerate(sorted_boxes, start=1):
        if len(box) == 7:
            box.append(i)
        processed_boxes.append(box)
    return [tuple(box) for box in processed_boxes]

def build_tree_no_duplicate(final_sorted):
    def box_in(parent_box, child_box):
        px1, py1, px2, py2 = parent_box
        cx1, cy1, cx2, cy2 = child_box
        return (cx1 >= px1) and (cy1 >= py1) and (cx2 <= px2) and (cy2 <= py2)
    newt = []
    for (x1, y1, x2, y2, cls_, ocrs, sl, od_) in final_sorted:
        ocr_tuple = tuple(ocrs)
        newt.append((x1, y1, x2, y2, cls_, ocr_tuple, sl, od_))
    top_nodes_map = {}
    for b_t in newt:
        x1, y1, x2, y2, c_, oc, sl, or_ = b_t
        node = {
            "cls": c_,
            "bbox": [x1, y1, x2, y2],
            "ocr_text": list(oc),
            "text_start_line": sl,
            "order": or_,
            "children": []
        }
        top_nodes_map[b_t] = node
    assigned = set()
    for pkey, pnode in list(top_nodes_map.items()):
        if pnode["cls"] == 5:
            px1, py1, px2, py2 = pnode["bbox"]
            valid_child_found = False
            for ckey, cnode in list(top_nodes_map.items()):
                bx1, by1, bx2, by2, bcls, _, _, _ = ckey
                if bcls in [6, 7] and box_in((px1, py1, px2, py2), (bx1, by1, bx2, by2)):
                    valid_child_found = True
                    break
            if not valid_child_found:
                top_nodes_map.pop(pkey)
    for pkey, pnode in list(top_nodes_map.items()):
        if pnode["cls"] == 5:
            px1, py1, px2, py2 = pnode["bbox"]
            child_list = []
            for ckey in list(top_nodes_map.keys()):
                if ckey in assigned or ckey == pkey:
                    continue
                bx1, by1, bx2, by2, bcls, _, _, _ = ckey
                if bcls in [2, 3, 4, 6, 7, 8, 10]:
                    if box_in((px1, py1, px2, py2), (bx1, by1, bx2, by2)):
                        child_node = top_nodes_map[ckey]
                        child_list.append(child_node)
                        assigned.add(ckey)
                        top_nodes_map.pop(ckey, None)
            pnode["children"].extend(child_list)
    for pkey, pnode in list(top_nodes_map.items()):
        if pnode["cls"] == 1:
            px1, py1, px2, py2 = pnode["bbox"]
            child_list = []
            for ckey in list(top_nodes_map.keys()):
                if ckey in assigned or ckey == pkey:
                    continue
                bx1, by1, bx2, by2, bcls, _, _, _ = ckey
                if bcls in [2, 3, 4, 5, 6, 7, 8, 10]:
                    if box_in((px1, py1, px2, py2), (bx1, by1, bx2, by2)):
                        child_node = top_nodes_map[ckey]
                        child_list.append(child_node)
                        assigned.add(ckey)
                        top_nodes_map.pop(ckey, None)
            pnode["children"].extend(child_list)
    top_nodes = list(top_nodes_map.values())
    return top_nodes

def assign_order_dfs(top_nodes):
    c = [1]
    def dfs(n):
        n["order"] = c[0]
        c[0] += 1
        for ch in n["children"]:
            dfs(ch)
    for nd in top_nodes:
        dfs(nd)

########################################
# DetectionYOLO 클래스
########################################
class DetectionYOLO:
    def __init__(self, yolo_model, pdf_path, labeling_path):
        self.model = yolo_model
        self.pdf_path = pdf_path   # PDF 파일 경로 (없으면 빈 문자열)
        self.labeling_path = labeling_path
        self.class_names = [
            "대제목", "섹션 박스", "중제목", "소제목", "내용", "이미지/표 박스",
            "이미지", "표", "아이콘_내용", "페이지 번호", "아이콘", "목차"
        ]
        self.class_colors = [
            "#FF4500", "#1E90FF", "#FF1493", "#32CD32", "#FFD700", "#8B008B",
            "#00CED1", "#FF8C00", "#9400D3", "#FF1493", "#696969", "#8B4513"
        ]
        self.element_names = [
            "title", "section", "subtitle", "lasttitle", "content", "image_table",
            "image", "table", "icon_content", "page", "icon", "toc"
        ]
    
    def detect_and_postprocess(self, image_list, pdf_name, out_img_dir, out_label_dir):
        # 각 이미지에 대해 객체 탐지 및 후처리 수행
        os.makedirs(out_label_dir, exist_ok=True)  # out_label_dir 없으면 생성
        for img_path in image_list:
            print(f"[INFO] Processing image: {os.path.basename(img_path)}")
            ocr_data = []
            page = None
            if self.pdf_path:
                try:
                    with pdfplumber.open(self.pdf_path) as pdf:
                        page_index = int(os.path.splitext(os.path.basename(img_path))[0])
                        if page_index < len(pdf.pages):
                            page = pdf.pages[page_index]
                            words = page.extract_words()
                            im = Image.open(img_path)
                            img_width, img_height = im.size
                            page_width = page.width
                            page_height = page.height
                            scale_x = img_width / page_width
                            scale_y = img_height / page_height
                            for w in words:
                                pdf_x0 = float(w['x0'])
                                pdf_y0 = float(w['top'])
                                pdf_x1 = float(w['x1'])
                                pdf_y1 = float(w['bottom'])
                                img_x0 = pdf_x0 * scale_x
                                img_y0 = pdf_y0 * scale_y
                                img_x1 = pdf_x1 * scale_x
                                img_y1 = pdf_y1 * scale_y
                                cleaned_text = re.sub(r'\(cid:\d+\)', '', w['text'])
                                ocr_data.append((img_x0, img_y0, img_x1, img_y1, cleaned_text, 1.0))
                        else:
                            print(f"[WARNING] PDF 페이지 수 부족: {page_index} 페이지 요청")
                except Exception as e:
                    print(f"[WARNING] PDF 처리 오류: {e}")
            else:
                print("[INFO] PDF 파일이 없으므로 OCR 처리를 건너뜁니다.")
            
            base_img_name = os.path.splitext(os.path.basename(img_path))[0]
            label_file = os.path.join(self.labeling_path, pdf_name, "labels", f"{base_img_name}.txt")
            if os.path.exists(label_file):
                print(f"[INFO] 라벨 파일 존재: {label_file}")
                raw_boxes = []
                im = Image.open(img_path)
                width, height = im.size
                with open(label_file, 'r', encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            try:
                                cls_label = int(parts[0])
                                cx_norm, cy_norm, w_norm, h_norm = map(float, parts[1:5])
                                cx_abs = cx_norm * width
                                cy_abs = cy_norm * height
                                w_abs = w_norm * width
                                h_abs = h_norm * height
                                x1 = cx_abs - w_abs / 2
                                y1 = cy_abs - h_abs / 2
                                x2 = cx_abs + w_abs / 2
                                y2 = cy_abs + h_abs / 2
                                raw_boxes.append((x1, y1, x2, y2, cls_label))
                            except Exception as e:
                                print(f"[ERROR] 라벨 파싱 에러: {e}")
                final_b = raw_boxes
            else:
                results = self.model.predict(source=img_path, save=False, imgsz=640, verbose=False)
                raw_boxes = []
                for r_ in results:
                    box_ = r_.boxes.xyxy.cpu().numpy()
                    cls_ = r_.boxes.cls.cpu().numpy()
                    for (xx1, yy1, xx2, yy2), c_ in zip(box_, cls_):
                        x1, y1, x2, y2 = map(float, [xx1, yy1, xx2, yy2])
                        raw_boxes.append((x1, y1, x2, y2, int(c_)))
                if ocr_data:
                    b_ocr = expand_boxes_with_ocr(raw_boxes, ocr_data)
                else:
                    b_ocr = [(*box, [], '') for box in raw_boxes]
                final_b = postprocess_boxes(b_ocr)
            
            sorted_b = sort_and_enumerate_boxes(final_b)
            top_nodes = build_tree_no_duplicate(sorted_b)
            assign_order_dfs(top_nodes)
            
            out_img_path = os.path.join(out_img_dir, f"{base_img_name}.jpg")
            self.draw_result_image(img_path, top_nodes, out_img_path)
            
            def flatten_nodes(node):
                nodes = [node]
                for child in node.get("children", []):
                    nodes.extend(flatten_nodes(child))
                return nodes
            all_nodes = []
            for node in top_nodes:
                all_nodes.extend(flatten_nodes(node))
            im = Image.open(img_path)
            img_w, img_h = im.size
            label_lines = []
            for node in all_nodes:
                if "bbox" not in node:
                    continue
                x1, y1, x2, y2 = node["bbox"]
                cls_id = node.get("cls", 0)
                x_center = (x1 + x2) / 2.0 / img_w
                y_center = (y1 + y2) / 2.0 / img_h
                width_norm = (x2 - x1) / img_w
                height_norm = (y2 - y1) / img_h
                label_line = f"{cls_id} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}"
                label_lines.append(label_line)
            out_label_path = os.path.join(out_label_dir, f"{base_img_name}.txt")
            try:
                with open(out_label_path, "w", encoding="utf-8") as f:
                    for line in label_lines:
                        f.write(line + "\n")
            except Exception as e:
                print(f"[ERROR] 라벨 저장 오류: {e}")
    
    def draw_result_image(self, image_path, top_nodes, output_path):
        im = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
        dr = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("malgun.ttf", size=20)
        except:
            font = ImageFont.load_default()
        all_nodes = []
        def dfs_collect(nd):
            all_nodes.append(nd)
            for c in nd.get("children", []):
                dfs_collect(c)
        for top_ in top_nodes:
            dfs_collect(top_)
        for nd in all_nodes:
            if "bbox" not in nd:
                continue
            x1, y1, x2, y2 = nd["bbox"]
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            cc = nd.get("cls", 0)
            oo = nd.get("order", 0)
            cname = self.class_names[cc] if 0 <= cc < len(self.class_names) else f"cls_{cc}"
            label = f"{oo} {cc} {cname}"
            col = self.class_colors[cc % len(self.class_colors)]
            tb = dr.textbbox((0, 0), label, font=font)
            tw = tb[2] - tb[0]
            th = tb[3] - tb[1]
            pad = 10
            bg = [x1, y1 - (th + 5), x1 + (tw + pad * 2), y1]
            dr.rectangle(bg, fill=col + "AA")
            dr.text((x1 + pad, y1 - th - 5), label, fill="white", font=font)
            dr.rectangle([x1, y1, x2, y2], outline=col, width=3)
        merged = Image.alpha_composite(im, overlay).convert("RGB")
        merged.save(output_path)
        print(f"[INFO] Result image saved => {output_path}")

########################################
# 홈 리셋 함수
def home_reset_process():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

########################################
# 스프레드 HTML 생성 함수 (두 페이지씩 결합)
def get_spread_html(spread_idx, pages_list):
    left_idx = spread_idx * 2
    right_idx = left_idx + 1
    left_html = ""
    right_html = ""
    if left_idx < len(pages_list):
        left_html = f'<img src="data:image/png;base64,{image_to_base64(pages_list[left_idx])}" style="max-width:100%; height:auto;">'
    if right_idx < len(pages_list):
        right_html = f'<img src="data:image/png;base64,{image_to_base64(pages_list[right_idx])}" style="max-width:100%; height:auto;">'
    combined = f"""
    <div style="display:flex; justify-content:center; align-items:flex-start; gap:5px;">
        <div style="flex:1;">{left_html}</div>
        <div style="flex:1;">{right_html}</div>
    </div>
    """
    return combined