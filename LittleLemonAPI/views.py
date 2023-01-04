from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from rest_framework.decorators import api_view, throttle_classes
from django.contrib.auth.models import User,Group
import datetime 
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.throttling import  AnonRateThrottle,UserRateThrottle
from rest_framework.decorators import permission_classes
from decimal import Decimal
from .serializers import UserSerilizer,MenuItemsSerlizer,CartSerializer,OrderSerializer,OrderItemSerializer
from .serializers import MenuItemsSerlizerView,OrderSerializerView
from .models import MenuItem,Cart,Order,Category

from rest_framework.decorators import api_view
from .pagination import StandardResultsSetPagination


#@permission_classes([AnonymousUser])
class Users(APIView):
    permission_classes = () 
    def post(self,request):
        data_serialized = UserSerilizer(data=request.data)
        data_serialized.is_valid(raise_exception = True)
        pas = request.data['password']
        data_serialized.create(pas)

        return Response(data_serialized.data,status= status.HTTP_201_CREATED)

@api_view(['GET','POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle,UserRateThrottle])
def MenuItems(request):
    if request.method == 'GET':
        items = MenuItem.objects.all()

        #filter
        category_filter = request.query_params.get("category")
        price_filter = request.query_params.get("price")
        featured_filer = request.query_params.get("featured")
        #search
        search = request.query_params.get("search")
        #order
        ordering = request.query_params.get("order")
        
        if search:
            items = items.filter(title__startswith=search)
        if price_filter:
            items = items.filter(price__lte = Decimal(price_filter))
        if category_filter:
            id_cat = Category.objects.filter(title=category_filter).first()
            if id_cat:
                items = items.filter(category=id_cat.id)
        if featured_filer and featured_filer.lower() in ['false','true']: 
            if featured_filer.lower() == 'false':
                featured_filer = False
            elif featured_filer.lower() == 'true':
                featured_filer = True
            items = items.filter(featured=featured_filer)
        if ordering:
            ordering_fiels = ordering.split(",")
            items = items.order_by(*ordering_fiels)
        
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(items, request)

        serialized_items = MenuItemsSerlizerView(result_page,many=True)
       
        return paginator.get_paginated_response(serialized_items.data)

    else:
        is_manager = request.user.groups.filter(name="manager").exists()
        if not is_manager:
            return Response({'message':"You are not authorized"},
                            status=status.HTTP_403_FORBIDDEN)

        data_serialized = MenuItemsSerlizer(data = request.data)
        data_serialized.is_valid(raise_exception = True)  
        data_serialized.save()      
        return Response(data_serialized.data,status= status.HTTP_201_CREATED)

@api_view(['GET','PUT','PATCH','DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def MenuItemView(request,pk):
    if request.method == 'GET':
        item=MenuItem.objects.filter(pk=pk).first()
        if not item:  
            return Response({'message':"item not found"},status= status.HTTP_404_NOT_FOUND)
        
        serialized_item = MenuItemsSerlizerView(item)
        return Response(serialized_item.data,status= status.HTTP_200_OK)

    else:
        is_manager = request.user.groups.filter(name="manager").exists()
        if not is_manager:
            return Response({'message':"You are not authorized"},status=status.HTTP_403_FORBIDDEN)
        

        item=MenuItem.objects.filter(pk=pk).first()
        if not item:
            return Response({'message':"item not found"},status= status.HTTP_404_NOT_FOUND)
        
        if request.method == 'PUT' or request.method == 'PATCH':
            data=MenuItemsSerlizer(item,data=request.data)
            data.is_valid(raise_exception = True)
            data.save()
            return Response(data.data,status= status.HTTP_206_PARTIAL_CONTENT)
            
        if request.method == 'DELETE':
            item.delete()
            return Response({'message':"item deleted"},status= status.HTTP_200_OK)

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def groupsViews(request,group):
    is_manager = request.user.groups.filter(name="manager").exists()
    if not is_manager:
            return Response({'message':"You are not authorized"},
                            status=status.HTTP_403_FORBIDDEN)

    #finding group
    group = Group.objects.filter(name=group).first()
    if not group:
        return Response({'message':"group does not exist"},
                        status= status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        users = User.objects.filter(groups__name=group)
        users = UserSerilizer(users,many=True)
        return Response(users.data,status= status.HTTP_200_OK)

    if request.method =='POST':
        username = request.data.get('username')
        user = User.objects.filter(username=username).first()
        
        if not username or not user:
            return Response({'message':"the field username is required"},
                            status= status.HTTP_400_BAD_REQUEST)

        group.user_set.add(user.id)
        
        return Response({'message':f'user {username} group updated'},status= status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def groupView(request,group,userId):
    is_manager = request.user.groups.filter(name="manager").exists()
    if not is_manager:
            return Response({'message':"You are not authorized"},
                            status=status.HTTP_403_FORBIDDEN)
    #finding group
    group = Group.objects.filter(name=group).first()
    if not group:
        return Response({'message':"group does not exist"},
                        status= status.HTTP_404_NOT_FOUND)
    
    user = User.objects.filter(groups__name=group,pk=userId).first()
    if not user:
        return Response({'message':"item not found"},
                        status= status.HTTP_404_NOT_FOUND)
    user.delete()
    return Response({'message':f"user: {user.username} was deleted"})

@api_view(['GET','POST','DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def cart(request):
    user = request.user
    if request.method == 'GET':
        cart = Cart.objects.filter(user=user)
        car_user = CartSerializer(data=cart,many=True)
        car_user.is_valid()
        return Response(car_user.data)


    if request.method == 'POST':
        menuitem_id = request.data.get('menuitem')
        quantity = request.data.get('quantity')
        queryset = MenuItem.objects.filter(id=menuitem_id).first()
        

        if not queryset:
            return Response({'message':"menuitem does not exist"},
                        status= status.HTTP_400_BAD_REQUEST)

        data={
            "user":user.id,
            "menuitem":queryset.id,
            "unit_price":queryset.price,
            "quantity" : quantity,
            "price":quantity*queryset.price
        }
        
        cart_new = CartSerializer(data=data)
        cart_new.is_valid(raise_exception = True)
        cart_new.save()
        return Response(cart_new.data)


    if request.method == 'DELETE':
        carts = Cart.objects.filter(user=user)
        if not carts:
            return Response({'message':"items not found"},
                        status= status.HTTP_404_NOT_FOUND)
        carts.delete()
        return Response({"message":"all items deleted"})

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def OrdersView(request):
    user = request.user
    is_manager = request.user.groups.filter(name="manager").exists()
    is_delivery = request.user.groups.filter(name="delivery-crew").exists()
    
    if request.method == 'GET':
        orders = None

        total_filter = request.query_params.get("total")
        status_filter = request.query_params.get("status")
        delivery = request.query_params.get("delivery")
        #order
        ordering = request.query_params.get("order")
        
        if not is_manager and not is_delivery:
            orders = Order.objects.filter(user=user.id)
        
        else:
            user = request.query_params.get("user")

            if is_manager:
                orders = Order.objects.all()
                

            if is_delivery:
                orders = Order.objects.filter(delivery_crew=user.id)
            
            if user:
                    id = User.objects.filter(username = user).first()
                    orders = orders.filter(user=id)

        if total_filter:
            orders = orders.filter(total__lte = Decimal(total_filter))
        if status_filter and (status_filter.lower() in ['true','false']):
            if status_filter.lower() == 'true':
                status_filter = True
            else:
                status_filter = False
            orders = orders.filter(status=status_filter)
        if ordering:
            ordering_fiels = ordering.split(",")
            orders = orders.order_by(*ordering_fiels)
        
        if delivery:
            id = User.objects.filter(username=delivery).first()
            if id:
                if id.groups.filter(name="delivery-crew").exists():
                    orders = orders.filter(delivery_crew = id)

        if total_filter:
            orders = orders.filter(total__lte = Decimal(total_filter))
        if status_filter and (status_filter.lower() in ['true','false']):
            if status_filter.lower() == 'true':
                status_filter = True
            else:
                status_filter = False
            orders = orders.filter(status=status_filter)
        if ordering:
            ordering_fiels = ordering.split(",")
            orders = orders.order_by(*ordering_fiels)
        if user:
            id = User.objects.filter(username = user).first()
            orders = orders.filter(user=id)
        if delivery:
            id = User.objects.filter(username=delivery).first()
            if id:
                if id.groups.filter(name="delivery-crew").exists():
                    orders = orders.filter(delivery_crew = id)
        

        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(orders, request)

        serialized_items = OrderSerializerView(data=result_page,many=True)
        serialized_items.is_valid()
        return paginator.get_paginated_response(serialized_items.data)


    if request.method == 'POST':    
        cart = Cart.objects.filter(user=user.id)
        if not cart:
            return Response({'message':"cart must not be empty"},
                        status= status.HTTP_400_BAD_REQUEST)

        total = 0
        for item in cart:
            total += item.price
        order = {
            "user":user.id,
            "total":total,
            "date":datetime.datetime.today().strftime('%Y-%m-%d')
        }

        new_order = OrderSerializer(data=order)
        new_order.is_valid(raise_exception = True)
        order_saved = new_order.save()

        for item in cart:
            orderItemData = {
            "order":order_saved.id,
            "menuitem":item.menuitem.id,
            "quantity":item.quantity,
            "unit_price":item.unit_price,
            "price":item.price
            }
            orderItem = OrderItemSerializer(data = orderItemData)
            orderItem.is_valid(raise_exception = True)
            orderItem.save()

            item.delete()


        return Response(new_order.data)

    
@api_view(['GET','POST','DELETE',"PATCH"])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def orderById(request,orderId):
    user = request.user

    is_manager = request.user.groups.filter(name="manager").exists()
    is_delivery = request.user.groups.filter(name="delivery-crew").exists()

    if request.method == 'GET':
        if not is_delivery and not is_manager:
            order = Order.objects.filter(id=orderId,user=user.id)
            if not order:
                return Response({'message':"this order does not exist"},
                                status= status.HTTP_400_BAD_REQUEST)
        
            orderI = OrderSerializer(data = order,many=True)
            orderI.is_valid()
            print(orderI.data)
            return Response(orderI.data[0])
        if is_manager:
            order = Order.objects.filter(id=orderId)
            orders = OrderSerializer(data=order,many=True)

            if not order:
                return Response({'message':"this order does not exist"},
                                status= status.HTTP_400_BAD_REQUEST)
            orders.is_valid()
            return Response(orders.data[0])
        return Response({'message':"You are not authorized"},
                                status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'POST' or request.method=='PATCH':
        if is_manager:
            
            statusOrder = request.data.get("status")
            delivery_crew_id = request.data.get('delivery-crew')
            
            if not Group.objects.filter(user=delivery_crew_id,name="delivery-crew"):
                 return Response({'message':"invalid delivery-crew field"},
                            status= status.HTTP_400_BAD_REQUEST)
            if not statusOrder == 1  and not statusOrder == 0:
                return Response({'message':"invalid status field"},
                            status= status.HTTP_400_BAD_REQUEST)

            order = Order.objects.filter(id=orderId).first()
            if not order:
                    return Response({'message':"item not found"},
                    status= status.HTTP_404_NOT_FOUND)
            
            id_crew = User.objects.filter(id=delivery_crew_id).first()
         
            orderNew = OrderSerializer(order,{
                "user":order.user.id,
                "total":order.total,
                "date":order.date,
                "status":statusOrder,
                "delivery_crew":id_crew.id
            })

            orderNew.is_valid(raise_exception = True)
            orderNew.save()
            return Response(orderNew.data)

        elif request.method=='PATCH' and is_delivery:
            order = Order.objects.filter(id=orderId).first()
            
            if not order:
                return Response({'message':"this order does not exist"},
                                status= status.HTTP_400_BAD_REQUEST)

            if not order.delivery_crew.id == user.id:
                return Response({'message':"You are not authorized"},
                                status=status.HTTP_403_FORBIDDEN)
            
            statusOrder = request.data.get("status")
            if not statusOrder == 1  and not statusOrder == 0:
                return Response({'message':"invalid status field"},
                            status= status.HTTP_400_BAD_REQUEST)
            

            orderNew = OrderSerializer(order,{
                "user":order.user.id,
                "total":order.total,
                "date":order.date,
                "status":statusOrder,
            })
            orderNew.is_valid(raise_exception = True)
            orderNew.save()
            return Response(orderNew.data)
        else:
            return Response({'message':"You are not authorized"},
                                status=status.HTTP_403_FORBIDDEN)

    if request.method == 'DELETE':
        if is_manager:
            order = Order.objects.filter(id=orderId)
            if not order:
                return Response({'message':"item not found"},status= status.HTTP_404_NOT_FOUND)
            order.delete()
            return Response({"message":"order deleted"})
        else:
            return Response({'message':"You are not authorized"},
                            status=status.HTTP_403_FORBIDDEN) 