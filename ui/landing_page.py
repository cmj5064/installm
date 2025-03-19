import streamlit as st
from utils.instagram import InstagramClient
from utils.helpers import log_error

def render_landing_page(db, vector_store, debug):
    """인스타그램 로그인 및 북마크 로드 페이지"""
    # 간소화된 사이드바 스타일 설정
    # langding_page_css = """
    # <style>
    # /* 버튼 스타일링 */
    # .stButton button {
    #     width: 46px;
    #     height: 46px;
    #     border-radius: 50%;
    #     display: flex;
    #     align-items: center;
    #     justify-content: center;
    #     background-color: white;
    #     border: none;
    #     margin: 10px auto;
    #     font-size: 18px;
    #     padding: 0;
    #     transition: all 0.2s;
    # }

    # .stButton button:hover {
    #     background-color: #f8f8f8;
    #     transform: scale(1.1);
    #     /* 호버 시 컬러로 변경 (선택 사항) */
    #     filter: grayscale(0%);
    # }
    # </style>
    # """

    # st.markdown(langding_page_css, unsafe_allow_html=True)

    if debug:
        st.write(f"페이지: {st.session_state.current_menu}, 세션 ID: {st.session_state.get('session_id', '없음')}")
        st.write(f"DB 저장 상태: {st.session_state.get('db_saved', False)}")
        st.write(f"VS 저장 상태: {st.session_state.get('vector_saved', False)}")

    # st.header("Instagram 북마크 매니저")
    
    # Instagram 로그인 정보를 세션 상태에서 확인
    if 'insta_logged_in' not in st.session_state:
        st.session_state.insta_logged_in = False
    
    # 로그인 영역
    if not st.session_state.insta_logged_in:
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

        if st.button("로그아웃"):
            # 세션 상태에서 로그인 정보 제거
            if 'insta_id' in st.session_state:
                del st.session_state.insta_id
            if 'insta_pw' in st.session_state:
                del st.session_state.insta_pw
            st.session_state.insta_logged_in = False
            st.rerun()

        if 'fetched_bookmarks' not in st.session_state:

            with st.form(key="bookmark_form"):
                url = st.text_input("URL", f"https://www.instagram.com/{st.session_state.insta_id}/saved/all-posts/")
                bookmark_description = st.text_area("설명", f"{st.session_state.insta_id}의 북마크")
                submit_button = st.form_submit_button(label="북마크 불러오기")
                
            if submit_button and url:
                # spinner로 로딩 표시
                with st.spinner('Instagram에서 북마크를 불러오는 중...'):
                    success, bookmarks = fetch_bookmarks(url, bookmark_description)
                
                if success and bookmarks:
                    st.session_state.fetched_bookmarks = bookmarks
                    st.success(f"{len(bookmarks)}개의 북마크를 불러왔습니다!")
                    
                    # 북마크 상태 정보 표시
                    # NOTE db 저장 현황 확인 # TODO vector store 저장 현황도?
                    conn = db._get_connection()
                    cursor = conn.cursor()

                    new_ids = [] # 새로 추가된 feed_id list
                    for i, bookmark in enumerate(bookmarks):
                        feed_id = bookmark.get('feed_id')
                        bookmark_id = db._check_bookmark_exists(cursor, feed_id)
                        if not bookmark_id:
                            new_ids.append(feed_id)

                    conn.commit()
                    conn.close()

                    # # 북마크 처리 현황 표시
                    # if 'fetched_bookmarks' in st.session_state:
                    #     st.subheader("북마크 처리 상태")
                        
                    #     # 북마크 상태 정보를 2열 레이아웃으로 표시
                    #     col1, col2 = st.columns(2)
                        
                    #     # DB 저장 상태
                    #     with col1:
                    #         db_status = "✅ 저장 완료" if 'db_saved' in st.session_state else "⏳ 대기 중"
                    #         db_count = len(st.session_state.successful_bookmarks) if 'successful_bookmarks' in st.session_state else 0
                    #         db_color = "green" if 'db_saved' in st.session_state else "orange"
                            
                    #         st.markdown(f"""
                    #         <div style="padding: 10px; border-radius: 5px; border: 1px solid {db_color}; background-color: rgba(0,0,0,0.05)">
                    #             <h3 style="margin:0; color: {db_color}">📊 데이터베이스</h3>
                    #             <p style="margin:5px 0;">상태: {db_status}</p>
                    #             <p style="margin:5px 0;">저장된 북마크 수: {db_count}</p>
                    #         </div>
                    #         """, unsafe_allow_html=True)
                        
                    #     # 벡터 스토어 저장 상태
                    #     with col2:
                    #         vector_status = "✅ 저장 완료" if 'vector_saved' in st.session_state else "⏳ 대기 중"
                    #         vector_count = len(st.session_state.successful_bookmarks) if 'successful_bookmarks' in st.session_state and 'vector_saved' in st.session_state else 0
                    #         vector_color = "green" if 'vector_saved' in st.session_state else "orange"
                            
                    #         st.markdown(f"""
                    #         <div style="padding: 10px; border-radius: 5px; border: 1px solid {vector_color}; background-color: rgba(0,0,0,0.05)">
                    #             <h3 style="margin:0; color: {vector_color}">🔍 벡터 스토어</h3>
                    #             <p style="margin:5px 0;">상태: {vector_status}</p>
                    #             <p style="margin:5px 0;">저장된 북마크 수: {vector_count}</p>
                    #         </div>
                    #         """, unsafe_allow_html=True)

                    if new_ids:
                        st.info(f"새로운 북마크가 {len(new_ids)}개 추가 되었습니다!")
                        st.session_state.fetched_bookmarks = new_ids # 신규 북마크만 추가하도록 갱신

                        # 북마크 추가 페이지로 이동 버튼
                        if st.button("신규 북마크 저장"):
                            st.session_state.current_menu = "북마크 추가"
                            st.query_params.menu = "북마크 추가"
                            st.rerun()
                        
                    else: # 중복되는 id만 있는 경우
                        st.session_state.db_saved = True
                        if st.button("북마크 검색"):
                            st.session_state.current_menu = "북마크 검색"
                            st.query_params.menu = "북마크 검색"
                            st.rerun()
                    
                else:
                    st.error("북마크를 불러오는 중 오류가 발생했습니다.")
        else:
            if st.button("북마크 검색"):
                st.session_state.current_menu = "북마크 검색"
                st.query_params.menu = "북마크 검색"
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
        return True, bookmark_data
    
    except Exception as e:
        log_error(f"북마크 불러오기 중 오류: {e}")
        return False, None