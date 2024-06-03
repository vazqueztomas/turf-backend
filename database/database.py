from motor.motor_asyncio import AsyncIOMotorClient


class DatabaseConnection:
    def __init__(self, uri, database_name):
        self.client = AsyncIOMotorClient(uri)
        self.database_name = self.client[database_name]

    def get_collection(self, collection_name):
        return self.database_name[collection_name]


db_uri = 'mongodb+srv://vazquezt2018:turf1234@cluster0.mmlsepe.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
db_name = 'turf'

database = DatabaseConnection(db_uri, db_name)
