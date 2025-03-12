from typing import List, Dict, Optional, Any, Tuple
import streamlit as st
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os
import ssl
from ui.bookmark_viewer import BookmarkViewer

# SSL 인증서 검증 비활성화
ssl._create_default_https_context = ssl._create_unverified_context

# 커스텀 모듈 import
from db import BookmarkDatabase
from vector_store import VectorStore
from utils.helpers import log_error
from utils.instagram import InstagramClient

# .env 파일에서 환경 변수 로드
load_dotenv()

# 기본 경로 및 설정
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "bookmarks.db"

# 데이터베이스 및 벡터 스토어 초기화
db = BookmarkDatabase(str(DB_PATH))
vector_store = VectorStore(str(DB_PATH))

# 사이드바 메뉴 정의
def sidebar_menu():
    st.sidebar.title("북마크 매니저")
    menu = st.sidebar.radio("메뉴", ["북마크 추가", "북마크 검색", "카테고리별 보기"])
    return menu

# 북마크 추가 폼
def add_bookmark_form():
    st.header("북마크 추가")

    # Instagram 로그인 정보를 세션 상태에서 확인
    if 'insta_logged_in' not in st.session_state:
        st.session_state.insta_logged_in = False
    
    # 로그인 영역
    if not st.session_state.insta_logged_in:
        st.subheader("Instagram 로그인")
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
            st.experimental_rerun()  # UI 새로고침
    
        with st.form(key="bookmark_form"):
            url = st.text_input("URL", "https://www.instagram.com/gulguleee27/saved/all-posts/")
            bookmark_description = st.text_area("설명", "전체")
            categories_input = st.text_input("카테고리 (쉼표로 구분)", "general")
            submit_button = st.form_submit_button(label="추가")
            
            if submit_button and url:
                categories = [cat.strip() for cat in categories_input.split(",") if cat.strip()]
                
                # 북마크 추가
                success = add_bookmark(url, bookmark_description, categories)
                
                if success:
                    st.success("북마크가 추가되었습니다!")
                else:
                    st.error("북마크 추가 중 오류가 발생했습니다.")

# 북마크 검색 기능
def search_bookmark():
    st.header("북마크 검색")
    
    search_type = st.radio("검색 유형", ["키워드 검색", "의미 검색"])
    search_query = st.text_input("검색어를 입력하세요")
    
    if search_query:
        if search_type == "키워드 검색":
            bookmarks = db.search_bookmarks(search_query)
        else:  # 의미 검색
            bookmarks = vector_store.search_bookmarks(search_query)
            # TODO script 분리해서 (semantic_search.py) filtering agent 등 추가해서 고도화
            # bookmarks = semantic_search(serach_query)
        
        if bookmarks:
            display_bookmarks(bookmarks)
            # viewer = BookmarkViewer(db)
            # viewer.display_bookmarks(bookmarks=bookmarks)

        else:
            st.info("검색 결과가 없습니다.")

# 카테고리별 보기
def view_by_category():
    st.header("카테고리별 보기")
    
    # 모든 카테고리 가져오기
    categories = db.get_categories()
    
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

# 북마크 저장 함수
def add_bookmark(url, bookmark_description, categories):
    try:
        client = InstagramClient(os.getenv("INSTA_ID"), os.getenv("INSTA_PW"))
        bookmark_data = client.get_saved_feed(collection_id="all-posts") # list output

        # for feed in bookmark_data[:50]: # 최신 50개만 불러옴
        #     success = db.add_bookmark(feed)
            
        #     # 벡터 스토어에 추가
        #     if success:
        #         vector_store.add_bookmark(feed)
        succes, fail = add_bookmarks_batch(bookmark_data[:50])
        return True
    
    except Exception as e:
        log_error(f"북마크 저장 중 오류: {e}")
        return False
    
def add_bookmarks_batch(bookmarks: List[dict]) -> Tuple[int, int]:
    """북마크 목록을 일괄적으로 추가합니다.
    
    Args:
        bookmarks: 북마크 목록
        
    Returns:
        (성공한 항목 수, 실패한 항목 수) 튜플
    """
    # 데이터베이스에 북마크 일괄 추가
    success_count, fail_count = db.add_bookmark_batch(bookmarks)
    
    if success_count > 0:
        # 벡터 저장소에 성공한 북마크만 추가
        successful_bookmarks = []
        for bookmark in bookmarks:
            if bookmark.get('feed_id') and bookmark.get('caption'):
                successful_bookmarks.append(bookmark)
        
        if successful_bookmarks:
            vector_store.add_bookmark_batch(successful_bookmarks)
    
    return (success_count, fail_count)

# 북마크 표시 함수 => # NOTE ui 작성 코드에서 가져옴
def display_bookmarks(bookmarks):
    for bookmark in bookmarks:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if bookmark.get("thumbnail_url"):
                try:
                    st.image(bookmark["thumbnail_url"], width=300)
                except:
                    st.write("🔖")
            else:
                st.write("🔖")
        
        with col2:
            st.write(bookmark.get("url", ""))
            st.write(bookmark.get("caption", ""))
            
            # 카테고리 및 태그 표시
            if "categories" in bookmark:
                categories = ", ".join([f"#{cat}" for cat in bookmark["categories"]])
                st.write(f"카테고리: {categories}")
            
            if "tags" in bookmark:
                tags = " ".join([f"#{tag}" for tag in bookmark["tags"]])
                st.write(f"태그: {tags}")
            
            # 날짜 표시
            created_at = datetime.fromisoformat(bookmark["created_at"])
            st.caption(f"저장일: {created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # 북마크 삭제 버튼
            if st.button("삭제", key=f"delete_{bookmark['id']}"):
                if db.delete_bookmark(bookmark["id"]):
                    vector_store.delete_bookmark(bookmark["id"])
                    st.success("북마크가 삭제되었습니다.")
                    st.experimental_rerun()
        
        st.markdown("---")

# 메인 함수
def main():
    st.set_page_config(
        page_title="북마크 매니저",
        page_icon="🔖",
        layout="wide",
    )
    
    menu = sidebar_menu()
    
    if menu == "북마크 추가":
        add_bookmark_form()
    elif menu == "북마크 검색":
        search_bookmark()
    elif menu == "카테고리별 보기":
        view_by_category()

if __name__ == "__main__":
    main()