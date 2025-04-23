from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid
from google.auth.transport import requests
from google.cloud import firestore
import google.oauth2.id_token
from fastapi import Request
from fastapi import HTTPException
from datetime import date, datetime, time

from pydantic import Json

from models.models import Comment, Post, User

firestore_db = firestore.Client()

firebase_request_adapter = requests.Request()

class Service:

    @staticmethod
    def unfollow_user(user:User,unfollow_user_username:str)->Json:
        try:
            do_unfollow_user_exist = next(firestore_db.collection("User").where("Username", "==", unfollow_user_username).stream(), None)
            if do_unfollow_user_exist is None:
                raise Exception('User does not exist')
            
            follow_user = User(**do_unfollow_user_exist.to_dict())
            print(user.Following)
            print(unfollow_user_username)
            if not (user.Following.__contains__(unfollow_user_username)):
                raise Exception("you are alredy unfollowed  the user")
            
            user.Following.remove(unfollow_user_username)

            follow_user.Followers.remove(user.Username)

            firestore_db.collection("User").document(str(user.Id)).update({
                "Following": user.Following
            })
            print("1 done")
            firestore_db.collection("User").document(str(follow_user.Id)).update({
                "Followers": follow_user.Followers
            })
            return {"message":"sucess"}
        except Exception as e:
            print(e)
            raise Exception(e)



    @staticmethod
    def follow_user(user:User,follow_user_username:str)->Json:
        try:
            do_follow_user_exist = next(firestore_db.collection("User").where("Username", "==", follow_user_username).stream(), None)
            if do_follow_user_exist is None:
                raise Exception('User does not exist')
            
            follow_user = User(**do_follow_user_exist.to_dict())

            if follow_user_username in user.Following:
                raise Exception("you are alredy following the user")
            user.Following.append(follow_user_username)

            follow_user.Followers.append(user.Username)

            firestore_db.collection("User").document(str(user.Id)).update({
                "Following": user.Following
            })
            print("1 done")
            firestore_db.collection("User").document(str(follow_user.Id)).update({
                "Followers": follow_user.Followers
            })

        except Exception as e:
            print(e)
            raise Exception(e)

    @staticmethod
    def get_data_for_root(user:Dict):
        try:
            posts = Service.get_posts(user)
            suggested_users = Service.get_suggested_users(user)
            return {
                "posts":posts,
                "suggested_users":suggested_users
            }
        except Exception as e:
            pass

    @staticmethod
    def check_login_and_return_user(request:Request)->Dict:
        token = request.cookies.get("token")
        if not token:
            return None
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(token, firebase_request_adapter)
            if not user_token:
                return None

            email = user_token.get("email")
            if not email:
                return None
            user_doc = next(firestore_db.collection("User").where("Email", "==", email).stream(), None)
            if not user_doc:
                raise Exception("user not found")
            user = User(**user_doc.to_dict())
            return user
        except Exception as e:
            print(f"in service {str(e)}")
            raise Exception(str(e))
    
    @staticmethod
    def get_posts(user:Dict)->List[Post]:
        try:
            
            user_doc = next(firestore_db.collection("User").where("Email", "==", user.Email ).stream(), None)
            if not user_doc:
                raise Exception("user not found")
            user_obj = User(**user_doc.to_dict())
            usernames = []
            usernames.append(user_obj.Username)
            for following in user_obj.Following:
                usernames.append(following)
            posts_query = firestore_db.collection("Post") \
            .where("Username", "in", usernames) \
            .order_by("Date", direction=firestore.Query.DESCENDING) \
            .limit(50) \
            .stream()
            posts = [Post(**doc.to_dict()) for doc in posts_query]
            for post in posts:
                comment_doc = firestore_db.collection('Comment').where('PostId','==',post.Id).stream()
                comments = [Comment(**doc.to_dict()) for doc in comment_doc]
                post.comments = comments
            
            return posts
        except Exception as e:
            print(e)
            print(f"in service {str(e)}")
            raise Exception(str(e))
        

    
    @staticmethod
    def create_user_into_firestore(request:Request)->None:
        token = request.cookies.get("token")
        if not token:
            return None
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(token, firebase_request_adapter)
            if not user_token:
                return None

            email = user_token.get("email")
            if not email:
                return None

            name = email.split("@")[0]
            users_ref = firestore_db.collection("User")
            existing_users = users_ref.where("Email", "==", email).limit(1).stream()

            if not any(existing_users):
                print("adding")
                user_id = str(uuid.uuid4())
                users_ref.document(user_id).set({
                    "Id": user_id,
                    "Email": email,
                    "Username": name,
                    "Followers": [],
                    "Following": []
                })
        except Exception as e:
            print("in service")
            print(str(e))
            raise Exception(str(e))
    
    @staticmethod
    def get_suggested_users(user: User) -> List[User]:
        try:
            current_username = user.Username
            following = user.Following or []

            users_ref = firestore_db.collection("User").stream()

            suggested_users = []
            for doc in users_ref:
                user_data = doc.to_dict()
                if user_data["Username"] != current_username and user_data["Username"] not in following:
                    user_obj = User(
                        Id=UUID(user_data["Id"]),
                        Username=user_data["Username"],
                        Email=user_data["Email"],
                        Followers=user_data.get("Followers", []),
                        Following=user_data.get("Following", [])
                    )
                    suggested_users.append(user_obj)

            return suggested_users

        except Exception as e:
            raise Exception(f"Error suggesting users: {str(e)}")