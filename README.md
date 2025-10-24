# Doll Image Search (Dinov2 + FAISS)

> 인형 디자인/도안 제작 편의성을 위한 이미지 검색 시스템 개발
> 기간: 2024.03 – 2025.05

---

## Summary

* 인형 파츠/종류 구분이 가능한 **커스텀 라벨링 체계 및 라벨링 툴 개발**
* Dinov2 임베딩 + FAISS 인덱싱 기반 **유사 이미지 검색 파이프라인 구현**
* Streamlit UI로 **검색/미리보기 가능한 데모 서비스** 제작

---

## Technical Highlights

* PyQt5 기반 **라벨링 툴 자체 개발** (카테고리/파츠 단위 주석 관리)
* Dinov2 feature extraction → FAISS ANN Index 구축으로 **고속 검색 데모 구현**
* Streamlit 기반 **Web UI 프로토타입** 제공 (검색·조회·확장 용이)

---

## Visual Examples (to be inserted)

* 라벨링 툴 작업 화면 (`docs/figures/label_tool.png`)
* 검색 결과 예시 Top-K (`docs/figures/search_topk.png`)
* Streamlit 데모 캡처 (`docs/figures/demo_ui.png`)

> 위 파일명대로 추가 시 README에 그대로 반영 가능

---

## Disclosure

* 인형 원본 이미지/DB는 외부 공유 불가로 저장소에 포함하지 않음
* 본 저장소는 구조·데모 설명 및 코드 일부만 공개 가능 범위 내 정리

---

## Contact

이현희 / AI Research Engineer
[fly4hyun@naver.com](mailto:fly4hyun@naver.com)
