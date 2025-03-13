from .agents import FilteringAgent

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
        filter = FilteringAgent()
        bookmarks = filter.run(search_query, bookmarks)
        return bookmarks