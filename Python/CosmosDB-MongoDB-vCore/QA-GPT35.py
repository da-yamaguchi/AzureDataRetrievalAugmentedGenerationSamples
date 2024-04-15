import json
import datetime
import time
import urllib 

from azure.core.exceptions import AzureError
from azure.core.credentials import AzureKeyCredential
import pymongo

from openai import AzureOpenAI
from dotenv import load_dotenv

from dotenv import dotenv_values

# specify the name of the .env file name 
env_name = "example.env" # following example.env template change to your own .env file name
config = dotenv_values(env_name)

COSMOS_MONGO_USER = config['cosmos_db_mongo_user']
COSMOS_MONGO_PWD = config['cosmos_db_mongo_pwd']
COSMOS_MONGO_SERVER = config['cosmos_db_mongo_server']

AOAI_client = AzureOpenAI(api_key=config['openai_api_key'], azure_endpoint=config['openai_api_endpoint'], api_version=config['openai_api_version'],)

def generate_embeddings(text):
    '''
    Generate embeddings from string of text.
    This will be used to vectorize data and user input for interactions with Azure OpenAI.
    '''
    response = AOAI_client.embeddings.create(input=text, model=config['openai_embeddings_deployment'])
    embeddings =response.model_dump()
    time.sleep(0.5) 
    return embeddings['data'][0]['embedding']

##接続のセットアップ
mongo_conn = "mongodb+srv://"+urllib.parse.quote(COSMOS_MONGO_USER)+":"+urllib.parse.quote(COSMOS_MONGO_PWD)+"@"+COSMOS_MONGO_SERVER+"?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
mongo_client = pymongo.MongoClient(mongo_conn)

##データベースとコレクションのセットアップ
db = mongo_client['ExampleDB']

# Create collection if it doesn't exist
COLLECTION_NAME = "ExampleCollection"
collection = db[COLLECTION_NAME]

# Simple function to assist with vector search
def vector_search(query, num_results=5):
    query_embedding = generate_embeddings(query)
    embeddings_list = []
    pipeline = [
        {
            '$search': {
                "cosmosSearch": {
                    "vector": query_embedding,
                    "path": "contentVector",
                    "k": num_results#, #, "efsearch": 40 # optional for HNSW only 
                    #"filter": {"title": {"$ne": "Azure Cosmos DB"}}
                },
                "returnStoredSource": True }},
        {'$project': { 'similarityScore': { '$meta': 'searchScore' }, 'document' : '$$ROOT' } }
    ]
    results = collection.aggregate(pipeline)
    return results

#This function helps to ground the model with prompts and system instructions.

def generate_completion(vector_search_results, user_prompt):
    system_prompt = '''
    You are an intelligent assistant for Microsoft Azure services.
    You are designed to provide helpful answers to user questions about Azure services given the information about to be provided.
        - Only answer questions related to the information provided below, provide at least 3 clear suggestions in a list format.
        - Write two lines of whitespace between each answer in the list.
        - If you're unsure of an answer, you can say ""I don't know"" or ""I'm not sure"" and recommend users search themselves."
        - Only provide answers that have products that are part of Microsoft Azure and part of these following prompts.
    '''

    messages=[{"role": "system", "content": system_prompt}]
    for item in vector_search_results:
        messages.append({"role": "system", "content": item['document']['content']})
    messages.append({"role": "user", "content": user_prompt})
    response = AOAI_client.chat.completions.create(model=config['openai_completions_deployment'], messages=messages,temperature=0)
    
    return response.dict()

# Create a loop of user input and model output. You can now perform Q&A over the sample data!

user_input = ""
print("*** Please ask your model questions about Azure services. Type 'end' to end the session.\n")
user_input = input("User prompt: ")
while user_input.lower() != "end":
    search_results = vector_search(user_input)
    completions_results = generate_completion(search_results, user_input)
    print("\n")
    print(completions_results['choices'][0]['message']['content'])
    user_input = input("User prompt: ")