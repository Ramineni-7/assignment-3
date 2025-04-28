import datetime
from typing import Dict, Optional
from uuid import UUID
from fastapi import FastAPI, File, HTTPException, Request,Form, Depends, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore,storage
import google.oauth2.id_token
from fastapi.responses import RedirectResponse
from models.models import  CommentInput, Post, PostInput, UserProfileUpdate
from services.service import Service
import local_constants
import starlette.status as status


app = FastAPI()



app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


def check_login_and_return_user(request:Request)->Dict:
    try:
        user = Service.check_login_and_return_user(request)
        return user
    except Exception as e:
        print(str(e))
        raise Exception(e)


@app.get("/", response_class=HTMLResponse)
def root(request:Request):
    try:
        new_user = Service.create_user_into_firestore(request)
        user = check_login_and_return_user(request)
        print(user)
        if user is None:
            return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        data = Service.get_data_for_root(user)
        return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":user,"posts":data['posts'],"suggested_users":data["suggested_users"],"new_user":new_user}
        )
    except Exception as e:
        print(str(e))
        return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
    

@app.get("/login", response_class=HTMLResponse)
def root(request:Request):
    try:
        new_user = Service.create_user_into_firestore(request)
        user = check_login_and_return_user(request)
        print(user)
        if user is None:
            return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        data = Service.get_data_for_root(user)
        return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":user,"posts":data['posts'],"suggested_users":data["suggested_users"],"new_user":new_user}
        )
    except Exception as e:
        print(str(e))
        return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )


@app.post("/follow/{follow_user_username}",response_class=JSONResponse)
def follow_user(request:Request,follow_user_username:str):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
        Service.follow_user(user,follow_user_username)
        return { "success": True, "message": "User followed successfully" }
    except Exception as e:
        return { "success": False, "message": str(e) }



@app.delete("/follow/{unfollow_user_username}",response_class=JSONResponse)
def unfollow_user(request:Request,unfollow_user_username:str):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
        Service.unfollow_user(user,unfollow_user_username)
        return { "success": True, "message": "User Unfollowed successfully" }
    except Exception as e:
        return { "success": False, "message": str(e) }
    

@app.get("/post", response_class=HTMLResponse)
def create_post(request:Request):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
        return templates.TemplateResponse(
            "create-post.html",
            {"request":request}
        )
    except Exception as e:
        print(str(e))
        return templates.TemplateResponse(
            "main.html",
            {"request":request}
        )
    
@app.post('/post',response_class=JSONResponse)
def create_post(request:Request,post_input:PostInput):
    try:
        print(post_input)
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
        post = Service.create_post(user,post_input)
        post_dict = post.dict()
        if isinstance(post_dict['Date'], datetime.datetime):
            post_dict['Date'] = post_dict['Date'].isoformat()
        return JSONResponse(content={"status": True, "post": post_dict}) 
    except Exception as e:
        print(e)
        return JSONResponse(content={"status": False})


@app.post('/upload-file',response_class=JSONResponse)
async def upload_file(request:Request,file_name: UploadFile = File(...)):
    try:
        print(file_name)
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request}
        )
        await Service.upload_file(request,file_name)
        return JSONResponse(content={"status": True, "filename": file_name.filename}) 
    except Exception as e:
        print(e)
        return JSONResponse(status_code=500,content={"error": str(e)})
    
@app.get("/profile/{username}",response_class=HTMLResponse)
def profile(request:Request,username:str):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
        if username == 'me':
            data = Service.get_all_posts(user,user.Username)
        else:
            data = Service.get_all_posts(user,username)
        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request,
                "posts": data['posts'],
                "is_own_profile": data['is_own_profile'],
                "user": user,
                "profile": data['profile'],
                "profile_username": data['profile_username'],
                "profile_name": data['profile_username'],
                "bio": data['bio'],
                "profile_pic_url":data['profile_pic_url'],
                "is_following": data['is_following']
            }
        )
    except Exception as e:
        print(e)


@app.get("/images/{file_name}",response_class=Response)
async def download_file(request:Request,file_name:str):
    try:
        print(file_name)
        if file_name.startswith("file_name="):
            actual_filename = file_name[10:]
            return await Service.download_file(actual_filename)
        return await Service.download_file(file_name)
    except Exception as e:
        print(e)
        return 
    
    
@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
        return templates.TemplateResponse("users.html", {
        "request": request,
        "mode": "search",
        "users": [],
        "current_user": user,
        "search_placeholder": "Search for users..."
    })
    except Exception as e:
        print(e)
        return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
    
@app.get("/api/search")
async def api_search(request:Request,query: str):
   
   try:
        user = check_login_and_return_user(request)
        if user is None:
            return {"users":None}
        users = Service.get_all_users_for_search(user,query)
        print(users)
        return {"users": users}
   except Exception as e:
       return {"users":None}
   

# Route to render the followers page
@app.get("/followers", response_class=HTMLResponse)
def followers_page(request: Request):
    try:
        user = check_login_and_return_user(request)
        if user is None:
                return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        
        followers = Service.get_all_user_followers(user)
        print(followers)
        return templates.TemplateResponse("users.html", {
            "request": request,
            "mode": "followers",
            "users": followers,
            "profile_username": user.Username,
            "current_user": user,
            "search_placeholder": f"Search {user.Username}'s followers..."
        })
    except Exception as e:
        return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
        )

@app.get("/following",response_class=HTMLResponse)
def get_all_user_following(request:Request):
    try:
        user = check_login_and_return_user(request)
        if user is None:
                return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        
        following = Service.get_all_user_following(user)
        print(following)
        return templates.TemplateResponse("users.html", {
            "request": request,
            "mode": "following",
            "users": following,
            "profile_username": user.Username,
            "current_user": user,
            "search_placeholder": f"Search {user.Username}'s following..."
        })
    except Exception as e:
        return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
        )

@app.post("/update",response_class=JSONResponse)
def update_user_profile(request:Request,profile_data:UserProfileUpdate):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        Service.update_user(user,profile_data)
        return {"status": True, "message": "Profile updated successfully"}
    except Exception as e:
        print(f"Error updating user profile: {str(e)}")
        return {"status": False, "message": f"Failed to update profile: {str(e)}"}
    
@app.post("/posts/{post_id}/comments",response_class=JSONResponse)
def add_comment(request:Request,post_id:UUID,cmoment_input:CommentInput):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        Service.add_comment(user,post_id,cmoment_input)
        return JSONResponse({
            "success": True, 
            "comment": {
                "username": user.Username, 
                "text": cmoment_input.text,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
         print(e)
         return JSONResponse({
            "success": False, 
            "message": f"Failed to add comment: {str(e)}"
        })
    
@app.get('/posts/{post_id}/comments',response_class=JSONResponse)
def get_comments(request:Request,post_id):
    print("hit atleasst")
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        comments = Service.get_comments(post_id)
        return {"comments":comments}
    except Exception as e:
        return {"status": False, "message": f"Failed to fetch comment: {str(e)}"}
    

@app.get('/post/{post_id}', response_class=HTMLResponse)
def get_post(request: Request, post_id):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
                "main.html",
                {"request": request, "user": None}
            )

        data = Service.get_post(user, post_id)

        return templates.TemplateResponse(
            "post-detail.html", {
                "request": request,
                "post": {
                    "Id": data['Id'],
                    "Username": data["Username"],
                    "User_Pic": data["User_Pic"],
                    "Image_ref": data["Image_ref"],
                    "Caption": data["Caption"],
                    "Date": data["Date"],
                    "Likes": data["Likes"],
                    "user_has_liked": False,
                    "Comments": data['Comments']
                },
                "user":user
            })
    except Exception as e:
        print(e)
