###################################################################################################
###################################################################################################

import os, glob, math, io, base64

import streamlit as st

from PIL import Image
import numpy as np

import torch
import torchvision.transforms as transforms

import faiss
import pickle

###################################################################################################
###################################################################################################

def open_image_with_white_bg(image_path):
    """
    알파 채널이 있는 이미지(PNG 등)는 흰색 배경으로 변환하여 RGB 이미지로 반환합니다.
    """
    image = Image.open(image_path)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        bg = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode in ("RGBA", "LA"):
            bg.paste(image, mask=image.split()[3])
        else:
            bg.paste(image)
        return bg
    else:
        return image.convert("RGB")

###################################################################################################
    
def letterbox_image(image, target_size):
    """
    이미지 비율은 유지하고, target_size에 맞게 리사이즈한 후 흰색 패딩을 추가합니다.
    target_size: (width, height)
    """
    iw, ih = image.size
    w, h = target_size
    scale = min(w/iw, h/ih)
    nw = int(iw * scale)
    nh = int(ih * scale)
    image_resized = image.resize((nw, nh), Image.BILINEAR)
    # 흰색 배경의 새 이미지 생성
    new_image = Image.new('RGB', target_size, (255, 255, 255))
    pad_left = (w - nw) // 2
    pad_top = (h - nh) // 2
    new_image.paste(image_resized, (pad_left, pad_top))
    return new_image

interpolation=transforms.InterpolationMode.BICUBIC

###################################################################################################

# custom_transform: letterbox를 이용해 224×224 크기로 만들기 (찌그러짐 없이 흰색 패딩)
dino_transform = transforms.Compose([
    transforms.Lambda(lambda img: letterbox_image(img, (256, 256))),
    transforms.Resize(256, interpolation=interpolation),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

###################################################################################################
###################################################################################################

def save_uploaded_image(uploaded_file, model, device):
    image = Image.open(uploaded_file)
    save_path = os.path.join(st.session_state.is_images_folder, uploaded_file.name)
    
    img = open_image_with_white_bg(uploaded_file)
    img_tensor = dino_transform(img).to(device)
    with torch.no_grad():
        embedding = model(img_tensor.unsqueeze(0))  # (1, D) 형태
    # L2 정규화 수행 (정규화된 벡터의 내적은 코사인 유사도와 동일)
    embedding = embedding / torch.norm(embedding, p=2, dim=1, keepdim=True)
    
    embedding_path = os.path.join(st.session_state.is_embedding_folder, os.path.splitext(uploaded_file.name)[0] + ".pt")
    image.save(save_path)
    torch.save(embedding.cpu(), embedding_path)
    
    return save_path

###################################################################################################

def save_uploaded_embedding(uploaded_file):
    image = Image.open(uploaded_file)
    save_path = os.path.join(st.session_state.is_images_folder, uploaded_file.name)
    image.save(save_path)
    return save_path

###################################################################################################

def get_image_list():
    return glob.glob(os.path.join(st.session_state.is_images_folder, "*"))

def get_base64_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def display_image_gallery(per_page=5):
    images = get_image_list()
    total_images = len(images)
    total_pages = math.ceil(total_images / per_page) if total_images else 1

    # 현재 페이지 관리 (세션 상태 사용)
    if "is_page" not in st.session_state:
        st.session_state.is_page = 1
    current_page = st.session_state.is_page

    # 페이지 범위 보정
    if current_page < 1:
        current_page = 1
    elif current_page > total_pages:
        current_page = total_pages
    st.session_state.is_page = current_page

    start_index = (current_page - 1) * per_page
    end_index = start_index + per_page
    current_images = images[start_index:end_index]

    # 아래 부분이 스크롤 영역의 높이를 조절하는 부분입니다.
    # height:700px; 를 원하는 높이로 변경하세요.
    html = '<div style="height:900px; overflow-y:auto;">'
    for img_path in current_images:
        image = Image.open(img_path)
        img_base64 = get_base64_image(image)
        html += f'<div style="margin-bottom:10px;"><img src="data:image/png;base64,{img_base64}" style="width:100%;"></div>'
    html += '</div>'

    # st.components.v1.html의 height 파라미터는 외부 컨테이너의 높이를 결정합니다.
    st.components.v1.html(html, height=720)

    # 페이지네이션 컨트롤
    col_prev, col_page, col_next = st.columns(3)
    if col_prev.button("이전") and current_page > 1:
        st.session_state.is_page -= 1
        st.rerun()
    col_page.markdown(f"페이지 {current_page} / {total_pages}")
    if col_next.button("다음") and current_page < total_pages:
        st.session_state.is_page += 1
        st.rerun()

###################################################################################################
###################################################################################################
###################################################################################################

def open_image_with_white_bg(uploaded_file):
    """
    업로드된 이미지 파일을 흰 배경 이미지로 변환합니다.
    (실제 구현은 환경에 맞게 수정)
    """
    image = Image.open(uploaded_file).convert("RGBA")
    white_bg = Image.new("RGBA", image.size, "WHITE")
    combined = Image.alpha_composite(white_bg, image)
    return combined.convert("RGB")

def image_to_base64_str(image):
    """PIL 이미지 객체를 Base64 문자열로 변환합니다."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def display_query_image(query_image, width=300):
    """검색 이미지를 지정한 너비로 표시합니다."""
    st.markdown("### 검색 이미지")
    st.image(query_image, width=width)
    
def display_similarity_results(results, image_width=200, container_height=400, threshold=0.87):
    """
    유사도 검색 결과를 가로 스크롤 영역에 표시합니다.
    
    results: (파일 경로, 유사도) 튜플 리스트
    threshold: 지정한 문턱값 미만의 유사도인 경우 이미지 밝기를 낮춥니다.
    """
    html = '<div style="overflow-x: auto; white-space: nowrap;">'
    for file_path, similarity in results:
        try:
            image = Image.open(file_path)
            # 지정한 유사도 문턱값 미만이면 이미지 밝기를 낮춰서 어둡게 표시
            if similarity < threshold:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(0.8)  # 0.8 미만이면 어둡게
            img_str = image_to_base64_str(image)
            html += (
                f'<div style="display:inline-block; margin-right:10px; text-align:center;">'
                f'<img src="data:image/png;base64,{img_str}" style="width:{image_width}px;"><br>'
                f'{os.path.basename(file_path)}<br>유사도: {similarity:.2f}'
                f'</div>'
            )
        except Exception as e:
            st.error(f"이미지 로드 오류: {file_path}")
    html += '</div>'
    st.components.v1.html(html, height=container_height)

###################################################################################################
###################################################################################################

def build_faiss_index():
    """
    st.session_state.is_embedding_folder에 저장된 모든 임베딩(.pt 파일)들을 모아서
    FAISS 내적 기반(IndexFlatIP) 인덱스로 구성한 후, 인덱스를 저장하고
    이미지 파일 이름(확장자 포함) 리스트를 pickle로 저장합니다.
    """
    embedding_folder = st.session_state.is_embedding_folder
    embedding_files = glob.glob(os.path.join(embedding_folder, "*.pt"))
    
    if not embedding_files:
        st.warning("임베딩 파일이 없습니다.")
        return None, None
    
    embeddings_list = []
    image_names = []
    
    for file in embedding_files:
        tensor = torch.load(file)
        embedding = tensor.cpu().numpy()  # shape: (1, D)
        # L2 정규화
        norm = np.linalg.norm(embedding, axis=1, keepdims=True)
        if np.any(norm):
            embedding = embedding / norm
        embeddings_list.append(embedding[0])
        
        # 임베딩 파일의 베이스 이름 기준으로 이미지 파일 찾기 (확장자 포함)
        base_name = os.path.splitext(os.path.basename(file))[0]
        candidate_files = glob.glob(os.path.join(st.session_state.is_images_folder, base_name + ".*"))
        if candidate_files:
            image_file = os.path.basename(candidate_files[0])
        else:
            image_file = base_name
        image_names.append(image_file)
    
    embeddings_matrix = np.vstack(embeddings_list).astype("float32")
    dimension = embeddings_matrix.shape[1]
    
    # 내적 기반 인덱스 사용 → 정규화된 벡터의 내적은 코사인 유사도 (동일 이미지: 1)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_matrix)
    
    faiss.write_index(index, "dolls_index.faiss")
    with open("dolls_docs.pickle", "wb") as f:
        pickle.dump(image_names, f)

###################################################################################################
###################################################################################################

def image_search(search_file, model, device):
    """
    업로드된 파일(search_file)을 바탕으로 임베딩을 계산한 후,
    미리 저장된 FAISS 인덱스("dolls_index.faiss")와 문서("dolls_docs.pickle")를 이용하여
    상위 k개의 유사 이미지 결과를 반환합니다.
    
    반환값:
      - results: [(이미지 파일 경로, 유사도), ...] (유사도는 정규화된 벡터의 내적으로, 동일 이미지 → 1)
      - query_img: 검색 이미지(PIL 객체)
    """
    # 검색 이미지 열기 (알파 채널 처리 포함)
    query_img = open_image_with_white_bg(search_file)
    # 인덱스 생성 시 사용한 dino_transform과 동일하게 적용
    query_tensor = dino_transform(query_img).to(device)
    with torch.no_grad():
        query_embedding = model(query_tensor.unsqueeze(0))
    query_embedding = query_embedding.cpu().numpy().astype(np.float32)
    # L2 정규화 (동일 이미지의 내적은 1)
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
    
    index = faiss.read_index("dolls_index.faiss")
    with open("dolls_docs.pickle", "rb") as f:
        image_names = pickle.load(f)
        
    k = min(16, len(image_names))
    D, I = index.search(query_embedding, k)
    I = I[0]
    D = D[0]
    
    results = []
    for sim, idx in zip(D, I):
        file_path = os.path.join(st.session_state.is_images_folder, image_names[idx])
        results.append((file_path, sim))
    
    return results, query_img
        
###################################################################################################
###################################################################################################





###################################################################################################
###################################################################################################