"""
Сериализаторы модели новостей
"""
from rest_framework import serializers

from main.models import News
from .image_transform import ImageTransformSerializer
from .site import BaseSiteSerializer
from .fields import NulledDatetimeField, NulledDateField


class BaseNewsSerializer(serializers.ModelSerializer):
    """ Базовый сериализатор новостей """
    date_publish = NulledDatetimeField(format='%Y-%m-%d', required=False, allow_null=True, 
                error_messages={
                    'invalid': 'Дата публикации: Неправильный формат времени'
                })

    date_top = NulledDateField(format='%Y-%m-%d', required=False, allow_null=True, 
                error_messages={
                    'invalid': 'Дата нахождения в топе: Неправильный формат даты'
                })

    class Meta:
        model = News
        fields = (
            'id',
            'title',
            'preview',
            'show_preview_on_detail',
            'body',
            'section',
            'date_created',
            'date_modified',
            'date_publish',
            'url',
            'image',
            'is_chronicles',
            'is_mailing',
            'is_top',
            'date_top',
            'is_top_expired',
            'is_deleted',
        )
        read_only_fields = (
            'date_created',
            'date_modified',
            'is_deleted',
        )
        

class NewsSerializer(BaseNewsSerializer):
    """ Публичный сериализатор новостей """
    image_detail = serializers.SerializerMethodField()

    class Meta(BaseNewsSerializer.Meta):
        fields = (
            'id',
            'title',
            'preview',
            'show_preview_on_detail',
            'body',
            'section',
            'date_created',
            'date_modified',
            'date_publish',
            'url',
            'image',
            'image_detail',
            'is_chronicles',
            'is_mailing',
            'is_top',
            'date_top',
            'is_top_expired',
            'is_deleted',
        )
        read_only_fields = (
            'date_created',
            'date_modified',
            'is_deleted',
        )

    def get_image_detail(self, obj):
        return ImageTransformSerializer(obj.image, context=self.context).data if obj.image_id else None


class NewsKindergartenSerializer(NewsSerializer):
    """ Публичный сериализатор для новости на детских садах """
    pass
    

class NewsPortalSerializer(NewsSerializer):
    """ Публичный сериализатор для новости на детских садах """
    image_preview = serializers.SerializerMethodField()
    image_preview_full = serializers.SerializerMethodField()

    class Meta(NewsSerializer.Meta):
        fields = (
            'id',
            'title',
            'preview',
            'show_preview_on_detail',
            'body',
            'section',
            'date_created',
            'date_modified',
            'date_publish',
            'url',
            'image',
            'image_detail',
            'image_preview',
            'image_preview_full',
            'is_chronicles',
            'is_mailing',
            'is_top',
            'date_top',
            'is_top_expired',
            'is_deleted',
        )
        read_only_fields = (
            'date_created',
            'date_modified',
            'is_deleted',
        )

    def get_image_preview(self, obj):
        try:
            return obj.image.image.image_source['news_preview_portal'].url
        except:
            return None

    def get_image_preview_full(self, obj):
        try:
            return obj.image.image.image_source['news_preview_full_portal'].url
        except:
            return None


class NewsStaffSerializer(BaseNewsSerializer):
    """ Сериализатор новостей для администраторов """
    site_detail = serializers.SerializerMethodField()

    class Meta(BaseNewsSerializer.Meta):
        fields = (
            'id',
            'title',
            'preview',
            'body',
            'section',
            'site',
            'site_detail',
            'date_created',
            'date_modified',
            'date_publish',
            'url',
            'image',
            'is_chronicles',
            'is_mailing',
            'is_top',
            'date_top',
            'is_top_expired',
            'is_deleted',
        )

    def get_site_detail(self, obj: News) -> dict:
        return BaseSiteSerializer(obj.site).data if obj.site else None


class NewsListStaffSerializer(BaseNewsSerializer):
    """ Сериализатор новостей для администраторов """
    site_detail = BaseSiteSerializer(source='site', read_only=True)

    class Meta(BaseNewsSerializer.Meta):
        fields = (
            'id',
            'title',
            'site',
            'site_detail',
            'date_created',
            'date_modified',
            'date_publish',
            'is_deleted',
        )