# recommendations/simple_recommender.py
from django.db.models import Count
from commerce.models import OrderItem, Product

def simple_recommendations(product_id, limit=4):
    """
    Find products that are often bought together
    Based on order history
    """
    try:
        # Find orders containing this product
        order_ids = OrderItem.objects.filter(
            product_id=product_id
        ).values_list('order_id', flat=True)
        
        # Find other products in those same orders
        recommended = OrderItem.objects.filter(
            order_id__in=order_ids
        ).exclude(
            product_id=product_id  # Exclude the current product
        ).values(
            'product_id'
        ).annotate(
            purchase_count=Count('product_id')
        ).order_by(
            '-purchase_count'  # Most frequently bought together
        )[:limit]
        
        # Get product details
        product_ids = [item['product_id'] for item in recommended]
        return Product.objects.filter(id__in=product_ids)
        
    except Exception:
        # Fallback: return featured products
        return Product.objects.filter(is_active=True, is_featured=True)[:limit]
    