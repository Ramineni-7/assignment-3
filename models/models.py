from typing import Dict, List, Optional

from datetime import date, time, datetime
from uuid import UUID
from fastapi import File, Form
from pydantic import BaseModel, Field


class Post(BaseModel):
    Id:UUID
    UserId:UUID
    Username:str
    Caption:str
    Date:Optional[datetime] = None
    Likes:int
    Image_ref:str




class User(BaseModel):
    Id:UUID
    Username:str
    Email:str
    Followers: List[Dict] = []
    Following: List[Dict] = []
    Bio:Optional[str] = None
    Profile_Pic_Url: Optional[str] = None
    Profile_Name:Optional[str] = None

class UserProfileUpdate(BaseModel):
    username: str
    bio: Optional[str] = None
    profile_pic_url: Optional[str] = None
    profile_name:Optional[str] = None

class Comment(BaseModel):
    PostId:UUID
    Text:str
    Id:UUID
    Username:str
    Date:Optional[datetime] = None


class PostSchemaOut(BaseModel):
    Id:UUID
    Username:str
    Caption:str
    Date:Optional[datetime] = None
    Likes:int
    Comments:List[Comment] = []

class PostInput(BaseModel):
    image_ref:str
    caption:str
    location:Optional[str] = None


class PostOutput(BaseModel):
    Id:UUID
    UserId:UUID
    Username:str
    Caption:str
    Date:Optional[datetime] = None
    Likes:int
    Image_ref:str
    Comments: List[Comment] = None
    User_Pic:Optional[str] = None


class CommentInput(BaseModel):
    text:str