import django_filters
from django.db.models import OuterRef, Subquery, Q, Min, DateTimeField
from django_filters.rest_framework import OrderingFilter
from .models import Product, Price


class ProductFilter(django_filters.FilterSet):
    model = django_filters.CharFilter(lookup_expr='icontains')
    like_count__gt = django_filters.NumberFilter(field_name='like_count', lookup_expr='gt')
    like_count__lt = django_filters.NumberFilter(field_name='like_count', lookup_expr='lt')
    brand = django_filters.CharFilter(field_name='brand__brand', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category__category', lookup_expr='icontains')

    price_min = django_filters.NumberFilter(method='filter_price_min')
    price_max = django_filters.NumberFilter(method='filter_price_max')
    created_at_min = django_filters.DateTimeFilter(method='filter_created_at_min')
    created_at_max = django_filters.DateTimeFilter(method='filter_created_at_max')

    ordering = OrderingFilter(
        fields=[
            ('like_count', 'like_count'),
            ('price_created', 'created_at'),
            ('min_price', 'price'),
        ]
    )

    class Meta:
        model = Product
        fields = [
            'model', 'like_count__gt', 'like_count__lt',
            'brand', 'category',
            'price_min', 'price_max',
            'created_at_min', 'created_at_max',
        ]

    def _price_created_at_subquery(self):
        return Price.objects.filter(
            Q(size__product=OuterRef('pk')) & Q(color__product=OuterRef('pk')) # The queries ensure both size and color belongs to same product
        ).values('size__product').annotate(
            created=Min('created_at')
        ).values('created')[:1]

    def _price_min_subquery(self):
        return Price.objects.filter(
            Q(size__product=OuterRef('pk')) & Q(color__product=OuterRef('pk'))
        ).values('size__product').annotate(
            min_price=Min('price')
        ).values('min_price')[:1]

    def filter_created_at_min(self, queryset, name, value):
        subquery = self._price_created_at_subquery()
        return queryset.annotate(price_created=Subquery(subquery, output_field=DateTimeField())).filter(
            price_created__gte=value)

    def filter_created_at_max(self, queryset, name, value):
        subquery = self._price_created_at_subquery()
        return queryset.annotate(price_created=Subquery(subquery, output_field=DateTimeField())).filter(
            price_created__lte=value)

    def filter_price_min(self, queryset, name, value):
        subquery = self._price_min_subquery()
        return queryset.annotate(min_price=Subquery(subquery)).filter(min_price__gte=value)

    def filter_price_max(self, queryset, name, value):
        subquery = self._price_min_subquery()
        return queryset.annotate(min_price=Subquery(subquery)).filter(min_price__lte=value)
