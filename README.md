# telegram-uploader
# Telegram Upload Bot – Mega / MediaFire / Terabox

Upload files/folders from **Mega**, **MediaFire**, or **Terabox** directly to your Telegram **Saved Messages** using a userbot.

## Features
- Supports **files** (up to 10 at once) and **entire folders**.
- Auto‑splits files > 1.9 GB.
- Human‑like delays to avoid rate‑limits.
- Session persistence (save `.session` to Google Drive).

## Setup
1. Clone this repo.
2. Install dependencies:  
   `pip install -r requirements.txt`
3. Run:  
   `python main.py`
4. Follow the on‑screen prompts.

## Running on Google Colab
- Mount Google Drive to save your session:  
  Uncomment the `drive.mount` lines in `main.py` and set `SESSION_PATH`.
- Then run `!python main.py`.

## Notes
- **Mega**: Requires `megatools` (auto‑installed on Ubuntu/Colab).
- **MediaFire**: Uses `mediafire` library.
- **Terabox**: Uses `terabox-dl` (auto‑installed).
- You need a **Telegram API ID and Hash** from [my.telegram.org](https://my.telegram.org/apps).

## This code is not ready to use now, please don't use it.
we're working on it with a book bastic logic