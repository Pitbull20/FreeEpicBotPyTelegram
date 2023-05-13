import feedparser
import telebot
import sample_config
import logging
import sqlite3

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
free_game_list = []
bot_token = sample_config.BOT_TOKEN

def create_database_connection():
    """
    Створює з'єднання з базою даних
    """
    conn = sqlite3.connect('./database/database.db')
    return conn

# Функція remove_id
def remove_id(chat_id):
    """
    Removes a certain chat ID from the database of subscribed users/chats
    Args:
        chat_id: A chat ID to be removed from the subscription
    """
    conn = create_database_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_data WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def send_message(text):
    """
    Sends a message to each ID in the dictionary, and removes the unreachable ones
    Args:
        text: The text to send (the game link)
    """
    conn = create_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM chat_data")
    chat_ids = cursor.fetchall()
    conn.close()

    bot = telebot.TeleBot(bot_token)
    for chat_id in chat_ids:
        try:
            bot.send_message(chat_id=chat_id[0], text=text)
        except Exception as e:
            logging.warning(f"The following chat ID doesn't exist - {e}")
            remove_id(chat_id[0])

def get_links():
    """
    Parses new games from the rss feed and formats them into a compact-looking message

    Returns:
        A list of ready-to-go messages, each containing a free game link + description
    """
    url = "https://www.indiegamebundles.com/category/free/rss"
    try:
        d = feedparser.parse(url)
        messages = []
        for entry in d.entries:
            free_description = entry.title
            free_link = entry.link
            if free_link not in free_game_list:
                free_game_list.append(free_link)
                messages.append(f"{free_description}\n{free_link}")
        if len(messages) > 0:
            send_message(text="\n\n".join(messages))
        return messages
    except Exception as e:
        send_message(text=f"The site is currently down or unreachable:\t{e}")

if __name__ == '__main__':
    conn = create_database_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS chat_data (chat_name TEXT PRIMARY KEY, chat_id INTEGER)")
    conn.commit()
    conn.close()

    free_right_now = get_links()

    bot = telebot.TeleBot(bot_token)

    @bot.message_handler(commands=['freegame'])
    def free_game(message):
        """
        Sends the current free game via Telegram
        """
        bot.send_message(chat_id=message.chat.id, text=free_right_now)

    @bot.message_handler(commands=['help', 'start'])
    def help_command(message):
        """
        Sends basic information about the bot and explains its use in short via Telegram
        """
        bot.send_message(chat_id=message.chat.id, text=sample_config.HELP_MESSAGE)

    @bot.message_handler(commands=['subscribe'])
    def subscribe(message):
        """
        Adds the chat ID to the database for future reference
        """
        chat_id = message.chat.id
        chat_name = message.chat.username

        conn = create_database_connection()
        cursor = conn.cursor()

        # Перевірка, чи існує запис з поточним chat_name в базі даних
        cursor.execute("SELECT chat_name FROM chat_data WHERE chat_name=?", (chat_name,))
        existing_row = cursor.fetchone()

        if existing_row:
            bot.send_message(chat_id=message.chat.id, text="You are already subscribed!")
        else:
            # Вставка нового запису в базу даних
            cursor.execute("INSERT INTO chat_data (chat_name, chat_id) VALUES (?, ?)", (chat_name, chat_id))
            conn.commit()
            bot.send_message(chat_id=message.chat.id, text="You have successfully subscribed!")

        conn.close()

    @bot.message_handler(commands=['unsubscribe'])
    def unsubscribe(message):
        """
        Removes the chat ID from the database
        """
        chat_id = message.chat.id

        conn = create_database_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT chat_name FROM chat_data WHERE chat_id=?", (chat_id,))
        existing_row = cursor.fetchone()

        if existing_row:
            cursor.execute("DELETE FROM chat_data WHERE chat_id=?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id=message.chat.id, text="You have successfully unsubscribed!")
        else:
            bot.send_message(chat_id=message.chat.id, text="You are not subscribed!")

        conn.close()

    if __name__ == '__main__':
        try:
            print("Bot started")
            bot.polling()
        except Exception as e:
            logging.error(f"An error occurred while polling: {e}")
