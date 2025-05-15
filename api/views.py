from decimal import Decimal

from django.utils import timezone
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Category, Product, Cart, CartItem, Price, Discount, Order, Voucher, AppliedVoucher, Stock, User, \
    SizeProduct, ColorProduct
from .paginator import CategoryPagination, ProductPagination
from .serializers import CategorySerializer, ProductSerializer, CartCreateSerializer, CartItemBulkCreateSerializer
from api.tasks import send_order_confirmation_email

class CategoryListView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = CategoryPagination

    @method_decorator(cache_page(60 * 15))  # Cache response for 15 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        """ Disable pagination when accessing `/category/all/` """
        if request.path == "/category/all/":
            self.pagination_class = None
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)

class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter  # ✅ use the custom filter

    @method_decorator(cache_page(60 * 15))  # Cache response for 15 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        """ Disable pagination when accessing `/product/all/` """
        if request.path == "/product/all/":
            self.pagination_class = None
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)

class ProductByCategoryView(ListAPIView):
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        """Retrieve products based on category_id or category_name."""
        category_id = self.kwargs.get('category_id')
        category_name = self.request.query_params.get('category_name', None)

        if category_id:
            return Product.objects.filter(category_id=category_id)

        if category_name:
            category = get_object_or_404(Category, category=category_name)
            return Product.objects.filter(category=category)

        return Product.objects.none()


class OrderCreateAPIView(APIView):
    def post(self, request):
        try:
            with transaction.atomic():
                user_id = request.data.get("user_id")
                cart_id = request.data.get("cart_id")
                payment_method = request.data.get("payment_method")
                shipping_type = request.data.get("shipping_type")
                is_company_order = request.data.get("is_company_order", False)
                additional_note = request.data.get("additional_note")
                voucher_ids = request.data.get("voucher_ids", [])

                user = User.objects.filter(id=user_id).first()
                cart = Cart.objects.get(id=cart_id, user=user)
                cart_items = CartItem.objects.filter(cart=cart)

                if not cart_items:
                    return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

                total_price = Decimal(0)
                discounted_product = Decimal(0)

                for item in cart_items:
                    price_obj = Price.objects.filter(size=item.size, color=item.color).order_by("-created_at").first()
                    if not price_obj:
                        raise ValueError("Price not found for selected size and color.")

                    price = price_obj.price * item.quantity

                    discount = Discount.objects.filter(
                        product=item.size.product,
                        start_at__lte=timezone.now(),
                        end_at__gte=timezone.now()
                    ).first()

                    if discount:
                        product_discount = price * (discount.discount_percent / Decimal(100))
                        discounted_product += product_discount
                        price -= product_discount

                    total_price += price

                    stock = Stock.objects.filter(color=item.color, size=item.size).first()
                    if not stock or stock.quantity < item.quantity:
                        raise ValueError("Insufficient stock for one or more items.")

                # Temporary shipping cost logic
                shipping_fee = Decimal(5000)
                discounted_shipping = Decimal(0)

                total_voucher_discount = Decimal(0)
                voucher = None
                for voucher_id in voucher_ids:
                    try:
                        voucher = Voucher.objects.filter(
                            id=voucher_id,
                            start_at__lte=timezone.now(),
                            end_at__gte=timezone.now()
                        ).first()
                    except Exception as e:
                        raise Exception(e).with_traceback()
                    if voucher:
                        # Prevent reuse of previously applied voucher
                        already_applied = AppliedVoucher.objects.filter(user=user, voucher=voucher).exists()
                        if already_applied:
                            return Response(
                                {"error": f"Voucher ID {voucher_id} has already been used by this user."},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    if voucher:
                        if voucher.discount_flat:
                            discount_amount = min(Decimal(voucher.discount_flat),
                                                  Decimal(voucher.max_discount or voucher.discount_flat))
                            total_voucher_discount += discount_amount
                        elif voucher.discount_percent:
                            discount_amount = Decimal(total_price) * (Decimal(voucher.discount_percent) / Decimal(100))
                            discount_amount = min(discount_amount, Decimal(voucher.max_discount))
                            total_voucher_discount += discount_amount
                        else:
                            continue
                discounted_product += total_voucher_discount

                final_price = total_price + shipping_fee - discounted_product - discounted_shipping - total_voucher_discount

                order = Order.objects.create(
                    cart=cart,
                    payment_method=payment_method,
                    shipping_type=shipping_type,
                    is_company_order=is_company_order,
                    additional_note=additional_note,
                    total_price=total_price,
                    shipping_fee=shipping_fee,
                    discounted_product=discounted_product,
                    discounted_shipping=discounted_shipping,
                    final_price=final_price
                )
                print(f"Order successfully created: {order.id}")

                # Send confirmation email asynchronously
                send_order_confirmation_email.delay(user.email, order.id)

                for voucher_id in voucher_ids:
                    try:
                        voucher = Voucher.objects.filter(id=voucher_id).first()
                        if voucher:
                            AppliedVoucher.objects.create(order=order, user=user, voucher=voucher)
                    except Exception as e:
                        print(f"Error while processing voucher {voucher_id}: {e}")
                print(f"AppliedVoucher successfully created: {order.id}")
                for item in cart_items:
                    stock = Stock.objects.get(color=item.color, size=item.size)
                    stock.quantity -= item.quantity
                    stock.save()
                print(f"Stock successfully modified: {order.id}")

                return Response({"message": "Order created successfully.", "order_id": order.id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CartCreateAPIView(APIView):
    def post(self, request):
        serializer = CartCreateSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            cart = Cart.objects.create(user=user)
            return Response({"message": "Cart created successfully.", "cart_id": cart.id},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartItemBulkCreateAPIView(APIView):
    def post(self, request):
        serializer = CartItemBulkCreateSerializer(data=request.data)
        if serializer.is_valid():
            cart_id = serializer.validated_data['cart_id']
            items = serializer.validated_data['items']
            try:
                cart = Cart.objects.get(pk=cart_id)
            except Cart.DoesNotExist:
                return Response({"error": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

            created_items = []
            for item in items:
                try:
                    size = SizeProduct.objects.get(pk=item['size_id'])
                    color = ColorProduct.objects.get(pk=item['color_id'])
                except (SizeProduct.DoesNotExist, ColorProduct.DoesNotExist):
                    return Response({"error": "Invalid size or color ID."}, status=status.HTTP_400_BAD_REQUEST)

                # Check that both size and color belong to the same product
                if size.product_id != color.product_id:
                    return Response({
                        "error": "Size and color must refer to the same product."
                    }, status=status.HTTP_400_BAD_REQUEST)

                cart_item = CartItem.objects.create(
                    cart=cart,
                    size=size,
                    color=color,
                    quantity=item['quantity']
                )
                created_items.append(cart_item.id)

            return Response({"message": "Items added successfully.", "cart_item_ids": created_items},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
