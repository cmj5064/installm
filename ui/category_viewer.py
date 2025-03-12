import streamlit as st

class CategoryViewUI:
    def __init__(self, db):
        """카테고리 뷰 UI 초기화
        
        Args:
            db: 데이터베이스 관리자 인스턴스
        """
        self.db = db
    
    def show(self, category_names):
        """카테고리별 북마크 표시
        
        Args:
            category_names: 모든 카테고리 이름 목록
        """
        st.header("카테고리별 보기")
        
        if not category_names:
            st.info("카테고리가 없습니다.")
            return
            
        # 카테고리 선택
        selected_category = st.selectbox("카테고리 선택", category_names)
        
        if selected_category:
            # 데이터베이스에서 해당 카테고리의 북마크 가져오기
            conn = self.db.db_path
            bookmarks = self._get_bookmarks_by_category(selected_category)
            
            st.subheader(f"{selected_category} 카테고리의 북마크")
            
            if not bookmarks:
                st.info(f"{selected_category} 카테고리에 북마크가 없습니다.")
                return
                
            # 북마크 표시 UI 사용
            from .bookmark_viewer import BookmarkViewer
            viewer = BookmarkViewer(self.db)
            viewer.display_bookmarks(bookmarks, show_confidence=True)
    
    def _get_bookmarks_by_category(self, category_name):
        """카테고리별 북마크 가져오기
        
        Args:
            category_name: 카테고리 이름
            
        Returns:
            북마크 목록
        """
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT b.id, b.media_type, b.caption, b.like_count, b.thumbnail_url, b.taken_at, bc.confidence
        FROM bookmarks b
        JOIN bookmark_categories bc ON b.id = bc.bookmark_id
        JOIN categories c ON bc.category_id = c.id
        WHERE c.name = ?
        ORDER BY bc.confidence DESC
        """, (category_name,))
        
        bookmarks = [dict(id=row[0], media_type=row[1], caption=row[2], 
                         like_count=row[3], thumbnail_url=row[4], 
                         taken_at=row[5], confidence=row[6]) for row in cursor.fetchall()]
        
        conn.close()
        return bookmarks