from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType


class SearchSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    text = serializers.CharField()
    url = serializers.CharField()
    score = serializers.SerializerMethodField()
    highlight = serializers.SerializerMethodField()
    model_class = serializers.CharField()
    node = serializers.SerializerMethodField()

    class Meta:
        fields = (
            'id',
            'title',
            'text',
            'url',
            'model_class',
            'node',
        )
        read_only_fields = fields

    def get_score(self, obj):
        return obj.meta['score']

    def get_highlight(self, obj):
        result = dict()
        try:
            result['title'] = obj.meta['highlight']['title'][0]
        except:
            pass
        try:
            result['text'] = obj.meta['highlight']['text'][0]
        except:
            pass
        return result

    def get_node(self, obj):
        try:
            node_type = ContentType.objects.get(app_label='main', model=obj.model_class)
            node = node_type.get_object_for_this_type(id=obj.id)
            serializer = node.get_search_serializer()
            if serializer:
                return serializer(node).data
            else:
                return None
        except:
            return None