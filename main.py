from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Request,Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore
import google.oauth2.id_token
from fastapi.responses import RedirectResponse
from models.models import Post
from services.service import Service

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
        Service.create_user_into_firestore(request)
        user = check_login_and_return_user(request)
        if user is None:
            return templates.TemplateResponse(
                "main.html",
                {"request":request,"user":None}
            )
        data = Service.get_data_for_root(user)
        return templates.TemplateResponse(
            "main.html",
            {"request":request,"user":user,"posts":data['posts'],"suggested_users":data["suggested_users"]}
        )
    except Exception as e:
        print(str(e))
        return templates.TemplateResponse(
            "main.html",
            {"request":request}
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
    

    