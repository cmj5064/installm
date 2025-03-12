import streamlit as st
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from utils.helpers import log_error, log_info
from dotenv import load_dotenv
import os

# .env 파일에서 환경 변수 로드
load_dotenv()

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
            show_confidence: 카테고리 신뢰도 표시 여부수빈 
        """
        bookmark_id = bookmark["id"]
        thumbnail_url = bookmark["thumbnail_url"]
        caption = bookmark.get("caption", "") or ""
        media_type = bookmark.get("media_type", "")
        taken_at = bookmark.get("taken_at", "")
        
        # 카테고리 정보 가져오기
        categories = "" # TODO 유저한테 받아오던지 하여튼 처리 필요
        
        # 썸네일 이미지
        if thumbnail_url:
            # 직접 이미지 URL을 사용해 표시
            try:
                st.image(thumbnail_url, width=300, use_container_width=True)
                log_info(f"st.image 로드 성공: {thumbnail_url}")
            except Exception as e:
                log_error((f"st.image 이미지 로드 실패: {str(e)}"))
                
                # 이미지 로드 실패 시 웹서버 프록시 사용
                try:
                    proxy_url = f"https://images.weserv.nl/?url={thumbnail_url}"
                    st.image(proxy_url, width=300)
                    log_info(f"proxy_url로 st.image 로드 성공: {thumbnail_url}")
                except Exception as e:
                    log_error(f"프록시 이미지도 실패: {str(e)}")
                    # 마지막 수단으로 Instagram URL에서 이미지 추출 시도
                    if "url" in bookmark:
                        self.get_instagram_image(bookmark["thumbnail_url"], bookmark["url"])
        
        # # 북마크 제목 (캡션 앞부분)
        # title = caption[:30] + "..." if len(caption) > 30 else caption
        # st.write(f"{title}")
        
        # # 카테고리 태그
        # if categories:
        #     cat_labels = []
        #     for cat in categories[:3]:  # 최대 3개 카테고리만 표시
        #         if show_confidence:
        #             cat_labels.append(f"{cat['name']} ({cat['confidence']:.2f})")
        #         else:
        #             cat_labels.append(cat['name'])
                    
        #     st.write(" | ".join(cat_labels))

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
        
        # 상세 보기 버튼
        if st.button("상세보기", key=f"detail_{bookmark_id}"):
            st.session_state.selected_bookmark = bookmark_id
            st.rerun()

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
                st.rerun()
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
                img = self.get_instagram_image(bookmark["thumbnail_url"], bookmark["url"])
                try:
                    st.image(img, width=300)
                except:
                    st.error(f"이미지 사용 불가: {Exception}")
        
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
            
            # # 카테고리 정보
            # categories = self.db.get_bookmark_categories(bookmark_id)
            # if categories:
            #     st.subheader("카테고리")
            #     for cat in categories:
            #         st.write(f"- {cat['name']} ({cat['confidence']:.2f})")
        
        # 캡션 표시
        caption = bookmark.get("caption", "")
        if caption:
            st.subheader("캡션")
            st.text_area("", value=caption, height=200, disabled=True)

    def get_instagram_image(self, img_url, url):
        """Instagram 페이지에서 이미지 추출"""
        self.logger.info(f"Instagram 이미지 추출 시도: {url}")
        st.write("**1. Facebook Graph API를 통한 Instagram 데이터 가져오기:**")
        
        # access_token = st.secrets.get("INSTA_API_TOKEN", "")
        access_token = os.getenv("INSTA_API_TOKEN")
        
        if not access_token:
            st.error("Facebook/Instagram API 액세스 토큰이 설정되지 않았습니다.")
            return None
        
        try:
            # Instagram 포스트 URL에서 ID 추출
            import re
            post_id = re.search(r"/p/([^/]+)/", url)
            if not post_id:
                st.error("올바른 Instagram 포스트 URL이 아닙니다.")
                return None
            
            post_id = post_id.group(1)
            
            # Facebook Graph API를 통해 oEmbed 정보 가져오기
            oembed_url = f"https://graph.facebook.com/v16.0/instagram_oembed"
            params = {
                "url": url,
                "access_token": access_token,
                "fields": "thumbnail_url,author_name,provider_name"
            }
            
            response = requests.get(oembed_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if "thumbnail_url" in data:
                img_url = data["thumbnail_url"]
                st.image(img_url, width=300, caption=f"Instagram 이미지: {data.get('author_name', '')}")
                return img_url
            else:
                st.warning("썸네일 URL을 찾을 수 없습니다.")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 요청 오류: {str(e)}")
            st.error(f"API 요청 오류: {str(e)}")
        except ValueError as e:
            self.logger.error(f"JSON 파싱 오류: {str(e)}")
            st.error(f"데이터 파싱 오류: {str(e)}")
        except Exception as e:
            self.logger.error(f"오류 발생: {str(e)}")
            st.error(f"오류 발생: {str(e)}")
        
        return None