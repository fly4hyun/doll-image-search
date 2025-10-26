###################################################################################################
###################################################################################################

import streamlit as st

from utils.utils_DL import *
from utils.utils_IS import *
from ultralytics import YOLO

###################################################################################################
###################################################################################################

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def page_main():
    
    ###############################################################################################
    ### 체크박스
    
    st.markdown("-------------------------------------------")
    st.markdown("#")
    st.markdown("### 시연할 기능을 선택하세요.")
    
    keywords = st.session_state.keywords.keys()
    
    keyword = st.radio(label = 'Check The Service You Require', options = keywords, label_visibility = 'hidden')
    st.session_state.selected_checkbox = keyword
    
    st.markdown("#")
    
    ###############################################################################################
    
    st.markdown("#")
    Process = st.button("Process")
    
    ###############################################################################################
    
    if Process:
        if not st.session_state.selected_checkbox:
            st.info("Please check the box to continue.")
            st.stop()
        else:
            if 'DefectDetection' == st.session_state.keywords[st.session_state.selected_checkbox]:
                st.info("보안 문제")
                st.stop()
            else:
                st.session_state.page = st.session_state.keywords[st.session_state.selected_checkbox]
                st.rerun()

###################################################################################################
###################################################################################################
### 메인 메뉴 동작 함수 (변수 초기화 후 페이지 이동)

def home_reset_process():
    
    st.session_state.page = "main_page"
    st.rerun()

###################################################################################################
###################################################################################################

def people_counting_page():
    
    ###############################################################################################
    ### 메인 메뉴
    
    with st.sidebar:
        
        st.markdown("## 빠른 시작")
        st.markdown("-------------------------------------------")
        Home_process = st.button("홈으로")
        # reset_process = st.button("대화 내용 초기화")
        st.markdown("-------------------------------------------")
        #st.markdown("(새로운 날씨나 국내 여행 정보를 원하시면 내용을 초기화 해주세요.)")
    
    ### 홈으로 함수 동작
    if Home_process:
        home_reset_process()

###################################################################################################
###################################################################################################


############## 이미ㅣ 있는거 가져오면 미리미리 로드 시켜놓는 기능 추가
############## 옆에 이미 올라가 있는거 목록 표시 및 제거 기능 추가







def document_layout_page():
    
    ###############################################################################################
    ### 메인 메뉴
    
    with st.sidebar:
        
        st.markdown("## 빠른 시작")
        st.markdown("-------------------------------------------")
        Home_process = st.button("홈으로")
        # reset_process = st.button("대화 내용 초기화")
        st.markdown("-------------------------------------------")
        #st.markdown("(새로운 날씨나 국내 여행 정보를 원하시면 내용을 초기화 해주세요.)")
    
    ### 홈으로 함수 동작
    if Home_process:
        home_reset_process()
        
    ###############################################################################################
        
    st.title("문서 레이아웃 탐지 데모")
    uploaded_pdf = st.file_uploader("문서 PDF 업로드", type=["pdf"])
    
    if uploaded_pdf is not None:
        # 새 PDF 파일 업로드 시 세션 초기화
        new_pdf_name = uploaded_pdf.name
        if "pdf_uploaded" not in st.session_state or st.session_state.pdf_uploaded != new_pdf_name:
            st.session_state.pdf_uploaded = new_pdf_name
            if "processed_pages" in st.session_state:
                del st.session_state.processed_pages
            if "current_page" in st.session_state:
                del st.session_state.current_page

        pdf_name = os.path.splitext(uploaded_pdf.name)[0]
        proc_dir = os.path.join("DL_processed_pages", pdf_name)
        
        # 폴더가 존재하면 결과 이미지를 불러오고, 없으면 새로 처리합니다.
        if os.path.exists(proc_dir):
            processed_pages = []
            for file in sorted(os.listdir(proc_dir)):
                # "page_"로 시작하는 파일을 불러옵니다.
                if file.startswith("temp_page_") and file.lower().endswith((".jpg", ".jpeg", ".png")):
                    try:
                        proc_img = Image.open(os.path.join(proc_dir, file))
                        new_width = 600
                        new_height = int(proc_img.height * new_width / proc_img.width)
                        proc_img = proc_img.resize((new_width, new_height))
                        processed_pages.append(proc_img)
                    except Exception as e:
                        st.error(f"파일 {file} 로드 오류: {e}")
            if processed_pages:
                st.session_state.processed_pages = processed_pages
            else:
                st.error("처리된 페이지 파일이 폴더에 없습니다.")
        else:
            # 폴더가 없으면 새로 생성하고 PDF를 처리합니다.
            os.makedirs(proc_dir, exist_ok=True)
            labels_dir = os.path.join(proc_dir, "labels")
            os.makedirs(labels_dir, exist_ok=True)
            with st.spinner("PDF 이미지 변환 및 레이아웃 탐지중..."):
                pdf_bytes = uploaded_pdf.read()
                pages = convert_from_bytes(pdf_bytes, dpi=200)
                processed_pages = []
                if "yolo_model" not in st.session_state:
                    st.session_state.yolo_model = YOLO("weights/best.pt")
                detector = DetectionYOLO(st.session_state.yolo_model, pdf_path="", labeling_path="")
                for i, page in enumerate(pages):
                    temp_path = os.path.join(proc_dir, f"temp_page_{i}.jpg")
                    out_path = os.path.join(proc_dir, f"page_{i}.jpg")
                    page.save(temp_path)
                    # 후처리 결과가 없으면 처리 시도
                    if not os.path.exists(out_path):
                        detector.detect_and_postprocess([temp_path], f"page_{i}", proc_dir, out_label_dir=labels_dir)
                    final_path = out_path if os.path.exists(out_path) else temp_path
                    try:
                        proc_img = Image.open(final_path)
                        new_width = 600
                        new_height = int(proc_img.height * new_width / proc_img.width)
                        proc_img = proc_img.resize((new_width, new_height))
                        processed_pages.append(proc_img)
                    except Exception as e:
                        st.error(f"페이지 {i} 처리 오류: {e}")
                st.session_state.processed_pages = processed_pages
        
        pages_list = st.session_state.processed_pages
        total_pages = len(pages_list)
        if total_pages == 0:
            st.error("처리된 페이지가 없습니다.")
            return
        total_spreads = (total_pages + 1) // 2  # 두 페이지씩
      
        if "current_spread" not in st.session_state:
            st.session_state.current_spread = 0
        
        # 네비게이션 버튼을 출력 영역 위쪽에 배치
        col_nav1, col_nav2 = st.columns(2)
        if col_nav1.button("이전 페이지"):
            st.session_state.current_spread = max(0, st.session_state.current_spread - 1)
            st.rerun()
        if col_nav2.button("다음 페이지"):
            st.session_state.current_spread = min(total_spreads - 1, st.session_state.current_spread + 1)
            st.rerun()
        
        st.markdown(f"스프레드 {st.session_state.current_spread + 1} / {total_spreads}")
        spread_html = get_spread_html(st.session_state.current_spread, st.session_state.processed_pages)
        st.components.v1.html(spread_html, height=1000)


###################################################################################################
###################################################################################################

def image_search_page():
    
    ###############################################################################################
    ### 메인 메뉴
    
    with st.sidebar:
        
        st.markdown("## 빠른 시작")
        st.markdown("-------------------------------------------")
        Home_process = st.button("홈으로")
        # reset_process = st.button("대화 내용 초기화")
        st.markdown("-------------------------------------------")
        #st.markdown("(새로운 날씨나 국내 여행 정보를 원하시면 내용을 초기화 해주세요.)")
    
    ### 홈으로 함수 동작
    if Home_process:
        home_reset_process()
        
    ###############################################################################################

    # 메인 레이아웃: 왼쪽은 기능, 오른쪽은 이미지 갤러리
    col_main, col_gallery = st.columns([4, 1])

    with col_main:
        st.markdown("### 이미지 업로드 및 검색 기능")
        mode = st.radio("모드를 선택하세요", ["이미지 업로드", "이미지 검색"])
        
        if mode == "이미지 업로드":
            uploaded_file = st.file_uploader("이미지 파일 선택", type=["png", "jpg", "jpeg"], key="file_uploader")
            if uploaded_file is not None:
                # 이전에 처리한 파일이 없거나 다른 파일인 경우에만 처리
                if ("last_uploaded_file" not in st.session_state or 
                    st.session_state.last_uploaded_file != uploaded_file.name):
                    save_uploaded_image(uploaded_file, st.session_state.is_model, device)
                    st.session_state.last_uploaded_file = uploaded_file.name
                    st.success("이미지가 저장되었습니다!")
                    build_faiss_index()
                    
        # 검색 모드 처리 예시
        elif mode == "이미지 검색":
            search_file = st.file_uploader("이미지 파일 선택", type=["png", "jpg", "jpeg"], key="search_file_uploader")
            if search_file is not None:
                # FAISS 인덱스를 사용한 유사도 검색 수행
                results, query_img = image_search(search_file, st.session_state.is_model, device)
                # 검색 이미지 표시 (크기 조절)
                display_query_image(query_img, width=300)
                st.markdown("### 검색 결과")
                display_similarity_results(results, image_width=200, container_height=400)

    with col_gallery:
        st.markdown('<h3 style="text-align: center;">이미지 갤러리</h3>', unsafe_allow_html=True)
        display_image_gallery(per_page=8)

###################################################################################################



###################################################################################################



###################################################################################################
###################################################################################################