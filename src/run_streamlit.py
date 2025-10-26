###################################################################################################
###################################################################################################

import warnings
warnings.filterwarnings("ignore", message="xFormers is not available")

import asyncio, sys
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os 

import streamlit as st

import timm
import torch

from utils.utils_streamlit import *

###################################################################################################
###################################################################################################
# 가장 먼저 호출되야함

st.set_page_config(
    page_title="VisionDemo", 
    page_icon=":books:", 
    layout="wide"
    )

###################################################################################################

# 캐시를 이용해 모델 로드를 한 번만 수행
@st.cache_resource
def load_dinov2_model():
    model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitg14_reg_lc', pretrained=True)
    return model

# main() 실행 전에 모델 로드 (한번만 수행됨)
dinov2_model = load_dinov2_model().to(device)

# CUDA 사용 여부 확인
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

###################################################################################################
###################################################################################################

def main():
    st.title(':blue[오케스트로 AGI] Vision Model :red[DEMO]')

    ###############################################################################################

    ### 현재 활성화된 페이지 저장 
    if "page" not in st.session_state:
        st.session_state.page = "main_page"
        
    ### 체크박스 키워드 변수 선언
    if "keywords" not in st.session_state:
        st.session_state.keywords = {# '지능형 CCTV 피플 카운팅 데모':'PeopleCounting', 
                                     '삼성 설명서 문서 레이아웃 탐지 데모':'DocumentLayout', 
                                     '인형 이미지 검색 데모':'ImageSearch', 
                                     #'하수관로 결함 탐지 데모':'DefectDetection'
                                     }
        
    ###############################################################################################
    
    
    ###############################################################################################
    
    
    ###############################################################################################
    
    if "is_images_folder" not in st.session_state:
        st.session_state.is_images_folder = "IS_images"
        if not os.path.exists(st.session_state.is_images_folder):
            os.makedirs(st.session_state.is_images_folder)

    if "is_embedding_folder" not in st.session_state:
        st.session_state.is_embedding_folder = "IS_embedding"
        if not os.path.exists(st.session_state.is_embedding_folder):
            os.makedirs(st.session_state.is_embedding_folder)
            
    if "is_model" not in st.session_state:
        st.session_state.is_model = dinov2_model
        
    ###############################################################################################
    
    ### 시작 페이지
    if st.session_state.page == "main_page":
        page_main()
        
    if st.session_state.page == "PeopleCounting":
        people_counting_page()
        
    if st.session_state.page == "DocumentLayout":
        document_layout_page()
        
    if st.session_state.page == "ImageSearch":
        image_search_page()


###################################################################################################





###################################################################################################



###################################################################################################
###################################################################################################

if __name__ == '__main__':
    
    
    
    main()

###################################################################################################
###################################################################################################