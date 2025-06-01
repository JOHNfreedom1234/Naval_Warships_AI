> ⚠️ **Disclaimer**  
> This app is dedicated to World War 2 Naval Battles and warships only. At the moment, it only provides textual information from Wikipedia, but future features include mapping integration, warship comparisons, detailed information and more.

> 👥 **Group Members:**  
> - Rei Duhina - Leader
> - Joshua Calibjo - Coder/Presenter
> - Prince Malatuba - Coder
> - Marc Escueta - Documentation
> - John Albert Claveria - Documentation

# WW2 Warships & Battles AI Agent

This Flask app uses Huggingface Transformers, web scraping, and Wikimedia/Wikidata APIs to answer questions about World War 2 warships and battles. Each answer includes a citation from Wikipedia, Navweaps, or Naval-History.net, and can provide tables/images from Wikimedia/Wikidata.

## Features
- AI-powered Q&A (Huggingface Transformers)
- Data collection from Wikipedia, Navweaps, Naval-History.net
- Citations for every answer
- Tables and images via Wikimedia/Wikidata APIs

## Setup
1. Ensure Python 3.13+ is installed.
2. (Recommended) Use a virtual environment.
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the app:
   ```powershell
   flask run
   ```

## Project Structure
- `app.py` — Main Flask app
- `requirements.txt` — Python dependencies
- `.github/copilot-instructions.md` — Copilot custom instructions

## Notes
- Replace any placeholder API keys with your own if needed.
