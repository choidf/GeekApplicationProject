from rest_framework import serializers
from .models import Category, Product, SizeProduct, ColorProduct


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'  # You can specify relevant fields instead

class CartCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class CartItemSerializer(serializers.Serializer):
    size_id = serializers.IntegerField()
    color_id = serializers.IntegerField()
    quantity = serializers.IntegerField()

    def validate(self, data):
        size_id = data.get('size_id')
        color_id = data.get('color_id')

        try:
            size = SizeProduct.objects.get(pk=size_id)
        except SizeProduct.DoesNotExist:
            raise serializers.ValidationError({'size_id': 'Invalid size_id'})

        try:
            color = ColorProduct.objects.get(pk=color_id)
        except ColorProduct.DoesNotExist:
            raise serializers.ValidationError({'color_id': 'Invalid color_id'})

        if size.product_id != color.product_id:
            raise serializers.ValidationError('Size and Color do not belong to the same product.')

        return data


class CartItemBulkCreateSerializer(serializers.Serializer):
    cart_id = serializers.IntegerField()
    items = CartItemSerializer(many=True)


class CartItemBulkCreateSerializer(serializers.Serializer):
    cart_id = serializers.IntegerField()
    items = CartItemSerializer(many=True)
