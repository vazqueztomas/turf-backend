import os

from motor.motor_asyncio import AsyncIOMotorClient


class DatabaseConnection:
    def __init__(self, uri, database_name):
        self.client = AsyncIOMotorClient(uri)
        self.database_name = self.client[database_name]

    def get_collection(self, collection_name):
        return self.database_name[collection_name]


db_uri = os.environ.get("DB_URI")
db_name = "turf"

database = DatabaseConnection(db_uri, db_name)
