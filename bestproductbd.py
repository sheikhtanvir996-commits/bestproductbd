import os
import random
import re
import requests
from bs4 import BeautifulSoup
from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BLOG_ID = os.getenv("BLOGGER_BLOG_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
AFFILIATE_ID = os.getenv("BDSTALL_AFFILIATE_ID")

CLIENT_ID = os.getenv("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("BLOGGER_REFRESH_TOKEN")

def get_bdstall_product():
    # ইউআরএলটি স্ট্রিং হিসেবে একদম নিখুঁত রাখা হয়েছে
    url = "[https://www.bdstall.com/](https://www.bdstall.com/)"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/details/' in href:
            if not href.startswith('http'):
                href = "[https://www.bdstall.com](https://www.bdstall.com)" + href
            products.append(href)
    
    if not products:
        raise Exception("BDStall ওয়েবসাইট থেকে কোনো প্রোডাক্ট পাওয়া যায়নি।")
        
    selected_url = random.choice(list(set(products)))
    
    prod_resp = requests.get(selected_url, headers=headers)
    prod_soup = BeautifulSoup(prod_resp.text, 'html.parser')
    
    title = prod_soup.find('h1').text.strip() if prod_soup.find('h1') else "উন্নত মানের ইলেকট্রনিক পণ্য"
    affiliate_url = f"{selected_url}?ref={AFFILIATE_ID}"
    
    # প্রোডাক্টের ইমেজ ইউআরএল সংগ্রহের লজিক
    image_url = None
    img_tag = prod_soup.find('img', {'id': 'bigimg'}) or prod_soup.find('img', {'class': 'product-image'})
    if not img_tag:
        for img in prod_soup.find_all('img'):
            src = img.get('src', '')
            if 'productshare' in src or 'product' in src or 'big' in src or 'details' in src:
                img_tag = img
                break
                
    if img_tag and img_tag.get('src'):
        image_url = img_tag['src']
        if not image_url.startswith('http'):
            image_url = "[https://www.bdstall.com](https://www.bdstall.com)" + image_url
            
    return title, affiliate_url, image_url

def generate_content(title, aff_url, image_url):
    client = genai.Client(api_key=GEMINI_KEY.strip())
    
    img_html = f'<div style="text-align: center; margin-bottom: 20px;"><img src="{image_url}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/></div>' if image_url else ''
    
    prompt = f"""
    তুমি একজন পেশাদার প্রযুক্তি ও প্রোডাক্ট রিভিউ লেখক। নিচে দেওয়া প্রোডাক্টটির জন্য একটি আকর্ষণীয় ও এসইও-ফ্রেন্ডলি বাংলা ব্লগ পোস্ট তৈরি করো:
    প্রোডাক্টের নাম: {title}
    
    কন্টেন্টের নির্দেশিকা:
    ১. একটি চমৎকার ও আকর্ষণীয় শিরোনাম (<h2>) দাও।
    ২. প্রোডাক্টটির বিস্তারিত ভূমিকা ও বিবরণ দাও।
    ৩. এর মূল ফিচার ও ব্যবহার করার সুবিধাগুলো আলোচনা করো।
    ৪. কেন এটি কেনা উচিত তার একটি চমৎকার উপসংহার দাও।
    ৫. পোস্টের একদম শেষে বড় এবং স্পষ্ট করে কেনার জন্য একটি লিঙ্ক যুক্ত করো।
    
    কেনার লিঙ্ক: {aff_url}
    
    বিশেষ নির্দেশনা:
    - শুধুমাত্র সরাসরি এইচটিএমএল ট্যাগ দিয়ে লেখা শুরু করবে।
    - কোনো ধরনের সূচনা বাক্য (যেমন: "এখানে এইচটিএমএল প্রদান করা হলো") লিখবে না।
    - ব্যাকটিকস (```) বা কোড ব্লক ব্যবহার করবে না।
    """
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
    )
    
    raw_content = response.text
    
    # প্রথম এইচটিএমএল ট্যাগ < এর আগে থাকা সকল টেক্সট এবং ব্যাকটিকস মুছে ফেলার ফিল্টার
    if '<' in raw_content:
        cleaned_content = raw_content[raw_content.find('<'):]
    else:
        cleaned_content = raw_content

    cleaned_content = re.sub(r'```html\s*', '', cleaned_content)
    cleaned_content = re.sub(r'```\s*', '', cleaned_content).strip()
    
    # ছবি এবং কন্টেন্ট একত্র করা
    final_content = f"{img_html}\n{cleaned_content}"
    return title, final_content

def post_to_blogger(title, content):
    if not BLOG_ID or not REFRESH_TOKEN or not CLIENT_ID or not CLIENT_SECRET:
        raise Exception("একটি বা একাধিক সিক্রেট (Secrets) মিসিং রয়েছে! GitHub Secrets চেক করুন।")

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
        post_title, post_content = generate_content(title, aff_url, image_url)
        post_to_blogger(post_title, post_content)
    except Exception as e:
        print(f"Error occurred: {e}")
