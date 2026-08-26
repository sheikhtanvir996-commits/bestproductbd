import os
import random
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from googleapiclient.discovery import build

BLOG_ID = os.getenv("BLOGGER_BLOG_ID")
API_KEY = os.getenv("BLOGGER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
AFFILIATE_ID = os.getenv("BDSTALL_AFFILIATE_ID")

def get_bdstall_product():
    url = "https://www.bdstall.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/details/' in href:
            if not href.startswith('http'):
                href = "https://www.bdstall.com" + href
            products.append(href)
    
    if not products:
        raise Exception("No product links found on BDStall homepage.")
        
    selected_url = random.choice(list(set(products)))
    
    prod_resp = requests.get(selected_url, headers=headers)
    prod_soup = BeautifulSoup(prod_resp.text, 'html.parser')
    
    title = prod_soup.find('h1').text.strip() if prod_soup.find('h1') else "উন্নত মানের ইলেকট্রনিক পণ্য"
    affiliate_url = f"{selected_url}?ref={AFFILIATE_ID}"
    
    return title, affiliate_url

def generate_content(title, aff_url):
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    তুমি একজন বিশেষজ্ঞ প্রোডাক্ট রিভিউ লেখক। নিচে দেওয়া প্রোডাক্টের ওপর ভিত্তি করে একটি দারুণ বাংলা রিভিউ ব্লগ পোস্ট তৈরি করো:
    প্রোডাক্টের নাম: {title}
    
    কন্টেন্টের নির্দেশিকা:
    - একটি চমৎকার ও আকর্ষণীয় শিরোনাম দাও।
    - প্রোডাক্টটির বিস্তারিত বিবরণ, বৈশিষ্ট্য ও সুবিধা আলোচনা করো।
    - কন্টেন্টের শেষে বড় করে একটি কেনার জন্য কল-টু-অ্যাকশন টেক্সট/লিঙ্ক যুক্ত করো।
    - কেনাকাটার লিঙ্কটি হলো: {aff_url}
    
    HTML ট্যাগ ব্যবহার করে আউটপুট দাও (যেমন: <h2>, <p>, <ul>, <li>, <a>) যাতে সরাসরি ব্লগস্পটে পোস্ট হিসেবে দেখানো যায়।
    """
    
    response = model.generate_content(prompt)
    return title, response.text

def post_to_blogger(title, content):
    blogger = build('blogger', 'v3', developerKey=API_KEY)
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    posts = blogger.posts()
    result = posts.insert(blogId=BLOG_ID, body=body).execute()
    print(f"Post successful! URL: {result.get('url')}")

if __name__ == "__main__":
    try:
        title, aff_url = get_bdstall_product()
        post_title, post_content = generate_content(title, aff_url)
        post_to_blogger(post_title, post_content)
    except Exception as e:
        print(f"Error occurred: {e}")
