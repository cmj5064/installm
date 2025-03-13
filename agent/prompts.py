"""
에이전트 시스템에서 사용되는 프롬프트 정의 모듈
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo


class AgentPrompt(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def get_system_prompt(self):
        pass

    @abstractmethod
    def get_user_prompt(self):
        pass


class FilteringPrompt(AgentPrompt):
    """필터링 에이전트를 위한 프롬프트"""
    class OutputFormat(BaseModel):
        """
        필터링 에이전트의 출력을 파싱하는 클래스
        """
        bookmark_indexes: List[str] = Field(
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
                f"[{i}] 제목: {bookmark.get('title', '')}",
                f"    URL: {bookmark.get('url', '')}",
                f"    설명: {bookmark.get('description', '')}",
                f"    태그: {', '.join(bookmark.get('tags', []))}"
            ]
            bookmarks_text.append("\n".join(bookmark_info))
        
        formatted_bookmarks = "\n\n".join(bookmarks_text)
        
        user_prompt = (
            f"검색어: {query}\n\n"
            f"다음 북마크 목록에서 위 검색어와 관련이 있는 북마크의 인덱스 번호만 선택하세요:\n\n"
            f"{formatted_bookmarks}\n\n"
            f"선택한 인덱스 번호들을 쉼표로 구분하여 다음 형식으로 제공해주세요:\n"
            f"[0,1,3,5]"
        )
        
        return user_prompt