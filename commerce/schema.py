import graphene
from graphene_django import DjangoObjectType
from .models import User, Product, Order, OrderItem, Payment
from django.db.models import Q


# define custom type to interact with django models

# for nested queries, we can define more complex types and resolvers as needed
class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "username", "email")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product 
        fields = ("id", "owner","name", "price", "category", "stock")

    # optimize query with filtering and pagination...
    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset.filter(category__icontains=["electronics"])

# get all products
def all_products(root, info):
    return Product.objects.all()

# entry point for GraphQL queries
class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, World! this is a test for GraphQL endpoint in commerce app.")
    products = graphene.List(ProductType)

    # passing arguments to types
    item = graphene.Field(ProductType, id=graphene.Int())
    search_products = graphene.List(ProductType, search=graphene.String())
    # all_products = graphene.List(ProductType, resolver=lambda root, info: Product.objects.all())

    products_all = graphene.List(ProductType, resolver=all_products)

    def resolve_hello(root, info):
        return f"hello {root} | {info.is_awaitable}"

    def resolve_products(root, info):
        # TODO use select_related or prefetch_related to optimize queries if needed(django silk)
        return Product.objects.all()

    def resolve_item(root, info, id):
        try:
            return Product.objects.get(pk=id)
        except Product.DoesNotExist:
            return None

    def resolve_search_products(root, info, search=None):
        qs = Query.resolve_products(root, info)

        # if search keyword is supplied
        if search:
            return qs.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(owner__username__icontains=search)
            ).distinct()

        # no search keyword
        return qs

# creating custom mutations
class CreateProductMutation(graphene.Mutation):

    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()
        category = graphene.String()
        price = graphene.Decimal()
        stock = graphene.Int()

    # class attribute defines the response of the mutation
    product = graphene.Field(ProductType)
    
    @classmethod
    def mutate(cls, root, info, name, description, category, price, stock):
        # user = info.context.user
        # if user.is_anonymous:
        #     raise Exception("Authentication required to create a product.")
        
        product = Product(
            name=name,
            description=description,
            category=category,
            price=price,
            stock=stock
        )
        product.save()

        # return instance of the mutation class with the created product
        return CreateProductMutation(product=product)

# delete product mutations
class DeleteProductMutation(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)
        
    # class attribute defines the response of the mutation
    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

    
    @classmethod
    def mutate(cls, root, info, id):
        try:
            product = Product.objects.get(pk=id)
            product.delete()
            return DeleteProductMutation(success=True, message="Product deleted successfully", product=product)
        except Product.DoesNotExist:
             return DeleteProductMutation(success=False, message=f"Product with id {id} does not exist.")



class UpdateProductMutation(graphene.Mutation):

    class Arguments:
        id = graphene.Int(required=True)
        price = graphene.Decimal()
        stock = graphene.Int()

    # class attribute defines the response of the mutation
    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()
    
    @classmethod
    def mutate(cls, root, info, id, price, stock):
        try:
            product = Product.objects.get(pk=id)
            if price:
                product.price = price
            if stock:
                product.stock = stock

            product.save()
           
            # return instance of the mutation class with the created product
            return UpdateProductMutation(product=product)
        except Product.DoesNotExist:
                return UpdateProductMutation(success=False, message=f"Product with id {id} does not exist.")


class Mutation(graphene.ObjectType):
    # registering the mutation(s) with a name that can be called from the client
    create_product = CreateProductMutation.Field()
    delete_product = DeleteProductMutation.Field()
    update_product = UpdateProductMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
