import os
import requests
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SamResponse(BaseModel):
    user_id : str
    client_id : str
    text : str

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)


def chat_with_sam(message):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", 
                "content": """You are a helpful AI assistant.
                You reply in short simple one to two line sentence."""},
                {"role": "user", 
                "content": message}
            ]
        )

        sam_reply = response.choices[0].message.content.strip()
        print("Assistant:", sam_reply)
        return sam_reply
    
    except Exception as e:
        print("Error: ", e)
        raise HTTPException(status_code = 500, details= str(e))

@app.post("/sam")
def sam_response_api(user_details: SamResponse):
    sam_reply= chat_with_sam(user_details.text)
    return {"reply": sam_reply}


# Example conversation
if __name__ == "__main__":
    uvicorn.run("Sam_ai:app", port = 9918, host = "localhost" , reload=True)