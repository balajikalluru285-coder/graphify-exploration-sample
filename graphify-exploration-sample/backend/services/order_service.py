from repositories.user_repository import get_user

def create_order(user_id, product_id):
    user = get_user(user_id)
    return {
        "status": "created",
        "user": user,
        "product_id": product_id,
    }
