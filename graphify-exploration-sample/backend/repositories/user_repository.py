from db.database import query_user

def get_user(user_id):
    return query_user(user_id)
