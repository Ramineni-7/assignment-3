import datetime
from typing import Dict, Optional
from fastapi import FastAPI, File, HTTPException, Request,Form, Depends, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore,storage
import google.oauth2.id_token
from fastapi.responses import RedirectResponse
from models.models import  Post, PostInput, UserProfileUpdate
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
        return JSONResponse(status_code=500,content="uploaded failed")
    
@app.get("/profile",response_class=HTMLResponse)
def profile(request:Request):
    try:
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":None}
        )
        posts = Service.get_posts(user)
        return templates.TemplateResponse(
            "profile.html",
            {"request":request,"posts":posts,"is_own_profile":True,"user":user}
        )
    except Exception as e:
        print(e)


@app.get("/images/{file_name}",response_class=Response)
def download_file(request:Request,file_name:str):
    try:
        print(file_name)
        if file_name.startswith("file_name="):
            actual_filename = file_name[10:]
            return Service.download_file(actual_filename)
        return Service.download_file(file_name)
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