# main.py
from fastapi import FastAPI
from bs4 import BeautifulSoup

app = FastAPI()

@app.get("/")
async def read_root():
    html_doc = "<html><head><title>Title</title></head><body><p>Hello, world!</p></body></html>"
    soup = BeautifulSoup(html_doc, 'html.parser')
    return {"title": soup.title.string, "body": soup.body.p.string}
