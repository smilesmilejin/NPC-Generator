from flask import Blueprint, request, abort, make_response
from ..db import db
from ..models.character import Character
from ..models.greeting import Greeting
from sqlalchemy import func, union, except_

# import the google-generativeai package and configure the Gemini API environment using the code below:
import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

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
    character = validate_model(Character, char_id)
    
    if not character.greetings:
        return {"message": f"No greetings found for {character.name} "}, 201
    
    print(character.name)
    response = {"Character Name" : character.name,
                "Greetings" : []}
    for greeting in character.greetings:
        response["Greetings"].append({
            "greeting" : greeting.greeting_text
        })
    
    return response

@bp.post("/<char_id>/generate")
def add_greetings(char_id):
    character_obj = validate_model(Character, char_id)
    greetings = generate_greetings(character_obj)

    if character_obj.greetings:
        return {"message": f"Greetings already generated for {character_obj.name} "}, 201
    
    new_greetings = []

    for greeting in greetings:
        new_greeting = Greeting(
            greeting_text = greeting.strip("\""), #Removes quotes from each string
            character = character_obj
        )
        new_greetings.append(new_greeting)
    
    db.session.add_all(new_greetings)
    db.session.commit()

    return {"message": f"Greetings successfully added to {character_obj.name}"}, 201


def generate_greetings(character):
    # The first thing we will do is use the aliased google.generativeai import: genai
    # constructor for the GenerativeModel class 
    # and pass it the name of the model as an string argument "gemini-1.5-flash".
    model = genai.GenerativeModel("gemini-1.5-flash")
    # Then we'll use the Character's attributes to construct a prompt for our request body.
    input_message = f"I am writing a fantasy RPG video game. I have an npc named {character.name} who is {character.age} years old. They are a {character.occupation} who has a {character.personality} personality. Please generate a Python style list of 10 stock phrases they might use when the main character talks to them. Please return just the list without a variable name and square brackets."
    # call the generate_content method on the model variable, passing our input_message as a parameter.
    response = model.generate_content(input_message)
    # If we access response.text to get to the string itself, we can split it by the newline character to get a list of responses:
    #Splits response into a list of stock phrases, ends up with an empty string at index -1
    response_split = response.text.split("\n")
    # Since the response we're given ends with a newline character, 
    # this split operation will leave us with an empty string at the end of our list. Since we don't want to save an empty string to our NPC sayings, 
    # we can slice off the last value before we return our list. 
    #Returns the stock phrases list, just without the empty string at the end
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