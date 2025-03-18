from typing import List, Dict, Optional, Any, Tuple
import streamlit as st
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import base64
from io import BytesIO
import ssl
import json

# SSL 인증서 검증 비활성화
ssl._create_default_https_context = ssl._create_unverified_context

# 커스텀 모듈 import
from agent.search import Search
from ui.instagram import *
from ui.bookmark_viewer import BookmarkViewer
from utils.helpers import log_error
from utils.instagram import InstagramClient
from db import BookmarkDatabase
from vector_store import VectorStore
from agent.agents import CategorizeAgent

# .env 파일에서 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="인스타그램 북마크 매니저",
    page_icon="📸",
    layout="wide",
)

# 쿼리 파라미터에서 세션 상태로 메뉴 상태 동기화
def sync_session_state_from_query_params():
    query_params = st.query_params
    if "menu" in query_params:
        current_menu = query_params.get("menu")
        st.session_state.current_menu = current_menu
    elif "current_menu" not in st.session_state:
        st.session_state.current_menu = "북마크 추가"

# # 앱 초기화 시 세션 상태 동기화
# sync_session_state_from_query_params()

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

# # 사이드바 메뉴 정의
# def sidebar_menu():
#     # st.sidebar.title("북마크 매니저")
#     menu = st.sidebar.radio("메뉴", ["북마크 추가", "북마크 검색", "카테고리별 보기"])
#     return menu

# 북마크 추가 폼
def add_bookmark_form():
    # Instagram 로그인 정보를 세션 상태에서 확인
    if 'insta_logged_in' not in st.session_state:
        st.session_state.insta_logged_in = False
    
    # 로그인 영역
    if not st.session_state.insta_logged_in:
        # st.subheader("Instagram 로그인")
        with st.form(key="instagram_login"):
            insta_id = st.text_input("Instagram 아이디")
            insta_pw = st.text_input("Instagram 비밀번호", type="password")
            login_button = st.form_submit_button(label="로그인")
            
            if login_button:
                if insta_id and insta_pw:
                    # 로그인 정보를 세션 상태에 저장
                    st.session_state.insta_id = insta_id
                    st.session_state.insta_pw = insta_pw
                    st.session_state.insta_logged_in = True
                    
                    # 성공 메시지 표시
                    st.success("로그인 정보가 저장되었습니다. 이제 북마크를 추가할 수 있습니다.")
                    st.rerun()  # UI 새로고침
                else:
                    st.error("Instagram 아이디와 비밀번호를 모두 입력해주세요.")
    
    # 로그인 상태인 경우 북마크 추가 폼 표시
    else:
        st.success("Instagram에 로그인되었습니다.")
        
        # 로그아웃 버튼
        if st.button("로그아웃"):
            # 세션 상태에서 로그인 정보 제거
            if 'insta_id' in st.session_state:
                del st.session_state.insta_id
            if 'insta_pw' in st.session_state:
                del st.session_state.insta_pw
            st.session_state.insta_logged_in = False
            st.rerun()  # UI 새로고침
    
        with st.form(key="bookmark_form"):
            url = st.text_input("URL", f"https://www.instagram.com/{st.session_state.insta_id}/saved/all-posts/")
            bookmark_description = st.text_area("설명", "gulguleee27의 북마크")
            submit_button = st.form_submit_button(label="북마크 불러오기")
            
            if submit_button and url:
                # spinner로 로딩 표시
                with st.spinner('Instagram에서 북마크를 불러오는 중...'):
                    success, bookmarks = fetch_bookmarks(url, bookmark_description)
                
                if success and bookmarks:
                    st.session_state.fetched_bookmarks = bookmarks
                    st.success(f"{len(bookmarks)}개의 북마크를 불러왔습니다!")
                    
                    # 북마크 상태 정보 표시
                    st.info("⬇️ 아래 버튼을 클릭하여 북마크를 DB에 저장하세요.")
                else:
                    st.error("북마크를 불러오는 중 오류가 발생했습니다.")

        # 북마크 처리 현황 표시
        if 'fetched_bookmarks' in st.session_state:
            st.subheader("북마크 처리 상태")
            
            # 북마크 상태 정보를 2열 레이아웃으로 표시
            col1, col2 = st.columns(2)
            
            # DB 저장 상태
            with col1:
                db_status = "✅ 저장 완료" if 'db_saved' in st.session_state else "⏳ 대기 중"
                db_count = len(st.session_state.successful_bookmarks) if 'successful_bookmarks' in st.session_state else 0
                db_color = "green" if 'db_saved' in st.session_state else "orange"
                
                st.markdown(f"""
                <div style="padding: 10px; border-radius: 5px; border: 1px solid {db_color}; background-color: rgba(0,0,0,0.05)">
                    <h3 style="margin:0; color: {db_color}">📊 데이터베이스</h3>
                    <p style="margin:5px 0;">상태: {db_status}</p>
                    <p style="margin:5px 0;">저장된 북마크 수: {db_count}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 벡터 스토어 저장 상태
            with col2:
                vector_status = "✅ 저장 완료" if 'vector_saved' in st.session_state else "⏳ 대기 중"
                vector_count = len(st.session_state.successful_bookmarks) if 'successful_bookmarks' in st.session_state and 'vector_saved' in st.session_state else 0
                vector_color = "green" if 'vector_saved' in st.session_state else "orange"
                
                st.markdown(f"""
                <div style="padding: 10px; border-radius: 5px; border: 1px solid {vector_color}; background-color: rgba(0,0,0,0.05)">
                    <h3 style="margin:0; color: {vector_color}">🔍 벡터 스토어</h3>
                    <p style="margin:5px 0;">상태: {vector_status}</p>
                    <p style="margin:5px 0;">저장된 북마크 수: {vector_count}</p>
                </div>
                """, unsafe_allow_html=True)

        # 북마크가 불러와졌고 DB에 저장되지 않은 경우에만 DB 저장 버튼 표시
        if 'fetched_bookmarks' in st.session_state and 'db_saved' not in st.session_state:
            if st.button("DB에 북마크 저장"):
                with st.spinner('북마크를 데이터베이스에 저장하는 중...'):
                    success_count, fail_count = db.add_bookmark_batch(
                        st.session_state.fetched_bookmarks, 
                        # categorize_agent=categorize_agent
                        categorize_agent=None
                    )
                
                if success_count > 0:
                    st.success(f"{success_count}개의 북마크가 DB에 저장되었습니다.")
                    # DB 저장이 성공하면 성공한 북마크만 필터링해서 session state에 저장
                    successful_bookmarks = []
                    for bookmark in st.session_state.fetched_bookmarks:
                        if bookmark.get('feed_id') and bookmark.get('caption'):
                            successful_bookmarks.append(bookmark)
                    
                    st.session_state.db_saved = True
                    st.session_state.successful_bookmarks = successful_bookmarks
                    
                    if fail_count > 0:
                        st.warning(f"{fail_count}개의 북마크는 저장에 실패했습니다.")
                        
                    # 다음 단계 안내
                    st.info("⬇️ 이제 벡터 스토어에 북마크를 저장해보세요.")
                    st.rerun()  # 상태 표시 업데이트를 위한 리로드
                else:
                    st.error("북마크 저장에 실패했습니다.")

        # DB 저장 성공 후 벡터 스토어 저장 버튼 표시
        if 'db_saved' in st.session_state and 'vector_saved' not in st.session_state and st.session_state.successful_bookmarks:
            if st.button("벡터 스토어에 북마크 저장"):
                with st.spinner('북마크를 벡터 스토어에 저장하는 중...'):
                    try:
                        vector_store.add_bookmark_batch(st.session_state.successful_bookmarks)
                        st.success(f"{len(st.session_state.successful_bookmarks)}개의 북마크가 벡터 스토어에 저장되었습니다.")
                        st.session_state.vector_saved = True
                        st.rerun()  # 상태 표시 업데이트를 위한 리로드
                    except Exception as e:
                        st.error(f"벡터 스토어 저장 중 오류 발생: {str(e)}")
        
        # 모든 저장이 완료된 경우 완료 메시지와 세션 초기화 버튼
        if 'vector_saved' in st.session_state:
            st.success("모든 저장 과정이 완료되었습니다! 🎉")
            st.balloons()  # 축하 효과 추가
            if st.button("새로운 북마크 불러오기"):
                # 세션 상태 초기화
                if 'fetched_bookmarks' in st.session_state:
                    del st.session_state.fetched_bookmarks
                if 'db_saved' in st.session_state:
                    del st.session_state.db_saved
                if 'successful_bookmarks' in st.session_state:
                    del st.session_state.successful_bookmarks
                if 'vector_saved' in st.session_state:
                    del st.session_state.vector_saved
                st.rerun()

# 북마크 불러오기 함수 (저장하지 않고 데이터만 반환)
def fetch_bookmarks(url, bookmark_description):
    try:
        # 세션 상태에서 로그인 정보 가져오기
        insta_id = st.session_state.insta_id
        insta_pw = st.session_state.insta_pw
        
        client = InstagramClient(insta_id, insta_pw)
        bookmark_data = client.get_saved_feed(collection_id="all-posts")  # list output
        
        # 불러온 데이터 반환 (저장은 하지 않음)
        # return True, bookmark_data[:50] # TODO hardcoded
        return True, bookmark_data # TODO hardcoded # NOTE 위로 바꾸기
    
    except Exception as e:
        log_error(f"북마크 불러오기 중 오류: {e}")
        return False, None



# 북마크 검색 기능
def search_bookmark():
    search_type = st.radio("검색 유형", ["키워드 검색", "의미 검색", "다중 검색"])
    search_query = st.text_input("검색어를 입력하세요")

    search = Search(db, vector_store)
    
    if search_query:
        if search_type == "키워드 검색":
            bookmarks = search.keyword_search(search_query)
        elif search_type == "의미 검색":
            bookmarks = search.semantic_search(search_query)
        elif search_type == "다중 검색":
            bookmarks = search.multi_search(search_query)
        
        if bookmarks:
            display_bookmarks(bookmarks)
            # viewer = BookmarkViewer(db)
            # viewer.display_bookmarks(bookmarks=bookmarks)

        else:
            st.info("검색 결과가 없습니다.")

# 카테고리별 보기
def view_by_category():
    # 모든 카테고리 가져오기
    categories = db.get_all_categories()
    
    if not categories:
        st.info("저장된 카테고리가 없습니다.")
        return
    
    selected_category = st.selectbox("카테고리 선택", categories)
    
    if selected_category:
        bookmarks = db.get_bookmarks_by_category(selected_category)
        if bookmarks:
            display_bookmarks(bookmarks)
            # viewer = BookmarkViewer(db)
            # viewer.display_bookmarks(bookmarks=bookmarks)
        else:
            st.info(f"'{selected_category}' 카테고리에 북마크가 없습니다.")

# 북마크 표시 함수
def display_bookmarks(bookmarks):
    for bookmark in bookmarks:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if bookmark.get("thumbnail"):
                try:
                    # base64 데이터를 이미지로 변환
                    image_data = base64.b64decode(bookmark["thumbnail"])
                    image = BytesIO(image_data)
                    st.image(image, width=300)
                except Exception as e:
                    st.write("🔖")
            else:
                st.write("🔖")
        
        with col2:
            st.write(bookmark.get("url", ""))
            st.write(bookmark.get("caption", ""))
            
            # 카테고리 및 태그 표시
            categories = db.get_bookmark_categories(bookmark["id"])
            if categories:
                st.write("카테고리:")
                for cat in categories:
                    # st.write(f"- #{cat['name']}: {cat['reason']}")
                    st.write(f"- #{cat['name']}\n")
                    if cat['caption'] != bookmark.get('caption', ''):
                        st.write(f"  📝 카테고리 지정 당시 캡션: {cat['caption']}")
            
            if "hashtags" in bookmark:
                tags = " ".join([f"#{tag}" for tag in bookmark["hashtags"]])
                st.write(f"태그: {tags}")
            
            # 날짜 표시
            created_at = datetime.fromisoformat(bookmark["created_at"])
            st.caption(f"저장일: {created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # 북마크 삭제 버튼
            if st.button("삭제", key=f"delete_{bookmark['id']}"):
                if db.delete_bookmark(bookmark["id"]):
                    vector_store.delete_bookmark(bookmark["id"])
                    st.success("북마크가 삭제되었습니다.")
                    st.rerun()
        
        st.markdown("---")

# 메인 함수
def main():    
    # CSS 로드
    load_css()
    
    # URL 쿼리 파라미터와 세션 상태 동기화 (새로고침 시 상태 유지)
    sync_session_state_from_query_params()
    
    # 사이드바 메뉴 렌더링 - ui.instagram 모듈에서 가져옴
    sidebar_menu()
    # st.session_state.current_menu = sidebar()
    
    # 콘솔에 현재 메뉴 로깅 (디버깅용)
    print(f"현재 메뉴: {st.session_state.current_menu}")
    
    # # 현재 선택된 메뉴 이름에 따라 제목 표시
    # menu_titles = {
    #     "랜딩 페이지": "Instagram 북마크 매니저",
    #     "북마크 추가": "북마크 추가",
    #     "북마크 검색": "북마크 검색",
    #     "카테고리별 보기": "카테고리별 보기"
    # }
    
    # st.markdown(f"<h2>{menu_titles.get(st.session_state.current_menu, '')}</h2>", unsafe_allow_html=True)
    
    # 현재 선택된 메뉴에 따라 콘텐츠 표시
    if st.session_state.current_menu == "랜딩 페이지":
        add_bookmark_form()
    elif st.session_state.current_menu == "북마크 추가":
        add_bookmark_form()
    elif st.session_state.current_menu == "북마크 검색":
        search_bookmark()
    # elif st.session_state.current_menu == "카테고리별 보기":
    #     view_by_category()

if __name__ == "__main__":
    main()