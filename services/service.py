import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import uuid
from google.auth.transport import requests
import google.oauth2.id_token
from fastapi import Request, Response, UploadFile
from fastapi import HTTPException
from pydantic import Json
from models.models import Comment, CommentInput, Post, PostInput, PostOutput, User, UserProfileUpdate
from google.cloud import firestore,storage
import local_constants
import starlette.status as status

firestore_db = firestore.Client()

firebase_request_adapter = requests.Request()

class Service:

    @staticmethod
    def get_all_posts(user:User,username):
        try:
            posts_query = firestore_db.collection("Post") \
            .where("Username", "==", username) \
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
            profile_user_query = firestore_db.collection("User").where("Username", "==", username).limit(1).stream()
            profile_user_docs = list(profile_user_query)
            if not profile_user_docs:
                raise Exception("profile not found")
            profile_user_data = profile_user_docs[0].to_dict()
            is_following = False
            if user and hasattr(user, "Following"):
                # Check if profile user's ID is in user's Following list
                if any(item.get("Username") == username for item in user.Following):
                    is_following = True
            data = {
                "profile": profile_user_data,
                "profile_username": username,
                "profile_name": profile_user_data.get("Name", username),
                "bio": profile_user_data.get("Bio", ""),
                "profile_pic_url": profile_user_data.get("Profile_Pic_Url", "default_user.jpeg"),
                "is_following": is_following,
                "is_own_profile": user.Username == username,
                "posts": posts,
            }
            return data
        except Exception as e:
            print(e)
            print(f"in service {str(e)}")
            raise Exception(str(e))

    def firestore_to_datetime(timestamp):
        if timestamp is None:
            return None
            
        if hasattr(timestamp, 'year'):
            return timestamp
        
        try:
            return timestamp.datetime
        except AttributeError:
            try:
                return timestamp.ToDatetime()
            except AttributeError:
                try:
                    import datetime
                    return datetime.datetime.fromtimestamp(timestamp)
                except (TypeError, ValueError):
                    print(f"Could not convert timestamp: {type(timestamp)}")
                    return None

    @staticmethod
    def get_comments(post_id:str):
        try:
            comments_data = firestore_db.collection('Comment').where('PostId', '==', post_id).order_by("Date", direction=firestore.Query.DESCENDING).stream()
            
            comments = []
            for doc in comments_data:
                data = doc.to_dict()
                timestamp = Service.firestore_to_datetime(data.get('Date'))
                comment = {
                    "text":data['Text'],
                    "username":data['Username'],
                    "timestamp": timestamp.isoformat() if timestamp else None 
                }
                comments.append(comment)
            
            return comments

        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))

    @staticmethod
    def add_comment(user:User,post_id:UUID,comment_input:CommentInput)->None:
        try:
            print(len(comment_input.text))
            if comment_input.text.strip() == "":
                raise Exception("comment cannot be empty")
            if len(comment_input.text) >200:
                raise Exception("comment can atmost have 200 characters")
            comment = Comment(
                Id = str(uuid.uuid4()),
                PostId = str(post_id),
                Username = user.Username,
                Text = comment_input.text,
                Date=None   ,
            )
            comment_dict = comment.dict()
            comment_dict['Id'] = str(comment_dict['Id'])
            comment_dict['PostId'] = str(comment_dict['PostId'])
            comment_dict['Date'] = firestore.SERVER_TIMESTAMP
            firestore_db.collection('Comment').add(comment_dict)
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))
        

    @staticmethod
    def update_user(user:User,profile_data:UserProfileUpdate):
        try:
            
            if profile_data.username.strip() is None or profile_data.profile_name.strip() is None:
                raise Exception("please enter username as well as profile name")
            if len(profile_data.username) < 6 or len(profile_data.profile_name) < 6:
                raise Exception("ensure profile name and username must be atleast 6 characters long")
            existing_users = firestore_db.collection('User').where('Username', '==', profile_data.username).get()
            if existing_users:
                raise Exception("username already exists.please use another one")
            updates = {
                "Username": profile_data.username.lower()
            }
            if profile_data.bio is not None:
                updates["Bio"] = profile_data.bio
            if profile_data.profile_pic_url is not None:
                updates["Profile_Pic_Url"] = profile_data.profile_pic_url
            if profile_data.profile_pic_url is  None:
                updates["Profile_Pic_Url"] = "default_user.jpeg"
            if profile_data.profile_name is not None:
                updates["Profile_Name"] = profile_data.profile_name.lower()
            firestore_db.collection('User').document(str(user.Id)).update(updates)
        except Exception as e:
            print("in service")
            print(str(e))
            raise Exception(str(e))
        
    @staticmethod
    def get_all_user_following(user: User):
        try:
            following = user.Following
            following_data = []
            
            for following_item in following:
                following_username = following_item.get("Username")
                if not following_username:
                    continue
                    
                docs = firestore_db.collection('User').where('Username', '==', following_username).get()
                if docs:
                    following_doc = docs[0]
                    following_data_dict = following_doc.to_dict()
                    
                    if following_data_dict:
                        # Get the date when started following
                        following_date = following_item.get("Date", "")
                        
                        following_data.append({
                            "Username": following_data_dict.get("Username", ""),
                            "Bio": following_data_dict.get("Bio", ""),
                            "profile_pic_url": following_data_dict.get("Profile_Pic_Url", "default_user.jpeg"),
                            "is_following": True,  # Always true since it's in the following list
                            "Profile_Name": following_data_dict.get("Profile_Name", ""),
                            "following_since": following_date  # Include the date they started following
                        })
                    else:
                        raise Exception("User not found")
            
            return following_data
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))

    @staticmethod
    def get_all_user_followers(user: User):
        try:
            followers = user.Followers
            followers_data = []
            
            following_usernames = [item.get("Username") for item in user.Following] if user.Following else []
            
            for follower_item in followers:
                follower_username = follower_item.get("Username")
                if not follower_username:
                    continue
                    
                docs = firestore_db.collection('User').where('Username', '==', follower_username).get()
                if docs:
                    follower_doc = docs[0]
                    follower_data = follower_doc.to_dict()
                    
                    if follower_data:
                        is_following = follower_username in following_usernames
                        
                        follower_date = follower_item.get("Date", "")
                        
                        followers_data.append({
                            "Username": follower_data.get("Username", ""),
                            "Bio": follower_data.get("Bio", ""),
                            "profile_pic_url": follower_data.get("Profile_Pic_Url", "default_user.jpeg"),
                            "is_following": is_following,
                            "Profile_Name": follower_data.get("Profile_Name", ""),
                            "follower_since": follower_date  # Include the date they started following
                        })
                    else:
                        raise Exception("User not found")
            
            return followers_data
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))
                

    @staticmethod
    def get_all_users_for_search(user: User, query: str):
        try:
            query = query.lower()
            users_ref = firestore_db.collection('User')
            end_query = query + u'\uf8ff'
            query_ref = users_ref.where("Profile_Name", ">=", query).where("Profile_Name", "<=", end_query)
            users_docs = query_ref.stream()
            users = []
            
            # Extract usernames from Following list of dictionaries
            following_usernames = [item.get("Username") for item in user.Following] if user.Following else []
            
            for user_doc in users_docs:
                data = user_doc.to_dict()
                username = data.get("Username", "")
                if username == user.Username:
                    continue
                
                # Check if username is in following_usernames
                is_following = username in following_usernames
                
                users.append({
                    "Username": username,
                    "Profile_Name": data.get("Profile_Name", ""),
                    "Bio": data.get("Bio", ""),
                    "profile_pic_url": data.get("Profile_Pic_Url", "default_user.jpeg"),
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
        try:
            content_type = file_name.content_type
            allowed_types = ["image/jpeg", "image/png"]
            if content_type not in allowed_types:
                raise Exception("please upload only jpeg or png files")
            await Service.addFile(file_name)
        except Exception as e:
            print("in service")
            print(e)
            raise Exception(str(e))
        

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
    def unfollow_user(user: User, unfollow_user_username: str) -> Json:
        try:
            do_unfollow_user_exist = next(firestore_db.collection("User").where("Username", "==", unfollow_user_username).stream(), None)
            if do_unfollow_user_exist is None:
                raise Exception('User does not exist')
            
            follow_user = User(**do_unfollow_user_exist.to_dict())
            
            # Remove by username
            user.Following = [item for item in user.Following if item.get("Username") != unfollow_user_username]
            follow_user.Followers = [item for item in follow_user.Followers if item.get("Username") != user.Username]

            firestore_db.collection("User").document(str(user.Id)).update({
                "Following": user.Following
            })
            
            firestore_db.collection("User").document(str(follow_user.Id)).update({
                "Followers": follow_user.Followers
            })
            return {"message": "success"}
        except Exception as e:
            print(e)
            raise Exception(e)



    @staticmethod
    def follow_user(user: User, follow_user_username: str) -> Json:
        try:
            do_follow_user_exist = next(firestore_db.collection("User").where("Username", "==", follow_user_username).stream(), None)
            if do_follow_user_exist is None:
                raise Exception('User does not exist')
            
            follow_user = User(**do_follow_user_exist.to_dict())

            if any(item.get("Username") == follow_user_username for item in user.Following):
                raise Exception("you are already following the user")
            
            current_date = datetime.datetime.now().isoformat()
            user.Following.append({"Username": follow_user_username, "Date": current_date})
            follow_user.Followers.append({"Username": user.Username, "Date": current_date})

            firestore_db.collection("User").document(str(user.Id)).update({
                "Following": user.Following
            })

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
            for following_item in user_obj.Following:
                usernames.append(following_item.get("Username"))
            posts_query = firestore_db.collection("Post") \
            .where("Username", "in", usernames) \
            .order_by("Date", direction=firestore.Query.DESCENDING) \
            .limit(50) \
            .stream()
            posts = [PostOutput(**doc.to_dict()) for doc in posts_query]
            for post in posts:
                post.Id = str(post.Id)
                post.UserId = str(post.UserId)
                post.User_Pic = post.User_Pic = firestore_db.collection('User').where('Id', '==', post.UserId).get()[0].to_dict().get("Profile_Pic_Url", "default_user.jpeg")
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

            name = str(uuid.uuid4())
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
            # Extract usernames from Following list of dictionaries
            following_usernames = [item.get("Username") for item in user.Following] if user.Following else []

            users_refs = firestore_db.collection("User").stream()

            suggested_users = []
            for doc in users_refs:
                user_data = doc.to_dict()
                if (user_data["Username"] != current_username and 
                    user_data["Username"] not in following_usernames):
                    
                    user_obj = User(
                        Id=UUID(user_data["Id"]),
                        Username=user_data["Username"],
                        Email=user_data["Email"],
                        Followers=user_data.get("Followers", []),
                        Following=user_data.get("Following", []),
                    )
                    if user_data.get('Profile_Pic_Url') == None:
                        user_obj.Profile_Pic_Url = 'default_user.jpeg'
                    else:
                        user_obj.Profile_Pic_Url = user_data["Profile_Pic_Url"]
                    
                    # Include Profile_Name if available
                    if user_data.get('Profile_Name'):
                        user_obj.Profile_Name = user_data["Profile_Name"]
                    
                    suggested_users.append(user_obj)

            return suggested_users

        except Exception as e:
            raise Exception(f"Error suggesting users: {str(e)}")