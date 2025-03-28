import os
import random
import uuid
import asyncio
from pyrogram import Client, filters
from pymongo import MongoClient
from datetime import datetime, timedelta

# Environment variables
API_ID = int(os.getenv('API_ID', '29475796'))
API_HASH = os.getenv('API_HASH', '3cc507f5d94835d46df597cb61ed55e3')
BOT_TOKEN = os.getenv('BOT_TOKEN', '7941536726:AAElMbx1pSzm19TXYH4fiMUEA9Zy25M7lBQ')

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://dextin:zaxscd123@leakedjalwa.9yauwbt.mongodb.net/?retryWrites=true&w=majority&appName=LeakedJalwa')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'RandomTest')

ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '7758708579').split(',')))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'trashxrd')
DB_CHANNEL_ID = int(os.getenv('DB_CHANNEL_ID', '-1002439416325'))

# Initialize bot client
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize MongoDB client
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB_NAME]
media_collection = db['media']
users_collection = db['users']
points_collection = db['points']
premium_collection = db['premium']
settings_collection = db['settings']

# Default settings
default_settings = {
    'auto_delete': False,
    'protect_content': False
}
settings = settings_collection.find_one({'_id': 'settings'}) or default_settings

# Command to start the bot
@app.on_message(filters.command('start') & filters.private)
async def start(client, message):
    user_id = message.from_user.id
    if not points_collection.find_one({'user_id': user_id}):
        points_collection.insert_one({'user_id': user_id, 'points': 20})

    # Check for referral
    if len(message.command) > 1:
        referrer_id = int(message.command[1])
        if referrer_id != user_id and not points_collection.find_one({'user_id': user_id, 'referred_by': {'$exists': True}}):
            points_collection.update_one({'user_id': referrer_id}, {'$inc': {'points': 10}}, upsert=True)
            points_collection.update_one({'user_id': user_id}, {'$set': {'referred_by': referrer_id}}, upsert=True)
            referrer_user = await client.get_users(referrer_id)
            await client.send_message(referrer_id, f"{message.from_user.username} has used your referral link. You have earned 10 points.")
    
    start_message = """
<b>Welcome to our Amazing Bot!</b> 🎉

<i>Here's what you can do:</i>
<u>Features:</u>
- <code>Earn points</code> by referring friends! 💰
- Get <b>random videos</b> and <b>photos</b> using your points! 📹📷
- Check your <u>points</u> and <u>referral link</u> anytime! 📈
- Contact <a href="https://t.me/trashxrd">Admin</a> to buy more points! 🛒

<b>Commands:</b>
- <code>/start</code> - Start the bot
- <code>/help</code> - Show help message
- <code>/video</code> - Get a random video (Costs 1 point)
- <code>/photo</code> - Get a random photo
- <code>/refferal</code> - Get referral link
- <code>/points</code> - Check your points
- <code>/buy</code> - Contact admin to buy coins
- <code>/pre_list</code> - Show premium plans

<spoiler>Enjoy all the features and have fun!</spoiler> 🎊
    """
    
    await message.reply(start_message)

# Help command
@app.on_message(filters.command('help') & filters.private)
async def help_command(client, message):
    help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/video - Get a random video (Costs 1 point)
/photo - Get a random photo
/refferal - Get referral link
/points - Check your points
/buy - Contact admin to buy coins
/pre <user_id> <points> - Add points to a user (admin only)
/pre_list - Show premium plans
    """
    await message.reply(help_text)

# Command to send a random video
@app.on_message(filters.command('video') & filters.private)
async def send_random_video(client, message):
    user_id = message.from_user.id
    user = points_collection.find_one({'user_id': user_id})
    points = user['points'] if user else 0

    if points <= 0:
        await message.reply('You do not have enough points to get a video. Use /buy to purchase more points.')
        return

    count = media_collection.count_documents({'type': 'video'})
    if count == 0:
        await message.reply('No videos available.')
        return
    
    random_index = random.randint(0, count - 1)
    video = media_collection.find({'type': 'video'})[random_index]
    sent_message = await client.send_video(
        message.chat.id, 
        video['file_id']
    )

    points_collection.update_one({'user_id': user_id}, {'$inc': {'points': -1}})

    if settings['auto_delete']:
        await schedule_auto_delete(sent_message)

# Command to send a random photo
@app.on_message(filters.command('photo') & filters.private)
async def send_random_photo(client, message):
    count = media_collection.count_documents({'type': 'photo'})
    if count == 0:
        await message.reply('No photos available.')
        return
    
    random_index = random.randint(0, count - 1)
    photo = media_collection.find({'type': 'photo'})[random_index]
    sent_message = await client.send_photo(
        message.chat.id, 
        photo['file_id']
    )

    if settings['auto_delete']:
        await schedule_auto_delete(sent_message)

# Command to get referral link
@app.on_message(filters.command('refferal') & filters.private)
async def referral(client, message):
    user_id = message.from_user.id
    bot_info = await client.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
    await message.reply(f"Share this link to refer others: {referral_link}")

# Command to check points
@app.on_message(filters.command('points') & filters.private)
async def check_points(client, message):
    user_id = message.from_user.id
    user = points_collection.find_one({'user_id': user_id})
    points = user['points'] if user else 0
    await message.reply(f"You have {points} points.")

# Command to buy points
@app.on_message(filters.command('buy') & filters.private)
async def buy_points(client, message):
    await message.reply(f"Contact @{ADMIN_USERNAME} to buy coins.")

# Command to add points (admin only)
@app.on_message(filters.command('pre') & filters.private & filters.user(ADMIN_IDS))
async def add_points(client, message):
    try:
        _, user_id, points = message.text.split()
        user_id = int(user_id)
        points = int(points)
        points_collection.update_one({'user_id': user_id}, {'$inc': {'points': points}}, upsert=True)
        await message.reply(f"Added {points} points to user {user_id}.")
    except ValueError:
        await message.reply("Invalid command format. Use /pre <user_id> <points>")

# Command to show premium plans
@app.on_message(filters.command('pre_list') & filters.private)
async def premium_list(client, message):
    premium_plans = """
Premium Plans:
₹30 = 60 Points
₹50 = 120 + 50 Bonus Points
₹100 = 280 + 100 Bonus Points
₹200 = 600 + 200 Bonus Points
₹300 = 1000 + 300 Bonus Points
₹500 = 2000 + 500 Bonus Points
    """
    await message.reply(premium_plans)

# Command to save media (admin only)
@app.on_message((filters.video | filters.photo) & filters.private & filters.user(ADMIN_IDS))
async def save_media(client, message):
    if message.video:
        file_id = message.video.file_id
        media_type = 'video'
    elif message.photo:
        file_id = message.photo.file_id
        media_type = 'photo'
    
    media_collection.insert_one({'uuid': str(uuid.uuid4()), 'file_id': file_id, 'type': media_type})
    await message.reply('Media saved to the database.')

# Token expiry notification
async def notify_token_expiry(user_id):
    await app.send_message(user_id, """
<b>Your premium token has expired!</b>
<i>Please</i> <u><a href="https://your.subscription.link">renew your premium subscription</a></u> <i>to continue enjoying premium benefits!</i> 😊
    """)

async def schedule_auto_delete(message):
    await asyncio.sleep(1200)  # 20 minutes
    await message.delete()

if __name__ == '__main__':
    app.run()
