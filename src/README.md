# Vision Demo

Streamlit 기반 대시보드(`run_streamlit.py`) 하나로 **문서 레이아웃 탐지 · 이미지 검색** 데모를 실행합니다.

---

## 폴더 구조 (요약)

```
.
├─DL_data/               # 원본 PDF
├─DL_processed_pages/    # PDF → 이미지(.jpg) + YOLO 라벨(.txt)
├─IS_data/               # 검색 대상 이미지
├─IS_embedding/          # 이미지 임베딩(.pt, DINOv2)
├─utils/                 # 보조 함수
├─weights/               # YOLO 가중치(best.pt 등)
└─run_streamlit.py       # ★ 실행 파일
```

---

## 환경 구축

```bash
# Python 3.12 가상환경
conda create --name lifelog_demo python=3.12 -y
conda activate lifelog_demo

# FAISS GPU (선택)
conda install -c pytorch faiss-gpu -y

# 파이썬 패키지
pip install -r requirements.txt
```

> CUDA 11.8 GPU가 없는 경우 `torch==2.5.0`(CPU 빌드)로 교체하세요.

---

## 실행

```bash
streamlit run run_streamlit.py
```

첫 실행 시 **DINOv2 모델**을 다운로드하므로 다소 시간이 걸릴 수 있습니다.  
브라우저가 자동으로 열리지 않으면 `http://localhost:8501` 로 접속하세요.

---

## 참고

- Poppler 가 없으면 PDF→이미지 변환이 실패합니다.  
  Windows 사용자는 [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/) 압축 후 bin 경로를 **환경변수** `PATH` 에 추가하거나  
  `utils/utils_DL.py` 의 `convert_from_path(..., poppler_path="경로")` 로 지정하세요.
- YOLO 가중치(`weights/*.pt`)를 교체하면 클래스 수를 `utils/utils_DL.py`에 맞춰 수정해야 합니다.
