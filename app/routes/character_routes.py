from flask import Blueprint, request, abort, make_response
from ..db import db
from ..models.character import Character
from ..models.greeting import Greeting
from sqlalchemy import func, union, except_
from google import genai
import os

# genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

bp = Blueprint("characters", __name__, url_prefix="/characters")

@bp.post("")
def create_character():

    request_body = request.get_json()
    try: 
        new_character = Character.from_dict(request_body)
        db.session.add(new_character)
        db.session.commit()

        return new_character.to_dict(), 201
    
    except KeyError as e:
        abort(make_response({"message": f"missing required value: {e}"}, 400))

@bp.get("")
def get_characters():
    character_query = db.select(Character)

    characters = db.session.scalars(character_query)
    response = []

    for character in characters:
        response.append(
            {
                "id" : character.id,
                "name" : character.name,
                "personality" : character.personality,
                "occupation" : character.occupation,
                "age" : character.age
            }
        )

    return response

@bp.get("/<char_id>/greetings")
def get_greetings(char_id):
    pass

@bp.post("/<char_id>/generate")
def add_greetings(char_id):
    character_obj = validate_model(Character, char_id)
    greetings = generate_greetings(character_obj)

    if character_obj.greetings:
        return{"message": f"Greetings already generated for {character_obj.name}"}, 201
    
    new_greetings = []
    for greeting in greetings:
        new_greeting = Greeting(
            greeting_text = greeting.strip("\""),
            character = character_obj
        )
        new_greetings.append(new_greeting)
    
    db.session.add_all(new_greetings)
    db.session.commit()

    return {"message": f"Greetings successfully added to {character_obj.name}"}

def generate_greetings(character):
    # model = genai.GenerativeModel("gemini-1.5-flash")

    input_message = f"I am writing a fantasy RPG video game. I have an npc named {character.name} who is {character.age} years old. They are a {character.occupation} who has a {character.personality} personality. Please generate a Python style list of 10 stock phrases they might use when the main character talks to them. Please return just the list without a variable name and square brackets. Please separate items in the list with an endline character"
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=input_message
    )
    response_split = response.text.split("\n")
    return response_split[:-1]
def validate_model(cls,id):
    try:
        id = int(id)
    except:
        response = {"message": f"{cls.__name__} {id} invalid"}
        abort(make_response(response , 400))

    query = db.select(cls).where(cls.id == id)
    model = db.session.scalar(query)
    if model:
        return model

    response = {"message": f"{cls.__name__} {id} not found"}
    abort(make_response(response, 404))