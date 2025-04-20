from typing import Optional
from fastapi import FastAPI, HTTPException, Request,Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore
import google.oauth2.id_token
from fastapi.responses import RedirectResponse

app = FastAPI()



app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=JSONResponse)
def root(request:Request):
    return {"hello":"assignment - 3"}


