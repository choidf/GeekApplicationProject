from django.urls import path, re_path
from . import views
urlpatterns = [
    path('category/', views.CategoryListView.as_view(), name='category'),
    path('category/all/', views.CategoryListView.as_view(), name='category-without-pagination'),
    path('product/', views.ProductListView.as_view(), name='product'),
    path('product/all/', views.ProductListView.as_view(), name='product-without-pagination'),
    path('product/category/<int:category_id>/', views.ProductByCategoryView.as_view(), name='product-category'),
    path('product/category/', views.ProductByCategoryView.as_view(), name='product-category-name'),
    path('order/create/', views.OrderCreateAPIView.as_view(), name='order-create'),
    path('cart/create/', views.CartCreateAPIView.as_view(), name='cart-create'),
    path('cart/items/add/', views.CartItemBulkCreateAPIView.as_view(), name='cart-item-create'),

]
