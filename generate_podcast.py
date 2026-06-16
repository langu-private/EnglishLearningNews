import os
import sys
import argparse
import datetime
import time
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
    
    import time as time_mod
    news_items = []
    twenty_four_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    
    for category, url in rss_sources.items():
        feed = feedparser.parse(url)
        
        category_items = []
        for entry in feed.entries:
            # Check if published in the last 24 hours
            try:
                dt = datetime.datetime.fromtimestamp(time_mod.mktime(entry.published_parsed))
                if dt >= twenty_four_hours_ago:
                    category_items.append(f"- Title: {entry.title}\n  Summary: {entry.get('description', '')}")
            except Exception:
                # If parsing fails, just include it to be safe
                category_items.append(f"- Title: {entry.title}\n  Summary: {entry.get('description', '')}")
            if len(category_items) >= limit_per_category:
                break
                
        if category_items:
            news_items.append(f"\n--- {category.upper()} ---")
            news_items.extend(category_items)
            
    return "\n".join(news_items)

def generate_newsletter(news_text, edition_type, api_key, model="gpt-4o", base_url=None):
    print("Generating newsletter via LLM...")
    
    # Initialize OpenAI client with the provided base_url and API key, adding a timeout
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=180.0)
    
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
The script MUST be an engaging and natural conversation between two hosts: Aria (female, the main anchor) and Andrew (male, the co-host/analyst).
You MUST write the dialogue in a STRICT bilingual format. For every spoken line, output the English sentence first (prefixed with the speaker's name), immediately followed by the Chinese translation on the NEXT line, wrapped in parentheses. ABSOLUTELY NO extra English text is allowed in the dialogue section; every single English word must be spoken by Aria or Andrew.
Example:
[Aria] Good morning! Welcome to our English learning news.
(早上好！欢迎收听我们的英语学习新闻。)
[Andrew] Thanks Aria! Today we have a very big story about...
(谢谢 Aria！今天我们有一个关于...的重大新闻。)

News Items:
{news_text}

Basic English 850 Words list:
{basic_words}

Output Format:
You must output exactly ONE comprehensive section which will serve as the podcast show notes.
CRITICAL: DO NOT use any Markdown formatting (no asterisks **, no hashtags #, no backticks). Apple Podcasts does not support Markdown. Use plain text formatting only.
Include the following in order:
1. 📝 A Catchy Title.
2. 📖 Key Vocabulary (Extract 5-10 advanced or useful words used in the script, with phonetics and Chinese meaning).
3. 🎯 Grammar Focus (Highlight 1-2 important grammar structures used in the news).
4. 🎙️ Full Bilingual Podcast Script (This is the most important part! Use the exact [Host] English. \\n (Chinese) format described above. The English portion must total 2500 words).
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
                # Fallback to a lighter model if the primary one is consistently 503 Overloaded
                if attempt == 1 and "503" in str(e):
                    fallback_model = "gemini-3.1-flash-lite"
                    print(f"High demand detected. Falling back from {model} to {fallback_model} for the next attempts...")
                    model = fallback_model
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
    
    # Split the script by [Aria] or [Andrew] tags
    blocks = re.split(r'\[(Aria|Andrew)\]', text)
    temp_files = []
    
    try:
        for i in range(1, len(blocks), 2):
            speaker = blocks[i].strip()
            speech = blocks[i+1].strip()
            
            if not speech:
                continue
                
            voice = "en-US-AriaNeural" if speaker == "Aria" else "en-US-AndrewNeural"
            
            tmp_mp3 = tempfile.mktemp(suffix=".mp3")
            temp_files.append(tmp_mp3)
            
            cmd = ["edge-tts", "--voice", voice, "--text", speech, "--write-media", tmp_mp3]
            
            # Robust retry loop for edge-tts
            max_tts_retries = 3
            for t_attempt in range(max_tts_retries):
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    time.sleep(1) # Small sleep to avoid hitting rate limits instantly
                    break
                except subprocess.CalledProcessError as e:
                    print(f"edge-tts failed on attempt {t_attempt+1} with error: {e.stderr.decode('utf-8', errors='ignore')}")
                    if t_attempt < max_tts_retries - 1:
                        time.sleep(3)
                    else:
                        raise e
            
        if temp_files:
            list_file = tempfile.mktemp(suffix=".txt")
            with open(list_file, 'w') as lf:
                for f in temp_files:
                    lf.write(f"file '{f}'\n")
            
            # Use ffmpeg to properly concatenate MP3s so headers aren't broken on iOS
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_mp3], check=True, capture_output=True)
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
    
    edition_dir = f"editions/{date_str}_{edition}"
    os.makedirs(edition_dir, exist_ok=True)
    
    print("Saving blog post (Bilingual Show Notes)...")
    blog_path = os.path.join(edition_dir, f"{edition}_Blog.md")
    with open(blog_path, 'w', encoding='utf-8') as f:
        f.write(result)
        
    print("Extracting English script for audio generation...")
    audio_script_en = []
    lines = result.split('\n')
    for line in lines:
        line_stripped = line.strip()
        # Only extract lines explicitly spoken by the hosts for the TTS engine
        if line_stripped.startswith("[Aria]") or line_stripped.startswith("[Andrew]"):
            audio_script_en.append(line_stripped)
            
    audio_script_text = "\n\n".join(audio_script_en)
    script_path = os.path.join(edition_dir, "audio_script.txt")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(audio_script_text)
        
    print("Creating podcast audio...")
    mp3_path = os.path.join(edition_dir, f"{edition}_Podcast.mp3")
    create_audio(audio_script_text, mp3_path, args.api_key)
    
    # Call the RSS generator here
    update_rss_feed(edition, date_str, mp3_path, args.github_url)
    
from feedgen.feed import FeedGenerator
import pytz

def update_rss_feed(edition, date_str, mp3_path, base_url):
    print("Updating RSS Feed...")
    fg = FeedGenerator()
    fg.load_extension('podcast')
    
    fg.title('虎子老师教英语')
    fg.description('Daily News Podcast, spoken strictly in Basic English 850 Words.')
    fg.link(href=base_url, rel='alternate')
    fg.language('en')
    
    fg.author({'name': '虎子老师', 'email': 'langu@qq.com'})
    fg.podcast.itunes_author('虎子老师')
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
                hour = 19 if ed_part == "Evening" else 8
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
                    content = bf.read()
                    # Strip everything before the dialogue starts to match audio exactly
                    if "4. 🎙️ Full Bilingual Podcast Script:" in content:
                        content = content.split("4. 🎙️ Full Bilingual Podcast Script:")[1].strip()
                    elif "[Aria]" in content:
                        content = "[Aria]" + content.split("[Aria]", 1)[1]
                        
                    blog_html = content.replace('\n', '<br>')
                    
            fe.description(blog_html)
            fe.enclosure(mp3_url, file_size, 'audio/mpeg')
            
    fg.rss_file('podcast.xml')
    print("podcast.xml updated.")

if __name__ == "__main__":
    main()
