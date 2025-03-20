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
        # """카테고리 분류 에이전트의 출력을 파싱하는 클래스"""
        # categories: List[str] = Field(
            # description="게시물에 할당할 카테고리 이름 목록"
        categories: str = Field(
            description="게시물에 할당할 카테고리 이름"
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
        # system_prompt = (
        #     "당신은 Instagram 게시물을 특정 카테고리로 분류하는 전문가입니다.\n"
        #     "게시물의 내용과 해시태그를 분석하여 가장 적절한 카테고리를 할당해야 합니다.\n"

        #     "다음 사항을 고려하세요:\n"
        #     "1. 게시물 내용과 hashtag를 보고 이 feed의 주요 주제와 내용을 파악하세요\n"
        #     "2. 주어진 카테고리 중 가장 적절한 것을 선택하세요. 하나의 게시물에 가장 관련 있다고 판단되는 하나의 카테고리만 해당할 수 있습니다\n"
        #     "3. 기존 카테고리로는 도저히 분류하기 어려운 경우, 새로운 카테고리를 제안하세요\n"
        #     "4. 새로운 카테고리를 제안할 때는 기존 카테고리와 중복되지 않는 주제의 카테고리를 제안하세요"
        #     "5. 카테고리 이름은 명사 단어 하나로 지어주세요"
        # #     "6. 게시물 내용이 많지 않아 주제 파악이 어려운 경우 기타 카테고리로 분류해주세요"
        # )
        system_prompt = (
            """
            Classify Instagram posts into specific categories based on their caption and hashtags.

            Consider the following:

            1. Analyze the post's caption and hashtags to determine the main topic and theme of the feed.
            2. Choose the most appropriate category from the given options. Only one category should be assigned to a single post that is most relevant.
            3. If it is challenging to categorize under existing categories, propose a new category.
            4. When suggesting a new category, ensure it is a distinct topic that does not overlap with existing categories.
            5. Category names should consist of a single noun.
            
            # Steps

            1. Review the post's caption and hashtags.
            2. Determine the main theme and choose the most fitting category.
            3. Consider proposing a new category if necessary.

            # Output Format

            - The name of the selected category (or proposed new category) in korean.
            - Ensure categories are concise and clear.

            # Notes

            - Aim for precision in category selection.
            - Avoid redundant or overlapping categories.
            """
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
            f"1. categories: 게시물에 할당할 카테고리 이름\n"
            f"2. category_reason: 카테고리 분류 이유"
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
        filter_reasons: List[str] = Field(
            description="모든 북마크에 대해 각 북마크 별로 채택했는지 안했는지와 그 이유를 list로 서술하세요. 예: ['0 / X / 검색 쿼리와 관련없는 개구리와 관련된 게시물입니다.', '1 / O / 검색 쿼리와 관련있는 여행에 대한 게시물입니다.']"
        )
    
    def __init__(
        self, query, bookmarks
    ) -> None:
        self.query = query
        self.bookmarks = bookmarks

    def get_system_prompt(self) -> str:
        # system_prompt = (
        #     "당신은 검색 결과 필터링을 담당하는 전문가입니다. 주어진 검색어와 각 북마크의 관련성을 평가하여\n"
        #     "검색어와 명확하게 관련 없는 북마크들을 제거해야 합니다.\n"
        #     "각 북마크에 대해 다음을 고려하세요:\n"
        #     "1. 북마크의 제목, 설명, URL이 검색어와 의미적으로 관련이 있는지\n"
        #     "2. 북마크의 해시태그가 검색어의 주제나 개념과 일치하는지\n"
        #     "3. 북마크가 검색어에 대한 유용한 정보를 제공하는지\n"
        #     "검색어와 관련이 있는 북마크의 인덱스 번호만 선택하세요."
        # )
        system_prompt = (
            """
            You are an expert responsible for filtering search results. Your task is to evaluate the relevance of each bookmark with the given search query and remove bookmarks that are not clearly related to the search query.

            # Considerations

            - Evaluate if the caption, url of the bookmark are semantically related to the search query.
            - Check if the hashtags of the bookmark match the topics or concepts of the search query.

            # Steps

            1. Analyze the caption and URL of each bookmark to evaluate their semantic relevance to the search query.
            2. Analyze the hashtags of each bookmark to determine if they match the topics or concepts of the search query.

            # Output Format

            - List only the index numbers of bookmarks that are related to the search query.
            - Return the list of index numbers as a comma-separated list.

            # Examples

            Input: 
            Search Query: "Artificial Intelligence Technology"
            Bookmark List:
            0. Caption: "Advancements in AI technology", URL: "https://aiexample.com", Hashtags: "#AI #Technology"
            1. Caption: "New trends in music", URL: "https://musicexample.com", Hashtags: "#Music"

            Output:
            [0]

            # Notes

            - Only select indices with clear relevance.
            - Exclude information indirectly related to the search query.
            """
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


class RecommendPrompt(AgentPrompt):
    """
    추천 에이전트를 위한 프롬프트
    """
    class OutputFormat(BaseModel):
        """
        추천 에이전트의 출력을 파싱하는 클래스
        """
        feed_indexes: List[int] = Field(
            description="최신 게시물 목록에서 사용자 쿼리와 관련 있는 게시물을 최대 5개까지 뽑아 게시물의 index 번호만 선택해서 list를 생성하세요. 예: [0, 1, 3, 5]"
        )
        recommend_reasons: List[str] = Field(
            description="채택한 게시물의 인덱스와 추천 이유를 list로 서술하세요. 예: ['0 / 사용자의 여행 관련 과거 히스토리와 일치하며 검색어 여행과 직접적으로 관련된 삿포로와 관련된 내용입니다', ...]"
        )
    
    def __init__(
        self, query, user_history, feeds
    ) -> None:
        self.query = query
        self.user_history = user_history
        self.feeds = feeds

    def get_system_prompt(self) -> str:
        system_prompt = (
            """
            당신은 사용자 맞춤형 콘텐츠 추천 전문가입니다. 제공된 컨텍스트(사용자 히스토리와 최신 게시물)를 활용하여 현재 검색 쿼리에 가장 관련성 높은 게시물을 최대 5개까지 추천해주세요.

            # 컨텍스트 활용 방법
            1. 사용자 히스토리: 사용자의 취향을 파악하세요
            2. 쿼리 관련 최신 게시물: 사용자에게 추천할 최대 5개의 게시물을 이 게시물들 중 선발합니다
            3. 두 정보를 종합하여 사용자에게 가장 적합한 게시물을 최대 5개까지 식별하세요

            # 추천 프로세스
            1. 제공된 사용자 히스토리에서 사용자의 취향 파악
            2. 검색 쿼리와 게시물 내용 간의 의미적 연관성 평가
            3. 사용자 과거 행동과 현재 관심사를 종합적으로 고려한 최적의 추천 제공
            4. 각 게시물별 추천 이유 상세 설명 (사용자 히스토리 연관성 포함)

            # 출력 형식
            - feed_indexes: 쿼리 관련 최신 게시물들 중 추천하는 게시물의 인덱스 번호 목록 (예시: [0, 1, 3, 5]) 리스트 최대 길이 5
            - recommend_reasons: 추천 게시물 인덱스와 추천 이유 설명
            예: ['0 / 사용자의 여행 관련 과거 히스토리와 일치하며 검색어 여행과 직접적으로 관련된 삿포로와 관련된 내용입니다', 
                ...]
            """
        )
        # system_prompt = (
        #     """

        #     """
        # )
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
        user_history = self.user_history
        feeds = self.feeds

        # 사용자 히스토리 포맷팅 # TODO
        history_text = "### 검색 히스토리:\n"
        if user_history and len(user_history) > 0:
            for i, h in enumerate(user_history):
                history_text += f"{i}: {h.get('caption', '')}, {h.get('hashtags', '')}\n"
                # if 'timestamp' in h:
                #     history_text += f"  (시간: {h.get('timestamp', '')})\n"
        else:
            history_text += "- 이용 가능한 사용자 히스토리가 없습니다.\n"
        
        # 게시물 목록 포맷팅
        feed_infos = []
        for i, f in enumerate(feeds):
            feed_infos.append(
                f"""
                {i}: \n
                caption: {f.get('caption', '')}\n
                hashtags: {f.get('hashtags')}
                """
            )
        
        formatted_feeds = "\n\n".join(feed_infos)
        
        user_prompt = (
            f"### 검색어: {query}\n\n"
            f"{history_text}\n\n"
            f"### 추천 후보 게시물 목록:\n\n"
            f"{formatted_feeds}\n\n"
            f"위 정보를 기반으로 추천 후보 게시물 중 사용자에게 가장 관련성 높은 게시물 최대 5개를 추천해주세요. 다음 형식으로 응답해주세요:\n"
            f"1. feed_indexes: [추천할 게시물 인덱스 번호들] (길이 5 이하의 list)\n"
            f"2. recommend_reasons: [추천한 게시물 인덱스와 추천 이유]"
        )
        
        return user_prompt