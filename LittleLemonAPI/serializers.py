from rest_framework import serializers
from django.contrib.auth.models import User
from .models import MenuItem,Category,Cart,Order,OrderItem



class CategorySerializer (serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id','slug','title']
    def __str__(self) -> str:
        return self.title


class UserSerilizer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id",'email', 'username', 'password']
        extra_kwargs = {
            'email': {'required': True,},
            'password': {'write_only': True,'min_length':4},
            }

    def create(self,pas):
        user = User(
        email=self.data['email'],
        username=self.data['username']
        )
        user.set_password(pas)
        user.save()
        return user

class MenuItemsSerlizer(serializers.ModelSerializer):
    category = CategorySerializer()
    class Meta:
        model = MenuItem
        fields = ["id","title","price","featured","category"]


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields ="__all__"
    def validate_quantity(self,value):
        if not value > 0:
            raise serializers.ValidationError("quiantity must be grather than 0")
        return value



class OrderSerializer(serializers.ModelSerializer):
    menuitems = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = ['id',"user","delivery_crew","total","date","menuitems","status"]

    def get_menuitems(self,order):

        items = OrderItem.objects.filter(
            order=order.id
        )
        menuItems = OrderItemSerializer(data=items,many=True)
        menuItems.is_valid()
        return menuItems.data


class OrderItemSerializer(serializers.ModelSerializer):
    orderItem = serializers.PrimaryKeyRelatedField(many=True,read_only=True)
    class Meta:
        model = OrderItem
        fields = "__all__"