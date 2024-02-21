from typing import Any, Dict
from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Leonardo da Vinci Quote Giver",
    description="Get a real quote said by Leonardo da Vinci himself.",
    servers=[
        {
            "url": "https://representation-issue-adding-producer.trycloudflare.com",
        },
    ],
)


class Quote(BaseModel):
    quote: str = Field(
        description="The quote that Leonardo da Vinci said.",
    )
    year: int = Field(
        description="The year when Leonardo da Vinci said the quote.",
    )


@app.get(
    "/quote",
    summary="Returns a random quote by Leonardo da Vinci",
    description="Upon receiving a GET request this endpoint will return a real quiote said by Leonardo da Vinci himself.",
    response_description="A Quote object that contains the quote said by Leonardo da Vinci and the date when the quote was said.",
    response_model=Quote,
    openapi_extra={
        "x-openai-isConsequential": False,
    },
)
def get_quote(request: Request):
    print(request.headers)
    return {
        "quote": "Life is short so eat it all.",
        "year": 1950,
    }


user_token_db = {"ABCDEF": "minjae"}


@app.get(
    "/authorize",
    response_class=HTMLResponse,
)
def handle_authorize(client_id: str, redirect_uri: str, state: str):
    return f"""
    <html>
        <head>
            <title>Leonardo da Vinci Log In</title>
        </head>
        <body>
            <h1>Log Into Leonardo da Vinci</h1>
            <a href="{redirect_uri}?code=ABCDEF&state={state}">Authorize Leonardo da Vinci GPT</a>
        </body>
    </html>
    """


@app.post("/token")
def handle_token(code=Form(...)):
    return {
        "access_token": user_token_db[code],
    }
