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

CRITICAL RULE: 
The English portion MUST be written using ONLY the words from the provided "Basic English 850 Words" list.
You MAY use proper nouns (names of people, specific countries, companies) not on the list, but ANY OTHER verb, adjective, adverb, or noun MUST be from the 850 words.
Keep sentences very simple, short, and clear, but write a very long and detailed overall script to hit the 20-minute mark.

News Items:
{news_text}

Basic English 850 Words list:
{basic_words}

Output Format:
You must output exactly two sections separated by "===AUDIO SCRIPT===" and "===BILINGUAL BLOG===".

===AUDIO SCRIPT===
(Write the English-only script here. This will be converted to audio for the podcast. Start with "Good {edition_type.lower()}..." and end with a nice sign-off.)
===BILINGUAL BLOG===
(Write the bilingual version here for the reading blog. Give it a catchy title, then line-by-line or paragraph-by-paragraph English and Chinese translation.)
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    return response.choices[0].message.content

def create_audio(text, output_mp3):
    print(f"Generating audio to {output_mp3}...")
    # Using edge-tts with a professional American voice
    voice = "en-US-AriaNeural"
    
    cmd = ["edge-tts", "--voice", voice, "--text", text, "--write-media", output_mp3]
    subprocess.run(cmd, check=True)
    print("Audio generation complete.")

def main():
    parser = argparse.ArgumentParser(description="Generate Basic English News Podcast")
    parser.add_argument("--edition", choices=["Morning", "Evening"], default="Morning", help="Morning or Evening edition")
    parser.add_argument("--api-key", required=True, help="LLM API Key")
    parser.add_argument("--base-url", default=None, help="Base URL for LLM API (e.g., https://api.deepseek.com/v1)")
    parser.add_argument("--model", default="gpt-4o", help="Model name")
    
    parser.add_argument("--github-url", default="https://YOUR_USERNAME.github.io/EnglishLearningNews", help="The GitHub Pages Base URL")
    
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
    create_audio(audio_script, audio_mp3_path)
    
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
            fe.description(f"News podcast for {folder}")
            fe.enclosure(mp3_url, file_size, 'audio/mpeg')
            
    fg.rss_file('podcast.xml')
    print("podcast.xml updated.")

    print(f"\nDone! All files saved in: {out_dir}")
    print(f"- Blog: {blog_path}")
    print(f"- Podcast: {audio_mp3_path}")
    print("- RSS Feed: podcast.xml")

if __name__ == "__main__":
    main()
