# apps/util/auth.py

import os
from fastapi import Depends, HTTPException, Header
from dotenv import load_dotenv

load_dotenv()

def verify_token(x_api_token: str = Header(...)):
    expected_token = os.getenv("API_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="Token not configured")
    if x_api_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid token")
