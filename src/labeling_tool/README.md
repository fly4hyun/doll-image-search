# DI Doll Labeling Tool

`main.py`는 **PyQt5 GUI** 기반 인형(Doll) 데이터 관리·라벨링 애플리케이션입니다.  
이미지·엑셀·JSON·YAML 등 다중 형식의 인형 관련 데이터를 일원화하여 관리하고,  
마우스로 **Bounding Box** 를 그리거나 테이블로 편집할 수 있습니다.

---

## 1. 폴더 구조 (요약)

```
.
├─data/                 # 인형 원본·라벨링 데이터(박스·클래스·체크 등)
├─utils/                # JSON·YAML·수치 연산 유틸
├─yaml/                 # 기본 카테고리·인형 목록 YAML
├─main.py               # ★ GUI 소스
└─dist/main.exe         # (선택) PyInstaller 패키징 결과
```

> 세부 파일명은 예시이며, 동일한 상위 구조만 유지하면 됩니다.

---

## 2. 환경 구축

### 2‑1. Conda 가상환경

```bash
conda create --name DI_search python=3.12.7 -y
conda activate DI_search
```

### 2‑2. 필수 패키지

```bash
pip install -r requirements.txt
```

`requirements.txt` *(아래)* 에는 실행에 필요한 최소 패키지만 포함되어 있습니다.  
실행 중 Qt 플러그인 오류가 나면 `pip install PyQt5‑Qt5 PyQt5‑sip` 로 수동 설치하세요.

---

## 3. 실행

```bash
python main.py --data_folder data \
               --category_list yaml/category_list.yaml \
               --detail_category_list yaml/detail_category_list.yaml \
               --doll_list yaml/doll_list.yaml
```

실행 후:

1. **좌측** 인형 목록 → 인형 추가/삭제/이름 변경  
2. **중앙** 이미지 뷰어 & 박스 테이블 → 마우스로 박스 그리기·편집  
3. **우측** 세부 카테고리 트리 → 더블클릭 편집 / 우클릭 추가·삭제

---

## 4. EXE 패키징 (선택)

Windows 단일 실행 파일을 만들려면:

```bash
# PyInstaller 설치
pip install pyinstaller

# 빌드
pyinstaller --onefile --windowed main.py
```

- 결과물은 `dist/main.exe` 로 생성됩니다.  
- 실행 시 `utils/`, `yaml/` 등 참조 데이터 폴더가 동일 경로에 있어야 합니다.

---

## 5. 참고

- **데이터 경로 구조**가 변경되면 `utils/utils_yaml.py`·`utils_json.py` 내부 로직을 함께 조정해야 합니다.  
- 대량 이미지 로드 시 메모리 사용량이 증가할 수 있으니 필요없는 `scene` 아이템은 `removeItem` 후 `del`로 해제하세요.
