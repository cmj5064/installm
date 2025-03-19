from .agents import FilterAgent

class Search:
    """agent를 활용한 검색 수행"""
    def __init__(self, db, vector_store):
        self.db = db
        self.vector_store = vector_store

    def keyword_search(self, search_query):
        bookmarks = self.db.search_bookmarks(search_query)
        return bookmarks

    def semantic_search(self, search_query):
        bookmarks = self.vector_store.search_bookmarks(search_query)
        return bookmarks
    
    def multi_search(self, search_query):
        bookmarks = self.vector_store.search_bookmarks(search_query)
        filter = FilterAgent()
        # bookmarks = filter.run(search_query, bookmarks)
        # return bookmarks
        state = filter.run(search_query, bookmarks)
        print(state["filter_reasons"])
        return state["filtered_bookmarks"]
    
    def total_search(self, search_query):
        db_bookmarks = self.keyword_search(search_query)
        ss_bookmarks = self.semantic_search(search_query)

        # 중복 제거(feed_id나 url 같은 고유 필드가 있음)
        bookmarks = db_bookmarks + [b for b in ss_bookmarks if b not in db_bookmarks]
        filter = FilterAgent()
        # bookmarks = filter.run(search_query, bookmarks)
        # return bookmarks
        state = filter.run(search_query, bookmarks)
        print(state["filter_reasons"])
        return state["filtered_bookmarks"]