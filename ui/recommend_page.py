import streamlit as st
from PIL import Image
import os
import time
# from datetime import datetime
# import base64
# from io import BytesIO
# from annotated_text import annotated_text

from agent.agents import RecommendAgent
from utils.instagram import get_recent_feeds


# 북마크 검색 기능
def render_recommend_page(db, vector_store, debug):
    if 'search_input' in st.session_state:
        previous_query = st.session_state["search_input"]
    else:
        previous_query = "이번 여름에 여행 어디 가지?"

    if 'search_output' in st.session_state:
        user_history = st.session_state["search_output"]
    else:
        st.error("검색 히스토리가 없습니다. LLM 오마카세 모드로 추천합니다.")
        # user_history = []
        from agent.search import Search
        search = Search(db, vector_store)
        user_history = search.total_search(previous_query)

    # TODO previous_query에서 hashtag extract agent와 같은 키워드 추출 기능 추가 필요
    if "뮤지컬" in previous_query:
        hashtag = "뮤지컬"
    elif "여행" in previous_query:
        hashtag = "여행"
    else:
        hashtag = "트렌드" 

    with st.spinner(f"#{hashtag}의 트렌드 게시물을 불러오는 중..."):
        time.sleep(5)
        recent_feeds = get_recent_feeds(hashtag) # List[dict]
        # print(f"recent_feeds: {recent_feeds}")

    if recent_feeds:
        recommend_agent = RecommendAgent()
        with st.spinner("당신의 취향을 기반으로 게시물을 추리고 있어요!"):
            state = recommend_agent.run(previous_query, user_history, recent_feeds)
            print(f"추천 이유: {state["recommend_reasons"]}")
        
        if state and state['recommended_feeds']:
            display_recom_bookmarks(state['recommended_feeds'], state["recommend_reasons"], hashtag, db, vector_store, debug)

            # if debug:
            #     for i, reason in enumerate(state["recommend_reasons"]):
            #         st.info(f"{i}: {reason}")

        else:
            st.error("추천 agent 답변 생성 중 에러가 발생했습니다.")

    else:
        st.info("검색 결과가 없습니다.")

# 북마크 표시 함수
def display_recom_bookmarks(bookmarks, reasons, hashtag, db, vector_store, debug):
    st.success("🤖: 다음과 같은 게시물들이 최근에 올라왔어요!")

    for i, bookmark in enumerate(bookmarks):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # if bookmark.get("thumbnail_"):
            try:
                # # base64 데이터를 이미지로 변환
                # image_data = base64.b64decode(bookmark["thumbnail"])
                # image = BytesIO(image_data)
                
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                img_path = os.path.join(base_dir, f"data/image/{bookmark['feed_id']}.png")
                # print(img_path)

                if os.path.exists(img_path):
                    image = Image.open(img_path)
                else:
                    # image = Image.open("./data/image/null.png")
                    image = Image.open(os.path.join(base_dir, f"data/image/null.png"))
                
                st.image(image, width=300)

            except Exception as e:
                st.write("🚫")
            # else:
            #     st.write("🚫")
        
        with col2:
            # categories = db.get_bookmark_categories(bookmark["id"])
            # if categories:
            #     cat_str = ""
            #     for cat in categories:
            #         cat_str += f"{cat["name"]}"
            #         # st.write(f"#{cat['name']}\n")
            #         # if cat['caption'] != bookmark.get('caption', ''):
            #         #     st.write(f"  📝 카테고리 지정 당시 캡션: {cat['caption']}")
            #     annotated_text("category: ", (cat_str, "", "#8ef"), "")

            st.write(bookmark.get("url", ""))
            st.write(bookmark.get("caption", ""))
            
            if "hashtags" in bookmark:
                tags = " ".join([f"#{tag}" for tag in bookmark["hashtags"]])
                st.write(f"tags: {tags}")
            
            # # 날짜 표시
            # created_at = datetime.fromisoformat(bookmark["created_at"])
            # st.caption(f"저장일: {created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # # 북마크 삭제 버튼
            # if st.button("삭제", key=f"delete_{bookmark['id']}"):
            #     if db.delete_bookmark(bookmark["id"]):
            #         vector_store.delete_bookmark(bookmark["id"])
            #         st.success("북마크가 삭제되었습니다.")
            #         st.rerun()

        # if debug:
        st.info(f"이 게시물을 추천한 이유: {reasons[i].split('/')[-1]}")
        
        st.markdown("---")