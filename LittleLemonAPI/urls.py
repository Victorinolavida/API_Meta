from django.urls import path,include
from .views import Users,MenuItems,MenuItemView,groupsViews,groupView,cart,OrdersView,orderById
# from .views import oderders,orderById

urlpatterns = [
    path('users', Users.as_view()),
    path('users/',include('djoser.urls')),
    path('menu-items/',MenuItems),
    path('menu-items/<int:pk>/',MenuItemView),
    path('groups/<group>/users',groupsViews),
    path('groups/<group>/users/<userId>/',groupView),
    path('cart/menu-items',cart),
    path('orders/',OrdersView),
    path("orders/<int:orderId>/",orderById)
]