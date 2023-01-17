import os
from typing import Union, Any

from jose.exceptions import JWTClaimsError

import db
from datetime import datetime, timedelta
from fastapi import HTTPException
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
ALGORITHM = os.getenv("JWT_ALG")
JWT_ACCESS_SECRET_KEY = os.getenv("JWT_ACCESS_SECRET_KEY")


class JwtPayload(BaseModel):
    sub: str
    username: str
    first_name: str
    last_name: str
    role: str


def create_access_token(payload: JwtPayload):
    exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": payload.sub,
        "username": payload.username,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "role": payload.role,
        "exp": exp
    }
    encoded_jwt = jwt.encode(to_encode, JWT_ACCESS_SECRET_KEY, ALGORITHM)
    return encoded_jwt


def decode_jwt(token: str, secret_key: str) -> Union[dict, Any]:
    try:
        return jwt.decode(token, secret_key, ALGORITHM)
    except JWTError:
        return None


def login_result(token: Union[str, Any]):
    if token is not None:
        try:
            payload = decode_jwt(token, JWT_ACCESS_SECRET_KEY)
            token_in_db = db.sessions.get(payload["sub"])
            if token_in_db is not None:
                return True, payload
        except JWTError:
            return False
    return False


def raise_unauthorized():
    raise HTTPException(
        status_code=401,
        detail="Unauthorized",
    )


def get_user(token: Union[str, Any]) -> dict:
    if token is not None:
        try:
            return decode_jwt(token, JWT_ACCESS_SECRET_KEY)
        except JWTClaimsError:
            raise_unauthorized()
        except ExpiredSignatureError:
            raise_unauthorized()
        except JWTError:
            raise_unauthorized()
    else:
        raise_unauthorized()


def get_token(user_id):
    item = db.sessions.get(user_id)
    return item["token"] if item else None


def response_with_cookies(token: str, response):
    response.set_cookie(
        key="ACCESS_TOKEN",
        value=token,
        secure=True,
        httponly=True,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response
