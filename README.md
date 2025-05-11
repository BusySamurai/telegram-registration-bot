# Telegram Registration Bot with Emoji CAPTCHA

A simple Telegram bot template that handles user registration with an emoji-based CAPTCHA system and stores user data in an SQLite database.

## Features

- Private chat registration
- Inline button CAPTCHA (emoji-based verification)
- User data storage (`id`, `username`, `registration date`, `blocked` status)
- CAPTCHA retry limit (3 attempts)
- Admin-only user list access
- Clean structure in a single file

## Tech Stack

- Python 3
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
- SQLite3

## Setup

1. Install dependencies:
   ```bash
   pip install pyTelegramBotAPI
   ```

2. Replace `'YOUR_TOKEN_HERE'` with your Telegram bot token.

3. (Optional) Add your Telegram user ID(s) to the `admins_id` list to access `/list` command.

4. Run the bot:
   ```bash
   python main.py
   ```

## Usage

- `/start`: Begin the CAPTCHA verification process.
- `/list`: Admin command to view all registered users.

## License

This project is open source and available under the MIT License.
