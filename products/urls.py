from django.urls import path
from . import views


urlpatterns = [
    path('', views.products, name='products'),
    path('add/', views.add_product, name='add_product'),
    path('edit/<int:product_id>', views.edit_product, name='edit_product'),
    path('delete/<int:product_id>', views.delete_product,
         name='delete_product'),
    path('like/<int:pk>', views.like_view, name='like_id'),
    path('dislike/<int:pk>', views.remove_like, name='remove_like'),
]
