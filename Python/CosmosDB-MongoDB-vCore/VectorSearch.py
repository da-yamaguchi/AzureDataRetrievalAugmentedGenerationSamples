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

query = "What are some NoSQL databases in Azure?"#"What are the services for running ML models?"
results = vector_search(query)
for result in results: 
#     print(result)
    print(f"Similarity Score: {result['similarityScore']}")  
    print(f"Title: {result['document']['title']}")  
    print(f"Content: {result['document']['content']}")  
    print(f"Category: {result['document']['category']}\n")  
