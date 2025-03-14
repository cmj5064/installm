from typing import List, Dict, Any
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
    temperature=0.0,
)

class CategorizeAgent:
    """북마크의 카테고리를 분류하는 에이전트"""
    
    def __init__(self):
        self.llm = llm
        
        # 기본 카테고리 목록
        self.base_categories = ["여행", "맛집", "개구리"] # TODO: 초기 세팅 혹은 db가 있는 경우 db에 존재하는 카테고리 list 받아오기
    
    def _update_base_categories(self, new_categories: List[str]) -> None:
        """새로운 카테고리를 기본 카테고리 목록에 추가합니다.
        
        Args:
            new_categories: 추가할 새로운 카테고리 목록
        """
        for category in new_categories:
            if category not in self.base_categories:
                self.base_categories.append(category)
                print(f"새로운 카테고리 추가됨: {category}")
    
    def classify(self, caption: str, hashtags: List[str]) -> CategoryPrompt.OutputFormat:
        """게시물의 카테고리를 분류합니다.
        
        Args:
            caption: 게시물 설명
            hashtags: 해시태그 목록
            
        Returns:
            분류된 카테고리 정보
        """
        # CategoryPrompt 인스턴스 생성
        prompt = CategoryPrompt(
            caption=caption,
            hashtags=hashtags,
            base_categories=self.base_categories
        )
        
        # 프롬프트 구성
        chat_messages = [
            ("system", prompt.get_system_prompt()),
            ("human", prompt.get_user_prompt())
        ]

        # LLM chain 생성
        chain = chat_messages | self.llm | prompt.OutputFormat
        response = chain.invoke()
        
        # 새로운 카테고리가 있다면 base_categories에 추가
        self._update_base_categories([name for name in response["categories"] if name not in self.base_categories])
        
        return response
    
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
                response = self.classify(caption, hashtags)
                bookmark['categories'] = response["categories"]
                bookmark['category_reason'] = response["category_reason"]
        
        return bookmarks

class FilterAgent:
    """검색 결과 필터링을 위한 에이전트"""
    
    def __init__(self):
        """
        검색 결과 필터링 에이전트 초기화
        """
        self.llm = llm
        
    def filter(self, query: str, bookmarks: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            "filtered_bookmarks": None
        }
        
        # FilteringPrompt 인스턴스 생성
        prompt = FilteringPrompt(query=query, bookmarks=bookmarks)
        
        # 시스템 프롬프트와 사용자 프롬프트 가져오기
        system_prompt = prompt.get_system_prompt()
        user_prompt = prompt.get_user_prompt()
        
        # 프롬프트 구성
        chat_messages = [
            ("system", system_prompt),
            ("human", user_prompt)
        ]

        # # 구조화된 LLM 생성
        # structured_llm = self.llm.with_structured_output(prompt.OutputFormat)
        
        # # LLM 호출 및 결과 저장
        # response = structured_llm.invoke(chat_messages)

        # LLM chain 생성성
        chain = chat_messages | self.llm | prompt.OutputFormat

        response = chain.invoke()

        # 결과에서 북마크 인덱스 추출 (문자열 리스트에서 정수로 변환)
        relevant_indices = [int(idx) for idx in response["bookmark_indexes"]]
        
        # 유효한 인덱스만 필터링 (범위 체크)
        valid_indices = [idx for idx in relevant_indices if 0 <= idx < len(state["bookmarks"])]
        
        # 인덱스가 비어있으면 원본 반환
        if not valid_indices:
            print("필터링 결과가 없습니다. 원본 북마크를 반환합니다.")
            state["filtered_bookmarks"] = state["bookmarks"]
        else:
            # 관련 있는 북마크만 필터링하여 반환
            state["filtered_bookmarks"] = [state["bookmarks"][idx] for idx in valid_indices]
    
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
            
            return state["filtered_bookmarks"]
            
        except Exception as e:
            print(f"필터링 과정에서 오류 발생: {e}")
            return bookmarks