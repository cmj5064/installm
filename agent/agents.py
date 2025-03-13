from typing import List, Dict, Any
from .prompts import FilteringPrompt
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

class FilteringAgent:
    """검색 결과 필터링을 위한 에이전트"""
    
    def __init__(self):
        """
        검색 결과 필터링 에이전트 초기화
        """
        self.llm = llm 
        self.response = None
        self.output_format = None
        
    def filter(self, query: str, bookmarks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLM을 사용하여 검색어와 북마크 데이터를 처리합니다.
        
        Args:
            query: 검색어
            bookmarks: 필터링할 북마크 리스트
            
        Returns:
            상태 정보를 포함한 딕셔너리
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
        
        # 출력 형식 저장
        self.output_format = prompt.OutputFormat
        
        # 프롬프트 구성
        chat_messages = [
            ("system", system_prompt),
            ("human", user_prompt)
        ]
        
        # LLM 호출 및 결과 저장
        self.response = self.llm.invoke(chat_messages).content
        
        return state
    
    def parser(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM 응답을 구조화된 데이터로 파싱합니다.
        
        Args:
            state: 현재 상태 정보
            
        Returns:
            필터링 결과가 추가된 상태 정보
        """
        try:
            # 파싱을 위한 프롬프트 구성
            parsing_prompt = f"""
            앞서 생성된 응답을 구조화된 형식으로 파싱하세요:
            
            응답: {self.response}
            
            위 응답으로부터 관련 있는 북마크의 index를 추출하여 list로 만드세요.
            """
            
            # 구조화된 LLM 생성
            structured_llm = self.llm.with_structured_output(self.output_format)
            
            # 파싱 수행
            chat_messages = [
                ("system", "당신은 텍스트에서 정보를 추출하여 구조화된 형식으로 변환하는 전문가입니다."),
                ("human", parsing_prompt)
            ]
            
            result = structured_llm.invoke(chat_messages)
            
            # 결과에서 북마크 인덱스 추출 (문자열 리스트에서 정수로 변환)
            relevant_indices = [int(idx) for idx in result.bookmark_indexes]
            
            # 유효한 인덱스만 필터링 (범위 체크)
            valid_indices = [idx for idx in relevant_indices if 0 <= idx < len(state["bookmarks"])]
            
            # 인덱스가 비어있으면 원본 반환
            if not valid_indices:
                print("필터링 결과가 없습니다. 원본 북마크를 반환합니다.")
                state["filtered_bookmarks"] = state["bookmarks"]
            else:
                # 관련 있는 북마크만 필터링하여 반환
                state["filtered_bookmarks"] = [state["bookmarks"][idx] for idx in valid_indices]
                
        except Exception as e:
            print(f"파싱 중 오류 발생: {e}")
            # 오류 발생 시 원본 북마크 반환
            state["filtered_bookmarks"] = state["bookmarks"]
            
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
            
            # 파싱 단계
            state = self.parser(state)
            
            return state["filtered_bookmarks"]
            
        except Exception as e:
            print(f"필터링 과정에서 오류 발생: {e}")
            return bookmarks