import os
import random
import re
import time
import requests
from bs4 import BeautifulSoup
from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BLOG_ID = os.getenv("BLOGGER_BLOG_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
AFFILIATE_ID = os.getenv("BDSTALL_AFFILIATE_ID")

CLIENT_ID = os.getenv("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("BLOGGER_REFRESH_TOKEN")

def get_bdstall_product():
    domain = "bdstall.com"
    base_site = "https://" + domain
    url = base_site + "/"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/details/' in href:
            if not href.startswith('http'):
                href = base_site + href
            products.append(href)
    
    if not products:
        raise Exception("BDStall ওয়েবসাইট থেকে কোনো প্রোডাক্ট পাওয়া যায়নি।")
        
    selected_url = random.choice(list(set(products)))
    
    prod_resp = requests.get(selected_url, headers=headers)
    prod_soup = BeautifulSoup(prod_resp.text, 'html.parser')
    
    title = prod_soup.find('h1').text.strip() if prod_soup.find('h1') else "উন্নত মানের পণ্য"
    affiliate_url = f"{selected_url}?ref={AFFILIATE_ID}"
    
    # প্রোডাক্ট থেকে ছবি বের করা
    image_url = None
    img_tag = prod_soup.find('img', {'id': 'bigimg'}) or prod_soup.find('img', {'class': 'product-image'})
    
    if not img_tag:
        for img in prod_soup.find_all('img'):
            src = img.get('src', '')
            if any(k in src for k in ['productshare', 'product', 'big', 'details', 'images']):
                img_tag = img
                break
                
    if img_tag and img_tag.get('src'):
        image_url = img_tag['src']
        if not image_url.startswith('http'):
            image_url = base_site + image_url
            
    return title, affiliate_url, image_url

def generate_with_groq(prompt):
    if not GROQ_KEY:
        raise Exception("GROQ_API_KEY গিটহাবের Actions environment-এ পাস করা হয়নি! YAML ফাইল চেক করুন।")
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    # বর্তমান Groq এর সচল ও অনুমোদিত মডেলগুলোর তালিকা
    groq_models = [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-20b"
    ]
    
    for model in groq_models:
        print(f"Trying Groq model: {model}...")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a professional product reviewer and tech blogger who writes comprehensive, engaging articles in Bengali using clean HTML formatting without markdown backticks."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.6
        }
        
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"Successfully generated using Groq model: {model}")
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Model {model} failed: {response.text}")
            
    raise Exception("Groq-এর কোনো মডেল দিয়েই কন্টেন্ট তৈরি করা যায়নি।")

def generate_content_with_fallback(title, aff_url):
    prompt = f"""
    তুমি একজন পেশাদার প্রোডাক্ট রিভিউ লেখক। নিচে দেওয়া প্রোডাক্টটির জন্য একটি অত্যন্ত আকর্ষণীয় ও এসইও-ফ্রেন্ডলি বাংলা ব্লগ পোস্ট তৈরি করো:
    প্রোডাক্টের নাম: {title}
    
    কন্টেন্টের নির্দেশিকা:
    ১. একটি চমৎকার ও আকর্ষণীয় শিরোনাম (<h2>) দাও।
    ২. প্রোডাক্টটির বিস্তারিত ভূমিকা ও বিবরণ দাও।
    ৩. এর মূল ফিচার ও ব্যবহার করার সুবিধাগুলো আলোচনা করো।
    ৪. কেন এটি কেনা উচিত তার একটি চমৎকার উপসংহার দাও।
    ৫. পোস্টের একদম শেষে বড় এবং স্পষ্ট করে কেনার জন্য একটি লিঙ্ক যুক্ত করো।
    বাটনের জন্য ঠিক এই HTML কোডটি পোস্টের শেষে ব্যবহার করবে:
    <div style="text-align: center; margin: 35px 0;">
      <a href="{aff_url}" target="_blank" style="background-color: #28a745; color: #ffffff; padding: 16px 30px; font-size: 18px; font-weight: bold; text-decoration: none; border-radius: 8px; display: inline-block; box-shadow: 0 4px 10px rgba(0,0,0,0.2); transition: 0.3s;">
        🛒 সেরা দামে {title} কিনতে এখানে ক্লিক করুন
      </a>
    </div>
    
    কেনার লিঙ্ক: {aff_url}
    
    বিশেষ নিয়ম:
    - শুধুমাত্র সরাসরি বিশুদ্ধ HTML ট্যাগ (<p>, <h2>, <ul>, <li>, <a>) ব্যবহার করে আউটপুট দাও।
    - কোনো সূচনা বা সমাপ্তিমূলক কথা (যেমন: "এখানে এইচটিএমএল কোড দেওয়া হলো") লিখবে না।
    - মার্কডাউন কোড ব্লক (```html বা ```) একদম ব্যবহার করবে না।
    """
    
    # ১. প্রথমে আপডেট জেমিনাই মডেল দিয়ে চেষ্টা করবে
    if GEMINI_KEY:
        try:
            client = genai.Client(api_key=GEMINI_KEY.strip())
            print("Attempting generation with Gemini (gemini-3.6-flash)...")
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            if response.text:
                return response.text
        except Exception as e:
            print(f"Gemini failed: {e}. Switching to Groq Cloud...")
            
    # ২. Gemini ব্যর্থ হলে Groq ব্যবহার করবে
    print("Generating content using Groq Cloud...")
    return generate_with_groq(prompt)

def clean_html_content(raw_content, image_url, title):
    img_html = f'<div style="text-align: center; margin-bottom: 25px;"><img src="{image_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);"/></div>' if image_url else ''
    
    cleaned = raw_content
    if '<' in cleaned:
        cleaned = cleaned[cleaned.find('<'):]
        
    cleaned = re.sub(r'```html\s*', '', cleaned)
    cleaned = re.sub(r'```\s*', '', cleaned).strip()
    
    return f"{img_html}\n{cleaned}"

def post_to_blogger(title, content):
    if not BLOG_ID or not REFRESH_TOKEN or not CLIENT_ID or not CLIENT_SECRET:
        raise Exception("একটি বা একাধিক সিক্রেট মিসিং রয়েছে! GitHub Secrets চেক করুন।")

    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN.strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID.strip(),
        client_secret=CLIENT_SECRET.strip()
    )
    
    blogger = build('blogger', 'v3', credentials=creds)
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    posts = blogger.posts()
    result = posts.insert(blogId=BLOG_ID.strip(), body=body).execute()
    print(f"Post successful! URL: {result.get('url')}")

if __name__ == "__main__":
    try:
        title, aff_url, image_url = get_bdstall_product()
        raw_content = generate_content_with_fallback(title, aff_url)
        final_content = clean_html_content(raw_content, image_url, title)
        post_to_blogger(title, final_content)
    except Exception as e:
        print(f"Error occurred: {e}")
