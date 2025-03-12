### 코드 구조
```
installm/
├── app.py - main script to run service
├── db.py
├── ui/ - streamlit ui
│   ├── bookmark_viewer.py
│   ├── category_viewer.py
│   ├── dashboard.py
│   └── search.py
├── utils/ - small utility functions
│   ├── helpers.py
│   └── instagram.py
├── vector_store.py
└── requirements.txt
```

### 실행 환경 세팅
먼저 ai-talent-lab에서 .env 정보를 받아 repo folder 안에 생성해주세요.

이후 실행 환경은 아래와 같이 설정해주세요.
```bash
# venv 혹은 conda 환경 생성 후
pip install -r requirements.txt
```

### 코드 실행 방법
```bash
# run
streamlit run app.py
```