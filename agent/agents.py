from typing import List, Dict, Any, Optional
from .prompts import FilteringPrompt, CategoryPrompt
from dotenv import load_dotenv
import os
from langchain_openai import AzureChatOpenAI

# .env 파일에서 환경 변수 로드
load_dotenv()

llm = AzureChatOpenAI(
    openai_api_key=os.getenv("AOAI_API_KEY"),
    azure_endpoint=os.getenv("AOAI_ENDPOINT"),
    azure_deployment=os.getenv("AOAI_DEPLOY_GPT4O_MINI"),
    api_version="2024-08-01-preview",
    temperature=0.5,
)

class CategorizeAgent:
    """북마크의 카테고리를 분류하는 에이전트"""
    
    def __init__(self):
        self.llm = llm
        
        # 기본 카테고리 목록
        self.base_categories = [] # app.py 57 line
    
    def _update_base_categories(self, category: str) -> None:
        """기본 카테고리 세트에 새 카테고리를 추가합니다."""
        if not category:
            return
            
        if category not in self.base_categories:
            self.base_categories.append(category)
            print(f"새로운 카테고리 추가됨: {category}")

    def classify(self, caption: str, hashtags: Optional[List[str]] = None) -> CategoryPrompt.OutputFormat:
        """
        인스타그램 캡션과 해시태그를 분석하여 카테고리를 분류합니다.
        단일 카테고리를 string 형태로 반환합니다.
        """
        try:
            prompt = CategoryPrompt(
                caption=caption, 
                hashtags=hashtags or [],
                base_categories=self.base_categories
            )
            
            chat_messages = [
                {"role": "system", "content": prompt.get_system_prompt()},
                {"role": "user", "content": prompt.get_user_prompt()}
            ]
            
            response = self.llm.with_structured_output(
                CategoryPrompt.OutputFormat
            ).invoke(chat_messages)
            
            self._update_base_categories(response.categories)
            
            # 원본 Pydantic 객체 반환
            return response
            
        except Exception as e:
            print(f"카테고리 분류 중 예상치 못한 오류: {e}")
            # 오류 발생 시 Pydantic 객체 직접 생성하여 반환
            fallback_result = prompt.OutputFormat(
                categories="기타",
                category_reason=f"분류 오류: {str(e)}"
            )
            return fallback_result
    
    def classify_batch(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """여러 북마크의 카테고리를 일괄 분류합니다.
        
        Args:
            bookmarks: 북마크 목록
            
        Returns:
            카테고리가 추가된 북마크 목록
        """
        for bookmark in bookmarks:
            caption = bookmark.get('caption', '')
            hashtags = bookmark.get('hashtags', [])
            
            if caption or hashtags:
                # classify 메서드가 반환하는 Pydantic 모델에서 속성 접근
                response = self.classify(caption, hashtags)
                bookmark['categories'] = response.categories
                bookmark['category_reason'] = response.category_reason
        
        return bookmarks

class FilterAgent:
    """검색 결과 필터링을 위한 에이전트"""
    
    def __init__(self):
        """
        검색 결과 필터링 에이전트 초기화
        """
        self.llm = llm
        
    def filter(self, query: str, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        LLM을 사용하여 검색어와 북마크 데이터를 처리합니다.
        
        Args:
            query: 검색어
            bookmarks: 필터링할 북마크 리스트
            
        Returns:
            필터링 결과가 추가된 상태 정보
        """
        # 상태 정보를 딕셔너리 형태로 관리
        state = {
            "query": query,
            "bookmarks": bookmarks,
            "filtered_bookmarks": None,
            "filter_reasons":None
        }
        
        # FilteringPrompt 인스턴스 생성
        prompt = FilteringPrompt(query=query, bookmarks=bookmarks)
        
        # 시스템 프롬프트와 사용자 프롬프트 가져오기
        system_prompt = prompt.get_system_prompt()
        user_prompt = prompt.get_user_prompt()
        
        # 프롬프트 구성
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # LLM 호출 및 구조화된 출력 처리
        response = self.llm.with_structured_output(prompt.OutputFormat).invoke(chat_messages)

        # 결과에서 북마크 인덱스 추출 (문자열 리스트에서 정수로 변환)
        try:
            # 딕셔너리로 반환되는 경우
            if isinstance(response, dict) and "bookmark_indexes" in response:
                relevant_indices = [int(idx) for idx in response["bookmark_indexes"]]
            # Pydantic 모델로 반환되는 경우
            else:
                relevant_indices = [int(idx) for idx in response.bookmark_indexes]
        except AttributeError:
            print("응답 형식이 예상과 다릅니다. 원본 북마크를 반환합니다.")
            state["filtered_bookmarks"] = state["bookmarks"]
            return state
        
        # 유효한 인덱스만 필터링 (범위 체크)
        valid_indices = [idx for idx in relevant_indices if 0 <= idx < len(state["bookmarks"])]
        
        # 인덱스가 비어있으면 원본 반환
        if not valid_indices:
            print("필터링 결과가 없습니다. 원본 북마크를 반환합니다.")
            state["filtered_bookmarks"] = state["bookmarks"]
        else:
            # 관련 있는 북마크만 필터링하여 반환
            state["filtered_bookmarks"] = [state["bookmarks"][idx] for idx in valid_indices]
            state["filter_reasons"] = [r for r in response.filter_reasons]
    
        return state
    
    def run(self, query: str, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색어와 관련 있는 북마크만 필터링하여 반환합니다.
        
        Args:
            query: 검색어
            bookmarks: 필터링할 북마크 리스트
            
        Returns:
            필터링된 북마크 리스트
        """
        try:
            # 필터링 단계
            state = self.filter(query, bookmarks)
            
            # return state["filtered_bookmarks"]
            return state
            
        except Exception as e:
            print(f"필터링 과정에서 오류 발생: {e}")
            return bookmarks