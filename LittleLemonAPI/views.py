from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from rest_framework.decorators import api_view
from django.contrib.auth.models import User,Group
import datetime 
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from .serializers import UserSerilizer,MenuItemsSerlizer,CartSerializer,OrderSerializer,OrderItemSerializer

from .models import MenuItem,Cart,Order

from rest_framework.decorators import api_view




#@permission_classes([AnonymousUser])
class Users(APIView):
    permission_classes = () 
    def post(self,request):
        data_serialized = UserSerilizer(data=request.data)
        data_serialized.is_valid(raise_exception = True)
        pas = request.data['password']
        data_serialized.create(pas)

        return Response(data_serialized.data,status= status.HTTP_201_CREATED)

@permission_classes([IsAuthenticated])
@api_view(['GET','POST'])
def MenuItems(request):
    if request.method == 'GET':
        items = MenuItem.objects.all()
        serialized_items = MenuItemsSerlizer(items,many=True)
        return Response(serialized_items.data,status=status.HTTP_200_OK)
    else:
        is_manager = request.user.groups.filter(name="manager").exists()
        if not is_manager:
            return Response({'message':"You are not authorized"},
                            status=status.HTTP_403_FORBIDDEN)

        data_serialized = MenuItemsSerlizer(data = request.data)
        data_serialized.is_valid(raise_exception = True)  
        data_serialized.save()      
        return Response(data_serialized.data,status= status.HTTP_201_CREATED)

@permission_classes([IsAuthenticated])
@api_view(['GET','PUT','PATCH','DELETE'])

def MenuItemView(request,pk):
    if request.method == 'GET':
        item = None
        try:
            item=MenuItem.objects.filter(pk=pk).first()
        except MenuItem.DoesNotExist:   
            return Response({'message':"item not found"},status= status.HTTP_404_NOT_FOUND)
        
        serialized_item = MenuItemsSerlizer(item)
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
            #data.update(data,request.data)
            data.save()
            return Response(data.data,status= status.HTTP_206_PARTIAL_CONTENT)
            
        if request.method == 'DELETE':
            item.delete()
            return Response({'message':"item deleted"},status= status.HTTP_200_OK)

@permission_classes([IsAuthenticated])
@api_view(['GET','POST'])
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

@permission_classes([IsAuthenticated])
@api_view(['DELETE'])
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

@permission_classes([IsAuthenticated])
@api_view(['GET','POST','DELETE'])
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



@permission_classes([IsAuthenticated])
@api_view(['GET','POST'])
def OrdersView(request):
    user = request.user
    is_manager = request.user.groups.filter(name="manager").exists()
    is_delivery = request.user.groups.filter(name="delivery-crew").exists()
    
    if request.method == 'GET':
        if not is_manager and not is_delivery:
            # not be a manager or delevery crew user
            orders = Order.objects.filter(user=user.id)
            
            orderI = OrderSerializer(data = orders, many =True)
            
            orderI.is_valid()
            return Response(orderI.data)
        else:
            if is_manager:
                orders = Order.objects.all()
                allOrders = OrderSerializer(data=orders,many=True)
                allOrders.is_valid()
                return Response(allOrders.data)

            if is_delivery:
                orders = Order.objects.filter(delivery_crew=user.id)
                orderDelivery = OrderSerializer(data=orders,many=True)
                orderDelivery.is_valid()
                return Response(orderDelivery.data)

    if request.method == 'POST':    
        cart = Cart.objects.filter(user=user.id)
        print(cart)
        if not cart:
            return Response({'message':"cart must not be empty"},
                        status= status.HTTP_400_BAD_REQUEST)

        total = 0
        for item in cart:
            total += item.price
        print(total)
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

    
@permission_classes([IsAuthenticated])
@api_view(['GET','POST','DELETE',"PATCH"])
def orderById(request,orderId):
    user = request.user

    is_manager = request.user.groups.filter(name="manager").exists()
    is_delivery = request.user.groups.filter(name="delivery-crew").exists()

    if request.method == 'GET':
        if not is_delivery and not is_delivery:
            order = Order.objects.filter(id=orderId,user=user.id)
            if not order:
                return Response({'message':"this order does not exist"},
                                status= status.HTTP_400_BAD_REQUEST)

            orderI = OrderSerializer(data = order,many=True)
            orderI.is_valid(raise_exception = True)
            print(orderI.data)
            return Response(orderI.data[0])

    
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
         
            orderUpdate = OrderSerializer(order,data={
                'status':statusOrder,
                "user": order.user.id,
                "date":order.date,
                "total":order.total
                })
            orderUpdate.is_valid(raise_exception = True)
            orderUpdate.delivery_crew = id_crew

            orderUpdate.save()
            return Response(orderUpdate.data)
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
    #     if is_delivery:
    #         statusOrder = request.data.get("status")
    #         if ( not statusOrder == 1  and not statusOrder == 0):
    #             return Response({'message':"invalid status field"},
    #                         status= status.HTTP_400_BAD_REQUEST)
    #         order = Order.objects.filter(id=orderId).first()
    #         orderUpdate = OrderSerializer(order,data={
    #             'status':statusOrder,
    #             "user": order.user.id,
	#             "date":order.date,
    #             "total":order.total
    #             })
    #         orderUpdate.is_valid(raise_exception = True)
    #         orderUpdate.save()
    #         return Response(orderUpdate.data)
    # if request.method == 'PATCH' or request.methods=='POST':
    #     is_manager = request.user.groups.filter(name="manager").exists()
    #     is_delivery = request.user.groups.filter(name="delivery-crew").exists()

    #     if not is_manager and not is_delivery:
            
    #         statusOrder = request.data.get("status")
    #         if ( not statusOrder == 1  and not statusOrder == 0):
    #             return Response({'message':"invalid status field"},
    #                         status= status.HTTP_400_BAD_REQUEST)
    #         order = Order.objects.filter(id=orderId,user=user.id).first()
    #         if not order:
    #                 return Response({'message':"item not found"},status= status.HTTP_404_NOT_FOUND)


    #     orderUpdate = OrderSerializer(order,data={
    #         'status':statusOrder,
    #         "user": order.user.id,
    #         "date":order.date,
    #         "total":order.total
    #         })
    #     orderUpdate.is_valid(raise_exception = True)
    #     orderUpdate.save()
    #     return Response(orderUpdate.data)



    
    