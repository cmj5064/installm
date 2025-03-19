import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import ssl
import uuid
import argparse

# SSL 인증서 검증 비활성화
ssl._create_default_https_context = ssl._create_unverified_context

# 커스텀 모듈 import
from ui.instagram import *
from ui.landing_page import render_landing_page
from ui.add_bookmark_page import render_add_bookmark_page
from ui.search_page import render_search_page

from db import BookmarkDatabase
from vector_store import VectorStore

from agent.agents import CategorizeAgent


parser = argparse.ArgumentParser()
parser.add_argument('--debug', action="store_true", help="debug mode")
args = parser.parse_args()

# .env 파일에서 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="인스타그램 북마크 매니저",
    page_icon="📸",
    layout="wide",
)

@st.cache_resource
def get_db(path):
    """데이터베이스 연결 객체를 반환합니다."""
    return BookmarkDatabase(path)

@st.cache_resource
def get_vector_store(path):
    """벡터 스토어 인스턴스를 반환합니다."""
    return VectorStore(path)

@st.cache_resource
def get_categorize_agent():
    """카테고리 분류 에이전트를 반환합니다."""
    return CategorizeAgent()

# 기본 경로 및 설정
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "bookmarks.db"

# 데이터베이스 및 벡터 스토어 초기화
db = get_db(str(DB_PATH))
vector_store = get_vector_store(str(DB_PATH))
# vector_store = "" # NOTE 위로 바꾸기
categorize_agent = get_categorize_agent()

# 카테고리 목록 가져오기
categorize_agent.base_categories = db.get_all_categories()


# 메인 함수
def main():
    # InstaLLM 로고 헤더
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Lobster&display=swap');
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
            .lobster-text {
                font-family: 'Lobster', sans-serif !important;
                font-weight: 400;
                font-size: 23px;
                font-style: normal;
            }
        </style>
        <h2 class="lobster-text" style='text-align: center; color: black;'><i class="fa-brands fa-instagram"></i>&nbsp;InstaLLM</h2>
    """, unsafe_allow_html=True)

    # streamlit page setting (endpoint, css style etc.)
    setup_page()
    
    # 사이드바 메뉴 렌더링 - ui.instagram 모듈에서 가져옴
    sidebar_menu()
    
    # 콘솔에 현재 메뉴 로깅 (디버깅용)
    print(f"현재 메뉴: {st.session_state.current_menu}")

    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]  # 짧은 고유 ID 생성
    
    # # 현재 선택된 메뉴 이름에 따라 제목 표시
    # menu_titles = {
    #     "랜딩 페이지": "Instagram 북마크 매니저",
    #     "북마크 추가": "북마크 추가",
    #     "북마크 검색": "북마크 검색",
    #     "카테고리별 보기": "카테고리별 보기"
    # }
    
    # st.markdown(f"<h2>{menu_titles.get(st.session_state.current_menu, '')}</h2>", unsafe_allow_html=True)

    sync_session_state_from_query_params()
    
    # 현재 선택된 메뉴에 따라 콘텐츠 표시
    if st.session_state.current_menu == "랜딩 페이지":
        render_landing_page(db, vector_store, args.debug)
    elif st.session_state.current_menu == "북마크 추가":
        render_add_bookmark_page(db, vector_store, categorize_agent, args.debug)
    elif st.session_state.current_menu == "북마크 검색":
        render_search_page(db, vector_store, args.debug)

if __name__ == "__main__":
    main()