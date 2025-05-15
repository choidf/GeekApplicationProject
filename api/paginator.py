from rest_framework.pagination import PageNumberPagination


class CategoryPagination(PageNumberPagination):
    page_size = 5  # Set the default page size
    page_query_param = 'page'

class ProductPagination(PageNumberPagination):
    page_size = 10  # Set the default page size
    page_query_param = 'page'