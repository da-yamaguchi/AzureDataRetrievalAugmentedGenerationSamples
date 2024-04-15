
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

# Load text-sample_w_embeddings.json which has embeddings pre-computed
data_file = open(file="../../DataSet/AzureServices/text-sample_w_embeddings.json", mode="r") 

# OR Load text-sample.json data file. Embeddings will need to be generated using the function below.
# data_file = open(file="../../DataSet/AzureServices/text-sample.json", mode="r")

data = json.load(data_file)
data_file.close()

# Take a peek at one data item
# print(json.dumps(data[0], indent=2))

def generate_embeddings(text):
    '''
    Generate embeddings from string of text.
    This will be used to vectorize data and user input for interactions with Azure OpenAI.
    '''
    response = AOAI_client.embeddings.create(input=text, model=config['openai_embeddings_deployment'])
    embeddings =response.model_dump()
    time.sleep(0.5) 
    return embeddings['data'][0]['embedding']

##読み込んだドキュメントをembeddingする処理 ここから##
# # Generate embeddings for title and content fields
# n = 0
# for item in data:
#     n+=1
#     title = item['title']
#     content = item['content']
#     title_embeddings = generate_embeddings(title)
#     content_embeddings = generate_embeddings(content)
#     item['titleVector'] = title_embeddings
#     item['contentVector'] = content_embeddings
#     item['@search.action'] = 'upload'
#     print("Creating embeddings for item:", n, "/" ,len(data), end='\r')
# # Save embeddings to sample_text_w_embeddings.json file
# with open("../../DataSet/AzureServices/text-sample_w_embeddings.json", "w") as f:
#     json.dump(data, f)

# # Take a peek at one data item with embeddings created
# print(json.dumps(data[0], indent=2))
##読み込んだドキュメントをembeddingする処理 ここまで##

# Connect and setup Cosmos DB for MongoDB vCore

##接続のセットアップ
mongo_conn = "mongodb+srv://"+urllib.parse.quote(COSMOS_MONGO_USER)+":"+urllib.parse.quote(COSMOS_MONGO_PWD)+"@"+COSMOS_MONGO_SERVER+"?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
mongo_client = pymongo.MongoClient(mongo_conn)

##データベースとコレクションのセットアップ
# create a database called TutorialDB
print("mongo_client")
print(mongo_client)
db = mongo_client['ExampleDB']
print("db")
print(db)

# Create collection if it doesn't exist
COLLECTION_NAME = "ExampleCollection"

collection = db[COLLECTION_NAME]

if COLLECTION_NAME not in db.list_collection_names():
    # Creates a unsharded collection that uses the DBs shared throughput
    db.create_collection(COLLECTION_NAME)
    print("Created collection '{}'.\n".format(COLLECTION_NAME))
else:
    print("Using collection: '{}'.\n".format(COLLECTION_NAME))

# Use only if re-reunning code and want to reset db and collection
collection.drop_indexes()
mongo_client.drop_database("ExampleDB")

#ベクトルインデックスの作成
##IVFインデックス(無料ティア)
db.command({
  'createIndexes': 'ExampleCollection',
  'indexes': [
    {
      'name': 'VectorSearchIndex',
      'key': {
        "contentVector": "cosmosSearch"
      },
      'cosmosSearchOptions': {
        'kind': 'vector-ivf',
        'numLists': 1,
        'similarity': 'COS',
        'dimensions': 1536
      }
    }
  ]
})

#コレクションにデータをアップロードする
collection.insert_many(data)


