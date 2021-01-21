from rest_framework.viewsets import ReadOnlyModelViewSet
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import MultiMatch, Q

from main.serializers.search import SearchSerializer
from main.api.general import PageSizeMixin


class SearchView(PageSizeMixin, ReadOnlyModelViewSet):
    page_size = 10
    serializer_class = SearchSerializer

    def get_queryset(self):
        search_text = self.request.GET.get('search', '')
        query = (Q('term', site=self.request.site.id) | Q('term', is_global=True))\
            & MultiMatch(query=search_text, fields=['title', 'text'])
        if self.request.GET.get('section') and self.request.GET.get('section') != 'all':
            query &= Q('term', model_class=self.request.GET.get('section'))
        return Search(index='search').query(query).highlight('title', 'text')
