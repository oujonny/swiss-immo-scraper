from app.bot import main as telegram_bot
from app.config import Config

def main(config: Config):
    """Start TelegramBot"""
    # Initialize & start the Telegram Bot
    token = config.telegram_bot_token
    telegram_bot.start(token)

if __name__ == "__main__":
    # Load the ENV Variables into a config instance
    config = Config()

    main(config)