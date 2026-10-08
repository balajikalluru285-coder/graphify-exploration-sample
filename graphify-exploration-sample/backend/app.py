from services.order_service import create_order

def handle_create_order(user_id, product_id):
    return create_order(user_id, product_id)

def health_check():
    return {"status": "ok"}
