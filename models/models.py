from typing import List, Optional

from datetime import date, time, datetime
from uuid import UUID
from fastapi import Form
from pydantic import BaseModel, Field


class Post(BaseModel):
    Id:UUID
    UserId:UUID
    Username:str
    Caption:str
    Date:Optional[datetime] = None
    Likes:int


class User(BaseModel):
    Id:UUID
    Username:str
    Email:str
    Followers: List[str] = []
    Following: List[str] = []


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
