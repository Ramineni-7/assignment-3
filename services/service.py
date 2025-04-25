import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import uuid
from google.auth.transport import requests
import google.oauth2.id_token
from fastapi import Request, Response, UploadFile
from fastapi import HTTPException
from pydantic import Json
from models.models import Comment, Post, PostInput, PostOutput, User, UserProfileUpdate
from google.cloud import firestore,storage
import local_constants
import starlette.status as status

firestore_db = firestore.Client()

firebase_request_adapter = requests.Request()

class Service:

    @staticmethod
    def update_user(user:User,profile_data:UserProfileUpdate):
        try:
            existing_users = firestore_db.collection('User').where('Username', '==', profile_data.username).get()
            if existing_users:
                raise Exception("username already exists.please use another one")
            updates = {
                "Username": profile_data.username
            }
            if profile_data.bio is not None:
                updates["Bio"] = profile_data.bio
            if profile_data.profile_pic_url is not None:
                updates["Profile_Pic_Url"] = profile_data.profile_pic_url
            firestore_db.collection('User').document(str(user.Id)).update(updates)
        except Exception as e:
            print("in service")
            print(str(e))
            raise Exception(str(e))
    @staticmethod
    def get_all_user_following(user:User):
        try:
            following = user.Following
            following_data = []
            for follower in following:
                docs = firestore_db.collection('User').where('Username','==',follower).get()
                if docs:
                    follower_doc = docs[0]
                    follower_data = follower_doc.to_dict()
                if follower_data:
                    is_following = follower in user.Following
                    
                    following_data.append({
                        "Username": follower_data.get("Username", ""),
                        "Bio": follower_data.get("Bio", ""),
                        "profile_pic_url": follower_data.get("profile_pic_url", ""),
                        "is_following": True
                    })
                else:
                    raise Exception("User not found")
                return following_data
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))

    @staticmethod
    def get_all_user_followers(user:User):
        try:
            followers = user.Followers
            followers_data = []
            for follower in followers:
                docs = firestore_db.collection('User').where('Username','==',follower).get()
                if docs:
                    follower_doc = docs[0]
                    follower_data = follower_doc.to_dict()
                if follower_data:
                    is_following = follower in user.Following
                    
                    followers_data.append({
                        "Username": follower_data.get("Username", ""),
                        "Bio": follower_data.get("Bio", ""),
                        "profile_pic_url": follower_data.get("profile_pic_url", ""),
                        "is_following": is_following
                    })
                else:
                    raise Exception("User not found")
                return followers_data
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))
                

    @staticmethod
    def get_all_users_for_search(user:User,query:str):
        try:
            users_ref = firestore_db.collection('User')
            end_query = query + u'\uf8ff'
            query_ref = users_ref.where("Username", ">=", query).where("Username", "<=", end_query)
            users_docs = query_ref.stream()
            users = []
            for user_doc in users_docs:
                data = user_doc.to_dict()
                username = data.get("Username","")
                if username == user.Username:
                    continue
                
                is_following = username in user.Following
                
                users.append({
                    "Username": username,
                    "Bio": data.get("Bio", ""),
                    "profile_pic_url": data.get("profile_pic_url", ""),
                    "is_following": is_following
                })

            return users
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(e)
    @staticmethod
    def get_all_users(user:User)->List[User]:
        try:
            users_ref = firestore_db.collection('User').get()
            users = []
            for doc in users_ref:
                data = doc.to_dict()
                fetched_user = User(
                    Id=UUID(data['Id']),
                    Username=data['Username'],
                    Email=data['Email'],
                    Followers=data.get('Followers', []),
                    Following=data.get('Following', [])
                )
                if fetched_user.Id != user.Id:
                    users.append(fetched_user)
            return users
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []
    @staticmethod
    def download_file(filename:str):
        try:
            return Response(Service.downloadBlob(filename))
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))

    @staticmethod
    def create_post(user:User,post_input_data:PostInput)->Post:
        try:
            if len(post_input_data.caption) > 500:
                raise Exception("no more than 500 characters please")
            post = Post(
                Id=str(uuid.uuid4()), 
                UserId=str(user.Id),  
                Username=user.Username,
                Caption=post_input_data.caption,
                Date=datetime.datetime.utcnow().isoformat(),
                Likes=0,
                Image_ref=post_input_data.image_ref
            )
            post.Id = str(post.Id)
            post.UserId = str(post.UserId)
            print(type(post.Id))
            firestore_db.collection("Post").add(post.dict())
            return post
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))

    @staticmethod
    async def upload_file(request: Request,file_name:UploadFile):
        # if file_name.filename.filename == "":
        #     raise Exception("file name is empty")
        await Service.addFile(file_name)
        

    @staticmethod
    def downloadBlob(filename):
        try:
            storage_client = storage.Client(project=local_constants.PROJECT_NAME)
            bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
            blob = bucket.get_blob(filename)
            return blob.download_as_bytes()
        except Exception as e:
            print("downalod blob ")
            print(e)
            raise Exception(e)

    @staticmethod
    async def blobList(prefix):
        try:
            storage_client = storage.Client(project=local_constants.PROJECT_NAME)
            return storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET, prefix=prefix)
        except Exception as e:
            print(e)
            raise Exception(e)

    @staticmethod
    async def addFile(file)->None:
        try:
            storage_client = storage.Client(project=local_constants.PROJECT_NAME)
            bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
            print(file)
            blob = storage.Blob(file.filename, bucket)
            blob.upload_from_file(file.file)
        except Exception as e:
            print(e)
            raise Exception(e)

    @staticmethod
    async def addDirectory(directory_name)->None:
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        blob = bucket.blob(directory_name)
        blob.upload_from_string('', content_type='application/x-www-form-urlencoded; charset=UTF-8')

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
            print(e)
            raise Exception(e)

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
            posts = [PostOutput(**doc.to_dict()) for doc in posts_query]
            for post in posts:
                post.Id = str(post.Id)
                post.UserId = str(post.UserId)
                post.User_Pic = post.User_Pic = firestore_db.collection('User').where('Id', '==', post.UserId).get()[0].to_dict().get("profile_pic_url", "")
                if isinstance(post.Date, datetime.datetime):
                    post.Date = post.Date.isoformat()
                comment_doc = firestore_db.collection('Comment').where('PostId','==',post.Id).stream()
                comments = [Comment(**doc.to_dict()) for doc in comment_doc]
                post.Comments = comments
            
            return posts
        except Exception as e:
            print(e)
            print(f"in service {str(e)}")
            raise Exception(str(e))
        

    
    @staticmethod
    def create_user_into_firestore(request:Request)->bool:
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
                return True
            return False
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
                        Following=user_data.get("Following", []),
                    )
                    if user_data.get('Profile_Pic_Url') == None:
                        user_obj.Profile_Pic_Url = 'default_user.jpeg'
                    else :
                        user_obj.Profile_Pic_Url=user_data["Profile_Pic_Url"]
                    suggested_users.append(user_obj)

            return suggested_users

        except Exception as e:
            raise Exception(f"Error suggesting users: {str(e)}")