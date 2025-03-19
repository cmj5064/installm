import streamlit as st
from datetime import datetime
import base64
from io import BytesIO
from annotated_text import annotated_text

from agent.search import Search
# from ui.bookmark_viewer import BookmarkViewer

category_color = {  # TODO 몇몇 카태고리 annotation 색 지정
    "여행": "#8ef",
    "개구리": "afa"
}


# 북마크 검색 기능
def render_search_page(db, vector_store, debug):
    if debug:
        search_type = st.radio("검색 유형", ["키워드 검색", "의미 검색", "다중 검색", "total"])
    if 'search_input' not in st.session_state or st.session_state.search_input == "":
        # st.session_state.search_input = st.text_input("검색어를 입력하세요")
        # st.session_state.search_input = st.text_input("검색어를 입력하세요", key="search_input", label_visibility="collapsed")
        st.session_state.search_input = st.text_input("검색어를 입력하세요")
    else:
        st.text_input("검색어를 입력하세요", value=st.session_state.search_input)

    # # Add custom CSS for button styling
    # st.markdown("""
    # <style>
    # div.stButton > button {
    #     background-color: #2d2d2d;
    #     color: white;
    #     border-radius: 20px;
    #     padding: 10px 15px;
    #     border: none;
    #     text-align: center;
    #     width: 100%;
    # }
    # div.stButton > button:hover {
    #     background-color: #3d3d3d;
    # }
    # </style>
    # """, unsafe_allow_html=True)

    # Example queries
    example_queries = [
        "뮤지컬 관련 정보 보여줘.",
        "이번 여름에 여행 어디 가지?"
    ]

    # Create dynamic buttons based on example queries
    if 'search_input' not in st.session_state or st.session_state.search_input == "":
        # cols = st.columns(len(example_queries))
        # for i, query in enumerate(example_queries):
        #     with cols[i]:
        #         if st.button(query):
        #             st.session_state.search_input = query
        #             st.rerun()
        for i, query in enumerate(example_queries):
            if st.button(query):
                st.session_state.search_input = query
                st.rerun()

    search = Search(db, vector_store)
    
    if st.session_state.search_input and st.session_state.search_input != "":
        if debug:
            if search_type == "키워드 검색":
                bookmarks = search.keyword_search(st.session_state.search_input)
            elif search_type == "의미 검색":
                bookmarks = search.semantic_search(st.session_state.search_input)
            elif search_type == "다중 검색":
                bookmarks = search.multi_search(st.session_state.search_input)
            elif search_type == "total":
                bookmarks = search.multi_search(st.session_state.search_input)
        else:
            # bookmarks = search.multi_search(st.session_state.search_input)
            bookmarks = search.total_search(st.session_state.search_input)

        if bookmarks:
            display_bookmarks(bookmarks, db, vector_store)
            # viewer = BookmarkViewer(db)
            # viewer.display_bookmarks(bookmarks=bookmarks)

        else:
            st.info("검색 결과가 없습니다.")

# 북마크 표시 함수
def display_bookmarks(bookmarks, db, vector_store):
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
            categories = db.get_bookmark_categories(bookmark["id"])
            if categories:
                cat_str = ""
                for cat in categories:
                    cat_str += f"{cat["name"]}"
                    # st.write(f"#{cat['name']}\n")
                    # if cat['caption'] != bookmark.get('caption', ''):
                    #     st.write(f"  📝 카테고리 지정 당시 캡션: {cat['caption']}")
                annotated_text("category: ", (cat_str, "", "#8ef"), "")

            st.write(bookmark.get("url", ""))
            st.write(bookmark.get("caption", ""))
            
            if "hashtags" in bookmark:
                tags = " ".join([f"#{tag}" for tag in bookmark["hashtags"]])
                st.write(f"tags: {tags}")
            
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

# # 카테고리별 보기
# def view_by_category():
#     # 모든 카테고리 가져오기
#     categories = db.get_all_categories()
    
#     if not categories:
#         st.info("저장된 카테고리가 없습니다.")
#         return
    
#     selected_category = st.selectbox("카테고리 선택", categories)
    
#     if selected_category:
#         bookmarks = db.get_bookmarks_by_category(selected_category)
#         if bookmarks:
#             display_bookmarks(bookmarks)
#             # viewer = BookmarkViewer(db)
#             # viewer.display_bookmarks(bookmarks=bookmarks)
#         else:
#             st.info(f"'{selected_category}' 카테고리에 북마크가 없습니다.")