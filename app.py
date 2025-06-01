import os
from flask import Flask, request, jsonify, render_template, session
from flask import redirect, url_for
from flask_session import Session
from transformers import pipeline
import requests
from bs4 import BeautifulSoup
import wikipediaapi
import wikipedia
import time
import logging
import difflib
import re

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Load Huggingface model (Gemma or similar)
gemma_pipeline = pipeline('text-generation', model='google/gemma-2b-it', device_map='cpu')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Helper: Search Wikipedia and return summary, url

def extract_main_subject(query):
    # Simple NLP: extract main noun phrase or subject
    # Lowercase and remove punctuation
    q = re.sub(r'[?!.]', '', query.lower())
    # Common question patterns
    patterns = [
        r'what can you tell me about (.+)',
        r'tell me about (.+)',
        r'give me information about (.+)',
        r'what is (.+)',
        r'who is (.+)',
        r'where is (.+)',
        r'when was (.+)',
        r'info about (.+)',
        r'details about (.+)',
        r'can you tell me about (.+)',  # new pattern added
        r'(.+)'  # fallback: use the whole query
    ]
    for pat in patterns:
        m = re.match(pat, q)
        if m:
            subject = m.group(1).strip()
            # Remove leading articles
            subject = re.sub(r'^(the|a|an) ', '', subject)
            return subject
    return query

def get_wikipedia_summary(query):
    user_agent = 'WW2-AI-Agent/1.0 (contact: percievalwritings@gmail.com)'
    main_subject = extract_main_subject(query)
    wiki = wikipediaapi.Wikipedia('en', headers={'User-Agent': user_agent})
    page = wiki.page(main_subject)
    time.sleep(1)
    if page.exists():
        logger.info(f"Wikipedia page found: {page.fullurl}")
        return page.summary, page.fullurl, None
    logger.info(f"Wikipedia exact page not found for '{main_subject}', trying fuzzy search.")
    try:
        wikipedia.set_lang('en')
        wikipedia.set_user_agent(user_agent)
        search_results = wikipedia.search(main_subject)
        if search_results:
            best_title = search_results[0]
            similarity = difflib.SequenceMatcher(None, main_subject.lower(), best_title.lower()).ratio()
            logger.info(f"Wikipedia fuzzy match found: {best_title} (similarity: {similarity:.2f})")
            if similarity > 0.7:
                page_content = wikipedia.page(best_title, auto_suggest=False)
                if hasattr(page_content, 'disambiguation') or 'may refer to:' in page_content.content:
                    logger.info(f"Disambiguation page detected for: {best_title}")
                    # Return a list of options instead of summary
                    options = []
                    for option in page_content.links:
                        option_similarity = difflib.SequenceMatcher(None, main_subject.lower(), option.lower()).ratio()
                        if option_similarity > 0.5:
                            page_url = f"https://en.wikipedia.org/wiki/{option.replace(' ', '_')}"
                            options.append({'title': option, 'url': page_url})
                    if options:
                        return None, None, options
                    logger.info("No suitable non-disambiguation option found.")
                    return None, None, None
                else:
                    summary = wikipedia.summary(best_title, sentences=3, auto_suggest=False)
                    page_url = f"https://en.wikipedia.org/wiki/{best_title.replace(' ', '_')}"
                    return summary, page_url, None
            else:
                logger.info(f"Fuzzy match '{best_title}' rejected due to low similarity ({similarity:.2f})")
        else:
            logger.info("Wikipedia fuzzy search found no results.")
    except Exception as e:
        logger.error(f"Wikipedia fuzzy search error: {e}")
    logger.info("Wikipedia page not found after fuzzy search.")
    return None, None, None

# Helper: Scrape Navweaps or Naval-History.net for a relevant citation

def get_external_citation(query):
    # Polite headers and delay
    headers = {
        'User-Agent': 'WW2-AI-Agent/1.0 (contact: percievalwritings@gmail.com)'
    }
    sources = [
        f'https://en.wikipedia.org/wiki/{query.replace(" ", "_")}',
        f'https://www.navweaps.com/Weapons/index.html',
        f'https://www.naval-history.net/WW2CampaignsOtherNavies.htm'
    ]
    for url in sources:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                time.sleep(1)  # 1 second polite delay
                return url
        except Exception:
            continue
        time.sleep(1)  # Polite delay between requests
    return None

def get_wikipedia_images(page_title):
    """Extracts image URLs from a Wikipedia page using the wikipedia library."""
    images = []
    try:
        page = wikipedia.page(page_title, auto_suggest=False)
        for image in page.images:
            if image.endswith(('.jpg', '.jpeg', '.png', '.gif')):  # Filter for common image formats
                images.append(image)
    except Exception as e:
        logger.error(f"Error extracting images: {e}")
    return images

@app.route('/')
def index():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('index.html')

@app.route('/api/chat_history', methods=['GET'])
def get_chat_history():
    return jsonify(session.get('chat_history', []))

@app.route('/api/ask', methods=['POST'])
def ask_ai():
    data = request.json
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'No question provided.'}), 400
    summary, wiki_url, disambig_options = get_wikipedia_summary(question)
    if summary:
        main_subject = extract_main_subject(question)
        images = get_wikipedia_images(main_subject)
        prompt = (
            f"You are an expert on World War 2 naval history. "
            f"Using the following factual information from Wikipedia, provide a detailed and conversational answer. "
            f"Structure the response in a ChatGPT/Gemini style with clear sections, bullet points for key features, and a professional tone. "
            f"Ensure the response is visually appealing and ends with a citation link to the Wikipedia page. "
            f"Do not make up information or add anything beyond the provided context. "
            f"If the answer is not in the context, say 'I don't know based on the provided information.'\n"
            f"Context: {summary}\n"
            f"Question: {question}\nAnswer: "
        )
        response = gemma_pipeline(prompt, max_new_tokens=768, do_sample=False)[0]['generated_text']
        answer = response.split('Answer:')[-1].strip()
        citation = wiki_url
        return jsonify({'answer': answer, 'citation': citation, 'images': images})
    elif disambig_options:
        options_text = 'I found multiple possible entries for your question. Please specify one of the following:\n' + '\n'.join([f"- <a href='{opt['url']}' target='_blank'>{opt['title']}</a>" for opt in disambig_options])
        return jsonify({'answer': options_text, 'citation': None, 'disambiguation': True, 'options': disambig_options})
    else:
        return jsonify({'answer': "I'm sorry, I don't know the answer to that.", 'citation': None, 'images': []})
    # After answer/citation are set:
    chat_entry = {'role': 'user', 'text': question}
    ai_entry = {'role': 'ai', 'text': answer, 'citation': citation}
    chat_history = session.get('chat_history', [])
    chat_history.append(chat_entry)
    chat_history.append(ai_entry)
    session['chat_history'] = chat_history
    session.modified = True
    return jsonify({'answer': answer, 'citation': citation})

@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    """Endpoint to clear the chat history."""
    session.pop('chat_history', None)
    return jsonify({'message': 'Chat history cleared successfully.'}), 200

if __name__ == '__main__':
    app.run(debug=True)
