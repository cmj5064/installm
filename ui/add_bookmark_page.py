import os
import streamlit as st
import hydralit_components as hc

theme_good = {'bgcolor': '#EFF8F7','title_color': 'green','content_color': 'green','icon_color': 'green', 'icon': 'fa fa-check-circle'}

def render_add_bookmark_page(db, vector_store, categorize_agent, debug):
    """북마크 DB 및 벡터 스토어 저장 페이지"""
    if debug:
        st.write(f"페이지: {st.session_state.current_menu}, 세션 ID: {st.session_state.get('session_id', '없음')}")
        st.write(f"DB 저장 상태: {st.session_state.get('db_saved', False)}")

    # st.header("북마크 추가")
    
    # 인스타그램 로그인 여부 확인
    if 'insta_logged_in' not in st.session_state or not st.session_state.insta_logged_in:
        st.warning("먼저 인스타그램에 로그인해야 합니다.")
        if st.button("로그인 페이지로 이동"):
            st.session_state.current_menu = "랜딩 페이지"
            st.query_params.menu = "랜딩 페이지"
            st.rerun()
        return
    
    # 북마크가 로드되었는지 확인
    if 'fetched_bookmarks' not in st.session_state:
        st.warning("먼저 북마크를 불러와야 합니다.")
        if st.button("북마크 불러오기 페이지로 이동"):
            st.session_state.current_menu = "랜딩 페이지"
            st.rerun()
        return
    
    # 북마크 처리 현황 표시
    # TODO vector_store 내 feed_id 체크...? 가능?
    vs_index = "./data/faiss_index/bookmark_vectors.index"
    vs_mapping = "./data/faiss_index/id_mapping.json"
    if os.path.exists(vs_index) and os.path.exists(vs_mapping):
        st.session_state.vector_saved = True

    # db 및 vector store 저장 현황 표시
    with st.expander("DB 및 Vector Store 저장 현황"):
        st.write(f"""
        {"✅" if 'db_saved' in st.session_state else "❌"}      DB\n
        {"✅" if 'vector_saved' in st.session_state else "❌"}  Vector Store
        """)
        # st.checkbox("DB", value=False, disabled=True)
    
    # 북마크가 불러와졌고 DB에 저장되지 않은 경우에만 DB 저장 버튼 표시
    if 'db_saved' not in st.session_state:
        if st.button("북마크 DB 저장", key="save_to_db"):
            with st.spinner('북마크를 데이터베이스에 저장하는 중...'):
                success_count, fail_count = db.add_bookmark_batch(
                    st.session_state.fetched_bookmarks,
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

    if debug: # NOTE 전체 북마크의 카테고리 업데이트는 debug에서만 수행
        if st.button("북마크 카테고리 분류", key="save_category_to_db"):
            with st.spinner('북마크의 카테고리를 분류하여 데이터베이스에 저장하는 중...'):
                success_count, fail_count = db.categorize_bookmark_batch(
                    st.session_state.fetched_bookmarks,
                    categorize_agent=categorize_agent
                )
            
            if success_count > 0:
                st.success(f"{success_count}개의 북마크의 카테고리가 분류되어 DB에 저장되었습니다.")
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
    if 'db_saved' in st.session_state and 'vector_saved' not in st.session_state:
        if st.button("벡터 스토어에 북마크 저장", key="save_to_vector"):
            with st.spinner('북마크를 벡터 스토어에 저장하는 중...'):
                success_vector = vector_store.add_bookmark_batch(st.session_state.successful_bookmarks)
            
            if success_vector:
                st.session_state.vector_saved = True
                st.success(f"{len(st.session_state.successful_bookmarks)}개의 북마크가 벡터 스토어에 저장되었습니다.")
                st.rerun()  # 상태 표시 업데이트를 위한 리로드
            else:
                st.error("벡터 스토어 저장에 실패했습니다.")
    
    # 모든 저장 과정이.완료된 경우 완료 메시지와 북마크 리스트 표시
    if 'db_saved' in st.session_state and 'vector_saved' in st.session_state:
        st.success("모든 북마크가 성공적으로 저장되었습니다!")

        # 저장된 북마크 정보 미리보기 표시
        if 'successful_bookmarks' in st.session_state and len(st.session_state.successful_bookmarks) > 0:
            with st.expander("저장된 북마크 미리보기"):
                for i, bookmark in enumerate(st.session_state.successful_bookmarks[:5]):  # 처음 5개만 표시
                    st.markdown(f"**북마크 #{i+1}**")
                    st.markdown(f"**게시물 ID:** {bookmark.get('feed_id', 'N/A')}")
                    st.markdown(f"**카테고리:**   {bookmark.get('category', 'N/A')}")
                    st.markdown(f"**내용:** {bookmark.get('caption', 'N/A')[:100]}...")
                    st.markdown("---")
                
                if len(st.session_state.successful_bookmarks) > 5:
                    st.markdown(f"... 외 {len(st.session_state.successful_bookmarks) - 5}개")
        
        # # 북마크 목록으로 이동 버튼
        # if st.button("북마크 목록으로 이동"):
        #     st.session_state.current_menu = "북마크 목록"
        #     # 세션에서 처리 중간 상태 정보 제거
        #     if 'fetched_bookmarks' in st.session_state:
        #         del st.session_state.fetched_bookmarks
        #     if 'db_saved' in st.session_state:
        #         del st.session_state.db_saved
        #     if 'vector_saved' in st.session_state:
        #         del st.session_state.vector_saved
        #     if 'successful_bookmarks' in st.session_state:
        #         del st.session_state.successful_bookmarks
        #     st.rerun()

        # col1, col2, _, _, _, _, _, _ = st.columns(8, vertical_alignment="bottom")
        col1, col2, _ = st.columns([0.1, 0.1, 0.8], gap="small")

        with col1:
            if st.button("북마크 검색"):
                st.session_state.current_menu = "북마크 검색"
                st.query_params.menu = "북마크 검색"
                st.rerun()
        
        with col2:       
            # 랜딩 페이지로 이동 버튼
            if st.button("초기화"):
                st.session_state.current_menu = "랜딩 페이지"
                # 세션에서 처리 중간 상태 정보 제거
                if 'fetched_bookmarks' in st.session_state:
                    del st.session_state.fetched_bookmarks
                if 'db_saved' in st.session_state:
                    del st.session_state.db_saved
                if 'vector_saved' in st.session_state:
                    del st.session_state.vector_saved
                if 'successful_bookmarks' in st.session_state:
                    del st.session_state.successful_bookmarks
                st.rerun()

    # 처리 중간에 취소 옵션
    if ('fetched_bookmarks' in st.session_state and 
        ('db_saved' not in st.session_state or 'vector_saved' not in st.session_state)):
        st.markdown("---")
        # if st.button("처리 취소하고 처음으로 돌아가기", key="cancel_process"):
        if st.button("처음으로 돌아가기", key="cancel_process"):
            # 세션에서 처리 중간 상태 정보 제거
            if 'fetched_bookmarks' in st.session_state:
                del st.session_state.fetched_bookmarks
            if 'db_saved' in st.session_state:
                del st.session_state.db_saved
            if 'vector_saved' in st.session_state:
                del st.session_state.vector_saved
            if 'successful_bookmarks' in st.session_state:
                del st.session_state.successful_bookmarks
            
            st.session_state.current_menu = "랜딩 페이지"
            st.rerun()