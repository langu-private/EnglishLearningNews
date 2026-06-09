import os
import sys
import argparse
import datetime
import feedparser
from openai import OpenAI
import subprocess

# Load 850 words
with open("basic_english_850.txt", "r") as f:
    basic_words = f.read()

def fetch_top_news(limit_per_category=4):
    print("Fetching news from multiple categories...")
    
    rss_sources = {
        "Technology": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
        "Business & Finance": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "China Domestic": "https://news.google.com/rss/search?q=China+Domestic+News&hl=en-US&gl=US&ceid=US:en",
        "World & Conflicts": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en"
    }
    
    news_items = []
    for category, url in rss_sources.items():
        feed = feedparser.parse(url)
        news_items.append(f"\n--- {category.upper()} ---")
        for entry in feed.entries[:limit_per_category]:
            news_items.append(f"- Title: {entry.title}\n  Summary: {entry.get('description', '')}")
            
    return "\n".join(news_items)

def generate_newsletter(news_text, edition_type, api_key, model="gpt-4o", base_url=None):
    print("Generating newsletter via LLM...")
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    prompt = f"""You are an expert English teacher for ESL learners.
I will provide you with today's news items.
Your task is to write a comprehensive '{edition_type} News Podcast' script in both English and Chinese.
The spoken audio must last approximately 20 minutes. At an ESL speaking rate of 130 words per minute, YOUR ENGLISH AUDIO SCRIPT MUST BE AT LEAST 2500 WORDS LONG.
To reach this length, do NOT just summarize the headlines. You must provide deep-dive explanations, historical background context, related impact analysis, and engaging storytelling for EACH news item.

CRITICAL RULE 1: 
The English portion MUST be written using ONLY the words from the provided "Basic English 850 Words" list.
You MAY use proper nouns (names of people, specific countries, companies) not on the list, but ANY OTHER verb, adjective, adverb, or noun MUST be from the 850 words.
Keep sentences very simple, short, and clear, but write a very long and detailed overall script to hit the 20-minute mark.

CRITICAL RULE 2 (DIALOGUE FORMAT):
The script MUST be an engaging and natural conversation between two hosts: Aria (female, the main anchor) and Guy (male, the co-host/analyst).
You must prefix every single spoken line with their bracketed name tag so the audio generator knows who is speaking.
Example:
[Aria] Good morning! Welcome to our English learning news.
[Guy] Thanks Aria! Today we have a very big story about...

News Items:
{news_text}

Basic English 850 Words list:
{basic_words}

Output Format:
You must output exactly two sections separated by "===AUDIO SCRIPT===" and "===BILINGUAL BLOG===".

===AUDIO SCRIPT===
(Write the English-only script here. This will be converted to audio for the podcast. Start with "Good {edition_type.lower()}..." and end with a nice sign-off.)
===BILINGUAL BLOG===
(Write the comprehensive show notes here. You MUST include the following in order:
1. A catchy title.
2. 📖 Key Vocabulary (Extract 5-10 advanced or useful words used in the script, with phonetics and Chinese meaning).
3. 🎯 Grammar Focus (Highlight 1-2 important grammar structures used in the news).
4. 📝 Full Bilingual Script (Line-by-line or paragraph-by-paragraph English and Chinese translation of the entire audio script).
5. 🔗 Useful Links (A placeholder "Read more at [English Learning News](https://langu-private.github.io/EnglishLearningNews)").)
"""

    import time
    
    max_retries = 4
    for attempt in range(max_retries):
        try:
            print(f"LLM API Call Attempt {attempt + 1} of {max_retries}...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API Error encountered: {e}")
            if attempt < max_retries - 1:
                wait_seconds = (attempt + 1) * 30  # Wait 30s, 60s, 90s...
                print(f"Model is busy. Retrying in {wait_seconds} seconds...")
                time.sleep(wait_seconds)
            else:
                print("Max retries reached. The server is consistently overloaded.")
                raise e

def create_audio(text, output_mp3, api_key):
    print(f"Generating conversational audio to {output_mp3} using edge-tts...")
    import tempfile
    import re
    import os
    import subprocess
    
    # Split the script by [Aria] or [Guy] tags
    blocks = re.split(r'\[(Aria|Guy)\]', text)
    temp_files = []
    
    try:
        for i in range(1, len(blocks), 2):
            speaker = blocks[i].strip()
            speech = blocks[i+1].strip()
            
            if not speech:
                continue
                
            voice = "en-US-AriaNeural" if speaker == "Aria" else "en-US-GuyNeural"
            
            tmp_mp3 = tempfile.mktemp(suffix=".mp3")
            temp_files.append(tmp_mp3)
            
            cmd = ["edge-tts", "--voice", voice, "--text", speech, "--write-media", tmp_mp3]
            subprocess.run(cmd, check=True)
            
        if temp_files:
            with open(output_mp3, 'wb') as outfile:
                for f in temp_files:
                    with open(f, 'rb') as infile:
                        outfile.write(infile.read())
            print("Conversational audio generation complete.")
        else:
            print("No valid speaker tags found! Falling back to single voice...")
            cmd = ["edge-tts", "--voice", "en-US-AriaNeural", "--text", text, "--write-media", output_mp3]
            subprocess.run(cmd, check=True)
            
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

def main():
    parser = argparse.ArgumentParser(description="Generate Basic English News Podcast")
    parser.add_argument("--edition", choices=["Morning", "Evening"], default="Morning", help="Morning or Evening edition")
    parser.add_argument("--api-key", required=True, help="LLM API Key")
    parser.add_argument("--base-url", default=None, help="Base URL for LLM API (e.g., https://api.deepseek.com/v1)")
    parser.add_argument("--model", default="gpt-4o", help="Model name")
    
    parser.add_argument("--github-url", default="https://langu-private.github.io/EnglishLearningNews", help="The GitHub Pages Base URL")
    
    args = parser.parse_args()

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    edition = args.edition
    
    news_text = fetch_top_news()
    result = generate_newsletter(news_text, edition, args.api_key, args.model, args.base_url)
    
    try:
        parts = result.split("===BILINGUAL BLOG===")
        audio_script = parts[0].replace("===AUDIO SCRIPT===", "").strip()
        blog_content = parts[1].strip()
    except Exception as e:
        print("Failed to parse LLM output. Full output:")
        print(result)
        sys.exit(1)
        
    out_dir = f"editions/{date_str}_{edition}"
    os.makedirs(out_dir, exist_ok=True)
    
    blog_path = os.path.join(out_dir, f"{edition}_Blog.md")
    with open(blog_path, "w") as f:
        f.write(blog_content)
        
    audio_txt_path = os.path.join(out_dir, "audio_script.txt")
    with open(audio_txt_path, "w") as f:
        f.write(audio_script)
        
    audio_mp3_path = os.path.join(out_dir, f"{edition}_Podcast.mp3")
    create_audio(audio_script, audio_mp3_path, args.api_key)
    
    # Call the RSS generator here
    update_rss_feed(edition, date_str, audio_mp3_path, args.github_url)
    
from feedgen.feed import FeedGenerator
import pytz

def update_rss_feed(edition, date_str, mp3_path, base_url):
    print("Updating RSS Feed...")
    fg = FeedGenerator()
    fg.load_extension('podcast')
    
    fg.title('850 Words Basic English News Podcast')
    fg.description('Daily Morning and Evening News, spoken strictly in Basic English 850 Words.')
    fg.link(href=base_url, rel='alternate')
    fg.language('en')
    
    fg.author({'name': 'langu', 'email': 'langu@qq.com'})
    fg.podcast.itunes_author('langu')
    fg.podcast.itunes_category('Education', 'Language Learning')
    
    cover_url = f"{base_url}/cover.png"
    fg.logo(cover_url)
    fg.podcast.itunes_image(cover_url)
    
    # Try to load existing feed if we have one (we'll simplify by regenerating with just the latest for now, or you can parse an old one. For robust github pages, regenerating with recent ones requires scanning the dir)
    # To keep it simple, we will scan the 'editions' directory and add all existing mp3s!
    
    editions_dir = "editions"
    if os.path.exists(editions_dir):
        folders = sorted(os.listdir(editions_dir), reverse=True)
        for folder in folders:
            folder_path = os.path.join(editions_dir, folder)
            if not os.path.isdir(folder_path): continue
            
            # Look for MP3
            mp3_files = [f for f in os.listdir(folder_path) if f.endswith('.mp3')]
            if not mp3_files: continue
            
            mp3_file = mp3_files[0]
            full_mp3_path = os.path.join(folder_path, mp3_file)
            file_size = str(os.path.getsize(full_mp3_path))
            
            # The URL to the MP3 on GitHub Pages
            mp3_url = f"{base_url}/editions/{folder}/{mp3_file}"
            
            fe = fg.add_entry()
            fe.id(mp3_url)
            fe.title(f"{folder.replace('_', ' ')} News Podcast")
            
            # Extract and set exact Beijing Time publication date for correct sorting in Apple Podcasts
            try:
                date_part, ed_part = folder.split('_')
                year, month, day = map(int, date_part.split('-'))
                hour = 8 if ed_part == "Morning" else 19
                tz = pytz.timezone('Asia/Shanghai')
                pub_date = tz.localize(datetime.datetime(year, month, day, hour, 0, 0))
            except Exception:
                pub_date = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
            fe.pubDate(pub_date)
            
            # Read the bilingual blog text to display in Apple Podcasts
            blog_files = [f for f in os.listdir(folder_path) if f.endswith('_Blog.md')]
            blog_html = f"News podcast for {folder}"
            if blog_files:
                with open(os.path.join(folder_path, blog_files[0]), 'r', encoding='utf-8') as bf:
                    blog_html = bf.read().replace('\n', '<br>')
                    
            fe.description(blog_html)
            fe.enclosure(mp3_url, file_size, 'audio/mpeg')
            
    fg.rss_file('podcast.xml')
    print("podcast.xml updated.")

if __name__ == "__main__":
    main()
