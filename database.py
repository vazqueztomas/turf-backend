from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb+srv://vazquezt2018:turf1234@cluster0.mmlsepe.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.turf
users_collection = db.users
