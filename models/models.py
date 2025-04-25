from typing import List, Optional

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
    Followers: List[str] = []
    Following: List[str] = []
    Bio:Optional[str] = None
    Profile_Pic_Url: Optional[str] = None

class UserProfileUpdate(BaseModel):
    username: str
    bio: Optional[str] = None
    profile_pic_url: Optional[str] = None

class Comment(BaseModel):
    PostId:UUID
    Text:str
    Id:UUID
    UserId:UUID


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
    location:str


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