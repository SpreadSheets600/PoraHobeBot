# PoraHobeBot

PoraHobeBot is a Python-based bot and web server for managing and sharing notes, lecture materials, and playlists. It features a Discord bot, a web interface for uploading and viewing notes, and a simple database backend.

## Features

- Discord bot for managing notes and links
- Web server for uploading and viewing notes
- SQLite database for storing notes and metadata
- Template-based HTML rendering
- File uploads and downloads

## Project Structure

```
main.py                  # Entry point for the application
pyproject.toml           # Project dependencies and metadata
cogs/                    # Discord bot cogs (commands/extensions)
    notes.py
templates/               # HTML templates for the web server
    _subject_list.html
    notes_list.html
    upload.html
uploads/                 # Uploaded files (PDFs, Excel, etc.)
utils/                   # Utility modules (bot, database, server)
    bot.py
    database.py
    server.py
notes.db                 # SQLite database file
```

## Getting Started

### Prerequisites

- Python 3.11+
- pip

### Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/yourusername/PoraHobeBot.git
   cd PoraHobeBot
   ```

2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

   Or, if using pyproject.toml:

   ```sh
   pip install .
   ```

### Usage

#### Run the Bot and Server

```sh
python main.py
```

#### Upload Notes

- Access the web interface (URL will be shown in the terminal, typically `http://localhost:8000`)
- Use the upload form to add new notes or files

#### Discord Bot

- Add the bot to your server using the provided invite link
- Use commands as described in the bot's help menu

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

MIT

---

Let me know if you want to customize any section or add more details!
