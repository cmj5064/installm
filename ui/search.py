import streamlit as st
from .bookmark_viewer import BookmarkViewer

class SearchUI:
    def __init__(self, db, vector_store):
        """검색 UI 초기화
        
        Args:
            db: 데이터베이스 관리자 인스턴스
            vector_store: 벡터 스토어 인스턴스
        """
        self.db = db
        self.vector_store = vector_store
        self.bookmark_viewer = BookmarkViewer(db)
    
    def show(self):
        """검색 UI 표시"""
        st.header("북마크 검색")
        
        # 검색 유형 선택
        search_type = st.radio(
            "검색 방식",
            ["텍스트 검색", "의미 검색"],
            horizontal=True
        )
        
        # 검색어 입력
        query = st.text_input("검색어를 입력하세요")
        
        if query:
            if search_type == "텍스트 검색":
                # 간단한 텍스트 검색
                bookmarks = self.db.search_bookmarks(query)
                st.subheader(f"'{query}' 검색 결과: {len(bookmarks)}개")
                self.bookmark_viewer.display_bookmarks(bookmarks)
            
            else:  # 의미 검색
                # 벡터 검색
                st.subheader(f"'{query}' 관련 내용 검색 결과")
                
                try:
                    results = self.vector_store.semantic_search(query, top_k=15)
                    
                    if results:
                        bookmarks = []
                        for result in results:
                            bookmark_id = int(result["id"])
                            bookmark = self.db.get_bookmark_by_id(bookmark_id)
                            
                            if bookmark:  # 때때로 ID는 있지만 실제 북마크가 없는 경우도 있음
                                # 유사도 점수 추가
                                bookmark["similarity"] = result["score"]
                                bookmarks.append(bookmark)
                        
                        st.write(f"총 {len(bookmarks)}개의 관련 북마크를 찾았습니다")
                        self.bookmark_viewer.display_bookmarks(bookmarks)
                    else:
                        st.info("검색 결과가 없습니다.")
                        
                except Exception as e:
                    st.error(f"검색 중 오류가 발생했습니다: {e}")
                    st.warning("벡터 스토어를 구축해야 의미 검색이 가능합니다. '북마크 추가' 메뉴를 활용하여 구축해주세요.")