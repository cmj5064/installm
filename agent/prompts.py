from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel, Field


class AgentPrompt(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def get_system_prompt(self):
        pass

    @abstractmethod
    def get_user_prompt(self):
        pass


class CategoryPrompt(AgentPrompt):
    """카테고리 분류 에이전트를 위한 프롬프트"""
    class OutputFormat(BaseModel):
        """카테고리 분류 에이전트의 출력을 파싱하는 클래스"""
        categories: List[str] = Field(
            description="게시물에 할당할 카테고리 이름 목록 (최대 3개)"
        )
        category_reason: str = Field(
            description="카테고리 분류 이유"
        )
    
    def __init__(
        self, caption: str, hashtags: List[str], base_categories: List[str]
    ) -> None:
        self.caption = caption
        self.hashtags = hashtags
        self.base_categories = base_categories

    def get_system_prompt(self) -> str:
        system_prompt = (
            "당신은 Instagram 게시물의 카테고리를 분류하는 전문가입니다.\n"
            "게시물의 내용과 해시태그를 분석하여 가장 적절한 카테고리를 할당해야 합니다.\n"
            "다음 사항을 고려하세요:\n"
            "1. 게시물의 주요 주제와 내용을 파악하세요\n"
            "2. 해시태그의 의미를 고려하세요\n"
            "3. 기본 카테고리 중 가장 적절한 것을 선택하세요\n"
            "4. 기본 카테고리로 분류하기 어려운 경우, 새로운 카테고리를 제안하세요\n"
            "5. 하나의 게시물이 여러 카테고리에 해당할 수 있습니다 (최소 1개 ~ 최대 3개)\n"
            "6. 새로운 카테고리를 제안할 때는 기존 카테고리와 중복되지 않고 명확한 주제를 가진 카테고리를 제안하세요"
        )
        return system_prompt

    def get_user_prompt(self) -> str:
        """사용자 프롬프트를 생성합니다."""
        user_prompt = (
            f"다음 Instagram 게시물의 내용을 분석하여 가장 적절한 카테고리를 분류해주세요.\n\n"
            f"게시물 설명: {self.caption}\n"
            f"해시태그: {', '.join(self.hashtags)}\n\n"
            f"기본 카테고리 목록:\n"
            f"{', '.join(self.base_categories)}\n\n"
            f"위 내용을 바탕으로 다음 형식에 맞춰 응답해주세요:\n"
            f"1. names: 게시물에 할당할 카테고리 이름 목록 (최대 3개)\n"
            f"2. reason: 카테고리 분류 이유"
        )
        return user_prompt


class FilteringPrompt(AgentPrompt):
    """필터링 에이전트를 위한 프롬프트"""
    class OutputFormat(BaseModel):
        """
        필터링 에이전트의 출력을 파싱하는 클래스
        """
        bookmark_indexes: List[int] = Field(
            description="북마크 목록에서 사용자 쿼리와 관련 있는 북마크의 index 번호만 선택해서 list를 생성하세요. 예: [0, 1, 3, 5]"
        )
    
    def __init__(
        self, query, bookmarks
    ) -> None:
        self.query = query
        self.bookmarks = bookmarks

    def get_system_prompt(self) -> str:
        system_prompt = (
            "당신은 검색 결과 필터링을 담당하는 전문가입니다. 주어진 검색어와 각 북마크의 관련성을 평가하여\n"
            "검색어와 명확하게 관련 없는 북마크들을 제거해야 합니다.\n"
            "각 북마크에 대해 다음을 고려하세요:\n"
            "1. 북마크의 제목, 설명, URL이 검색어와 의미적으로 관련이 있는지\n"
            "2. 북마크의 태그가 검색어의 주제나 개념과 일치하는지\n"
            "3. 북마크가 검색어에 대한 유용한 정보를 제공하는지\n"
            "검색어와 관련이 있는 북마크의 인덱스 번호만 선택하세요.\n"
            "관련성이 낮더라도 검색어와 일부 연관성이 있다면 포함해주세요."
        )
        return system_prompt

    def get_user_prompt(self) -> str:
        """
        사용자 프롬프트를 생성합니다.
        
        Args:
            query: 검색어
            bookmarks: 북마크 목록
        
        Returns:
            str: 사용자 프롬프트
        """
        query = self.query
        bookmarks = self.bookmarks

        bookmarks_text = []
        for i, bookmark in enumerate(bookmarks):
            bookmark_info = [
                f"[index: {i}] feed caption: {bookmark.get('caption', '')}",
                # f"    URL: {bookmark.get('url', '')}",
                f"hashtags: {', '.join(bookmark.get('hashtags', []))}"
            ]
            bookmarks_text.append("\n".join(bookmark_info))
        
        formatted_bookmarks = "\n\n".join(bookmarks_text)
        
        user_prompt = (
            f"검색어: {query}\n\n"
            f"다음 북마크 목록에서 위 검색어와 관련이 있는 북마크의 인덱스 번호만 선택하세요:\n\n"
            f"{formatted_bookmarks}\n\n"
            f"선택한 인덱스 번호들을 쉼표로 구분하여 주어진 형식에 따라 다음과 같이 제공해주세요\n"
            f"예시: [0,1,3,5]"
        )
        
        return user_prompt