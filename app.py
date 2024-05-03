import sys
from flask import Flask, render_template, request
import google.generativeai as genai
import os
import re

import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Check if API key is provided as command-line argument
if len(sys.argv) < 2:
    print("Please provide your API key as a command-line argument.")
    sys.exit(1)

api_key = sys.argv[1]

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')
chat = model.start_chat(history=[])

carousel_count = 0
scholar_results = {}  # Global variable declaration

# FUNCTIONS: Fetching papers
def getScholarDataHelper(search: str, num_pages:int=5)->None:
    global scholar_results  # Declare scholar_results as global
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
        }
        for page in range(num_pages):
            url = f"https://www.google.com/scholar?q={'+'.join(search.split(' '))}&hl=en&start={page * 10}"
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            for el in soup.select(".gs_ri"):
                if '[BOOK]' in el.select(".gs_rt")[0].text:
                    pattern = r'\[\w+\]'
                    clean_text = re.sub(pattern, '', el.select(".gs_rt")[0].text).strip()
                    scholar_results[clean_text] = {
                            "type": "BOOK",
                            "title_link": el.select(".gs_rt a")[0]["href"],
                            "id": el.select(".gs_rt a")[0]["id"],
                            "displayed_link": el.select(".gs_a")[0].text,
                            "snippet": el.select(".gs_rs")[0].text.replace("\n", ""),
                            "cited_by_count": el.select(".gs_nph+ a")[0].text,
                            "cited_link": "https://scholar.google.com" + el.select(".gs_nph+ a")[0]["href"],
                            "versions_count": el.select("a~ a+ .gs_nph")[0].text,
                            "versions_link": "https://scholar.google.com" + el.select("a~ a+ .gs_nph")[0]["href"] if el.select("a~ a+ .gs_nph")[0].text else ""
                        }
                elif '[HTML]' in el.select(".gs_rt")[0].text:
                    pattern = r'\[\w+\]'
                    clean_text = re.sub(pattern, '', el.select(".gs_rt")[0].text).strip()
                    scholar_results[clean_text] = {
                            "type": "HTML",
                            "title_link": el.select(".gs_rt a")[0]["href"],
                            "id": el.select(".gs_rt a")[0]["id"],
                            "displayed_link": el.select(".gs_a")[0].text,
                            "snippet": el.select(".gs_rs")[0].text.replace("\n", ""),
                            "cited_by_count": el.select(".gs_nph+ a")[0].text,
                            "cited_link": "https://scholar.google.com" + el.select(".gs_nph+ a")[0]["href"],
                            "versions_count": el.select("a~ a+ .gs_nph")[0].text,
                            "versions_link": "https://scholar.google.com" + el.select("a~ a+ .gs_nph")[0]["href"] if el.select("a~ a+ .gs_nph")[0].text else ""
                        }
                else:
                    scholar_results[el.select(".gs_rt")[0].text] = {
                            "title_link": el.select(".gs_rt a")[0]["href"],
                            "id": el.select(".gs_rt a")[0]["id"],
                            "displayed_link": el.select(".gs_a")[0].text,
                            "snippet": el.select(".gs_rs")[0].text.replace("\n", ""),
                            "cited_by_count": el.select(".gs_nph+ a")[0].text,
                            "cited_link": "https://scholar.google.com" + el.select(".gs_nph+ a")[0]["href"],
                            "versions_count": el.select("a~ a+ .gs_nph")[0].text,
                            "versions_link": "https://scholar.google.com" + el.select("a~ a+ .gs_nph")[0]["href"] if el.select("a~ a+ .gs_nph")[0].text else ""
                        }
    except Exception as e:
        print(e)

def getScholarData(search: str) -> None:
    print('Inside getScholarData!')
    global carousel_count  # Declare carousel_count as global
    global scholar_results  # Declare scholar_results as global
    scholar_results = {} 
    getScholarDataHelper(search)
    carousel_str = str(scholar_results)
    carousel_count += 1
    return carousel_str

#FUNCTIONS: Returning paper snippet
def paperOverview(paper_name: str)->str:
    return f'<p>{scholar_results[paper_name]}</p>'

def summarize(paper_text:str)->str:
    global summarizer
    message = "Summarize this text: "+paper_text
    return f'<p>{summarizer.send_message(message)}</p>'

# GLOBAL HELPER
research_system = [getScholarData, paperOverview, summarize]
use_sys_inst=False
model_name = 'gemini-1.5-pro-latest' if use_sys_inst else 'gemini-1.0-pro-latest'
BOT_PROMPT = """\You are a research assisting system and you are restricted to talk only about research. Do not talk about anything but assisting with research to the user, ever. 
All of your outputs should be STRICTLY of the form of HTML <p></p> text. Stylize the text with Bootstrap. Use <ol></ol> for lists, <b></b> for bold texts.
Your goal is to do getScholarData after understanding the term the user wants to search. List the papers found as an ordered list of the paper titles and the paper title links.
If a user asks to learn more about one of the papers that you've listed, your goal is to do paperOverview.
If a user wants to summarize a large body of text, your goal is to do summarize.
If you are unsure about a search term or any input from the user, ask a question to clarify or redirect.
"""
# Toggle this to switch between Gemini 1.5 with a system instruction, or Gemini 1.0 Pro.
use_sys_inst = False
model_name = 'gemini-1.5-pro-latest' if use_sys_inst else 'gemini-1.0-pro-latest'
if use_sys_inst:
  model = genai.GenerativeModel(
      model_name, tools=research_system, system_instruction=BOT_PROMPT)
  global_helper = model.start_chat(enable_automatic_function_calling=True)

else:
  model = genai.GenerativeModel(model_name, tools=research_system)
  global_helper = model.start_chat(
      history=[
          {'role': 'user', 'parts': [BOT_PROMPT]},
          {'role': 'model', 'parts': ['OK I understand. I will do my best!']}
        ],
      enable_automatic_function_calling=True)

def send_message(message):
  return global_helper.send_message(message)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    user_input = request.form['user_input']
    response = send_message(user_input)
    capitalized_text = response.text
    print(capitalized_text)
    return capitalized_text

if __name__ == '__main__':
    app.run(debug=True)
