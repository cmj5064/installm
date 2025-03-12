import streamlit as st
from datetime import datetime

class BookmarkViewer:
    def __init__(self, db):
        """북마크 뷰어 초기화
        
        Args:
            db: 데이터베이스 관리자 인스턴스
        """
        self.db = db
    
    def show_recent(self):
        """최근 북마크 표시"""
        st.header("최근 북마크")
        
        # 전체 북마크 수 가져오기
        total_bookmarks = self.db.get_total_bookmark_count()
        
        # 페이지네이션 설정
        per_page = 20
        total_pages = (total_bookmarks + per_page - 1) // per_page
        
        # 페이지 선택
        current_page = st.number_input("페이지", min_value=1, max_value=max(1, total_pages), value=1)
        
        # 북마크 가져오기
        bookmarks = self.db.get_paginated_bookmarks(page=current_page, per_page=per_page)
        
        # 북마크 표시
        st.subheader(f"북마크 목록 (페이지 {current_page}/{total_pages})")
        self.display_bookmarks(bookmarks)
        
        # 페이지 네비게이션
        col1, col2 = st.columns(2)
        with col1:
            if current_page > 1:
                if st.button("이전 페이지"):
                    st.experimental_rerun()  # 이전 페이지로 이동
        with col2:
            if current_page < total_pages:
                if st.button("다음 페이지"):
                    st.experimental_rerun()  # 다음 페이지로 이동
    
    def display_bookmarks(self, bookmarks, show_confidence=False):
        """북마크 목록 표시
        
        Args:
            bookmarks: 북마크 목록
            show_confidence: 카테고리 신뢰도 표시 여부
        """
        if not bookmarks:
            st.info("표시할 북마크가 없습니다.")
            return
        
        # 북마크를 그리드 형식으로 표시
        num_columns = 4 # 한 행에 표시할 북마크 수
        
        for i in range(0, len(bookmarks), num_columns):
            row_bookmarks = bookmarks[i:i+num_columns]
            cols = st.columns(num_columns)
            
            for j, bookmark in enumerate(row_bookmarks):
                with cols[j]:
                    self.display_bookmark_card(bookmark, show_confidence)
    
        def display_bookmark_card(self, bookmark, show_confidence=False):
            """북마크 카드 표시
            
            Args:
                bookmark: 북마크 정보
                show_confidence: 카테고리 신뢰도 표시 여부
            """
            bookmark_id = bookmark["id"]
            thumbnail_url = bookmark["thumbnail_url"]
            caption = bookmark.get("caption", "") or ""
            media_type = bookmark.get("media_type", "")
            taken_at = bookmark.get("taken_at", "")
            
            # 카테고리 정보 가져오기
            categories = self.db.get_bookmark_categories(bookmark_id)
            
            # 썸네일 이미지
            if thumbnail_url:
                st.image(thumbnail_url, width=150)
            
            # 북마크 제목 (캡션 앞부분)
            title = caption[:30] + "..." if len(caption) > 30 else caption
            st.write(f"**{title}**")
            
            # 카테고리 태그
            if categories:
                cat_labels = []
                for cat in categories[:3]:  # 최대 3개 카테고리만 표시
                    if show_confidence:
                        cat_labels.append(f"{cat['name']} ({cat['confidence']:.2f})")
                    else:
                        cat_labels.append(cat['name'])
                        
                st.write(" | ".join(cat_labels))
            
            # 상세 보기 버튼
            if st.button("상세보기", key=f"detail_{bookmark_id}"):
                st.session_state.selected_bookmark = bookmark_id
                st.experimental_rerun()
    
        def show_bookmark_detail(self, bookmark_id):
            """북마크 상세 정보 표시
            
            Args:
                bookmark_id: 북마크 ID
            """
            bookmark = self.db.get_bookmark_by_id(bookmark_id)
            
            if not bookmark:
                st.error("북마크를 찾을 수 없습니다.")
                if st.button("돌아가기"):
                    st.session_state.selected_bookmark = None
                    st.experimental_rerun()
                return
            
            # 뒤로가기 버튼
            if st.button("목록으로 돌아가기"):
                st.session_state.selected_bookmark = None
                st.experimental_rerun()
            
            # 북마크 상세정보 표시
            st.header("북마크 상세정보")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if bookmark.get("thumbnail_url"):
                    st.image(bookmark["thumbnail_url"], width=300)
            
            with col2:
                st.subheader("정보")
                st.write(f"**미디어 유형:** {bookmark.get('media_type', '정보 없음')}")
                
                # 날짜 포맷팅
                taken_at = bookmark.get("taken_at")
                if taken_at:
                    try:
                        taken_date = datetime.fromisoformat(taken_at)
                        formatted_date = taken_date.strftime("%Y년 %m월 %d일 %H:%M")
                        st.write(f"**저장일:** {formatted_date}")
                    except:
                        st.write(f"**저장일:** {taken_at}")
                
                st.write(f"**좋아요 수:** {bookmark.get('like_count', 0)}")
                
                # 카테고리 정보
                categories = self.db.get_bookmark_categories(bookmark_id)
                if categories:
                    st.subheader("카테고리")
                    for cat in categories:
                        st.write(f"- {cat['name']} ({cat['confidence']:.2f})")
            
            # 캡션 표시
            caption = bookmark.get("caption", "")
            if caption:
                st.subheader("캡션")
                st.text_area("", value=caption, height=200, disabled=True)