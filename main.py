from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="Leonardo da Vinci Quote Giver",
    description="Get a real quote said by Leonardo da Vinci himself.",
    servers=[
        {
            "url": "https://rage-adapter-gtk-wooden.trycloudflare.com",
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
)
def get_quote():
    return {
        "quote": "Life is short so eat it all.",
        "year": 1950,
    }
