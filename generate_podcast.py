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
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=600.0)
    
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
    
    try:
        print(f"LLM API Call for {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API Error encountered: {e}")
        print("Server is blocked or overloaded. Returning failure immediately without retries.")
        raise e

def generate_learning_document(script_text, api_key, model="gemini-3.5-flash", base_url=None):
    print("Generating learning document...")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=600.0)
    prompt = f"""You are an expert English teacher. I am providing you with the transcript of a daily news podcast meant for ESL learners.
Please create a comprehensive and engaging 'Learning Document' in Markdown format for this podcast.
Include the following:
1. **Podcast Summary**: A brief Chinese summary of the topics discussed.
2. **Key Vocabulary**: Extract 5-10 advanced or important words/phrases, provide their phonetic transcriptions, Chinese meanings, and example sentences.
3. **Useful Expressions**: 3-5 idiomatic expressions or sentence structures used in the podcast, with explanations.
4. **Comprehension Check**: 3 simple questions (with answers provided at the end) to test understanding.
5. **How to Use this Document**: A brief study guide on how to listen to the podcast while reviewing this vocabulary.

Podcast Script:
{script_text}
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating learning doc: {e}")
        return "Learning document could not be generated due to an error."

def create_audio(text, output_mp3, api_key):
    print(f"Generating conversational audio to {output_mp3} using edge-tts...")
    import tempfile
    import re
    import os
    import subprocess
    import json
    
    # Split the script by [Aria] or [Andrew] tags
    blocks = re.split(r'\[(Aria|Andrew)\]', text)
    temp_files = []
    shadowing_data = []
    current_time_offset = 0.0
    
    try:
        for i in range(1, len(blocks), 2):
            speaker = blocks[i].strip()
            speech = blocks[i+1].strip()
            
            if not speech:
                continue
                
            voice = "en-US-AriaNeural" if speaker == "Aria" else "en-US-AndrewNeural"
            
            tmp_mp3 = tempfile.mktemp(suffix=".mp3")
            tmp_vtt = tempfile.mktemp(suffix=".vtt")
            temp_files.append(tmp_mp3)
            temp_files.append(tmp_vtt)
            
            cmd = ["edge-tts", "--voice", voice, "--text", speech, "--write-media", tmp_mp3, "--write-subtitles", tmp_vtt]
            
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
                        
            # Parse VTT for shadowing
            if os.path.exists(tmp_vtt):
                with open(tmp_vtt, 'r', encoding='utf-8') as f:
                    vtt_content = f.read().split('\n\n')
                for block in vtt_content:
                    lines = block.strip().split('\n')
                    if len(lines) >= 3 and '-->' in lines[1]:
                        times = lines[1].split(' --> ')
                        sentence_text = " ".join(lines[2:])
                        def parse_time(t_str):
                            t_str = t_str.replace(',', '.')
                            h, m, s = t_str.split(':')
                            return int(h)*3600 + int(m)*60 + float(s)
                        try:
                            start_t = parse_time(times[0]) + current_time_offset
                            end_t = parse_time(times[1]) + current_time_offset
                            shadowing_data.append({
                                'speaker': speaker,
                                'start': round(start_t, 3),
                                'end': round(end_t, 3),
                                'text': sentence_text
                            })
                        except Exception as e:
                            print("Error parsing VTT line:", e)
                            
            # Get duration of tmp_mp3 to update current_time_offset
            try:
                res = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', tmp_mp3])
                duration = float(res.decode('utf-8').strip())
                current_time_offset += duration
            except Exception as e:
                print("Error getting duration:", e)
                if shadowing_data and shadowing_data[-1]['speaker'] == speaker:
                    current_time_offset = shadowing_data[-1]['end']
            
        if temp_files:
            list_file = tempfile.mktemp(suffix=".txt")
            with open(list_file, 'w') as lf:
                for f in temp_files:
                    if f.endswith('.mp3'):
                        lf.write(f"file '{f}'\n")
            
            # Use ffmpeg to properly concatenate MP3s so headers aren't broken on iOS
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_mp3], check=True, capture_output=True)
            print("Conversational audio generation complete.")
        else:
            print("No valid speaker tags found! Falling back to single voice...")
            cmd = ["edge-tts", "--voice", "en-US-AriaNeural", "--text", text, "--write-media", output_mp3]
            subprocess.run(cmd, check=True)
            
        return shadowing_data
            
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

def main():
    parser = argparse.ArgumentParser(description="Generate Basic English News Podcast")
    parser.add_argument("--edition", choices=["Morning", "Evening", "Daily"], default="Daily", help="Morning, Evening, or Daily edition")
    parser.add_argument("--api-key", required=True, help="LLM API Key")
    parser.add_argument("--base-url", default=None, help="Base URL for LLM API (e.g., https://api.deepseek.com/v1)")
    parser.add_argument("--model", default="gpt-4o", help="Model name")
    
    parser.add_argument("--github-url", default="https://langu-private.github.io/EnglishLearningNews", help="The GitHub Pages Base URL")
    
    args = parser.parse_args()

    import pytz
    beijing_tz = pytz.timezone('Asia/Shanghai')
    date_str = datetime.datetime.now(beijing_tz).strftime("%Y-%m-%d")
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
        
    print("Generating and saving Learning Document...")
    learning_doc_md = generate_learning_document(audio_script_text, args.api_key, args.model, args.base_url)
    doc_path = os.path.join(edition_dir, "Learning_Document.md")
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(learning_doc_md)
        
    print("Creating podcast audio...")
    mp3_path = os.path.join(edition_dir, f"{edition}_Podcast.mp3")
    shadowing_data = create_audio(audio_script_text, mp3_path, args.api_key)
    
    if shadowing_data:
        print("Appending single-sentence shadowing to Learning Document...")
        shadowing_html = "\n\n## 🎧 单句跟读 (Sentence Shadowing)\n\n"
        audio_id = f"audio-{date_str}_{edition}"
        for seg in shadowing_data:
            speaker = seg['speaker']
            start = seg['start']
            end = seg['end']
            # Escape quotes for html attributes
            text = seg['text'].replace("'", "&apos;").replace('"', "&quot;")
            shadowing_html += f"<p><strong>{speaker}:</strong> {seg['text']} <button onclick=\"playShadowing('{audio_id}', {start}, {end})\" style=\"margin-left: 10px; cursor: pointer; padding: 2px 6px; border-radius: 4px; border: 1px solid #ccc; background: #fff;\">🎵 播放本句</button></p>\n"
            
        with open(doc_path, 'a', encoding='utf-8') as f:
            f.write(shadowing_html)
    
    # Call the RSS generator here
    update_rss_feed(edition, date_str, mp3_path, args.github_url)
    
    # Update the GitHub Pages index.html
    update_index_html()

def update_index_html():
    print("Updating index.html...")
    try:
        import markdown
    except ImportError:
        print("markdown package not installed. Skipping index.html update.")
        return
        
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>虎子老师教英语 - 每日播客与学习文档</title>
    <style>
        :root { --primary: #4F46E5; --bg: #F3F4F6; --card: #FFFFFF; --text: #1F2937; }
        body { font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; line-height: 1.6; }
        header { background: linear-gradient(135deg, #4F46E5, #7C3AED); color: white; padding: 3rem 2rem; text-align: center; }
        header h1 { margin: 0; font-size: 2.5rem; }
        header p { opacity: 0.9; margin-top: 1rem; font-size: 1.1rem; }
        .container { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
        .episode { background: var(--card); border-radius: 12px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .episode:hover { transform: translateY(-5px); }
        .episode h2 { margin-top: 0; color: var(--primary); border-bottom: 2px solid #E5E7EB; padding-bottom: 0.5rem; }
        audio { width: 100%; margin: 1rem 0; }
        .learning-doc { background: #F9FAFB; padding: 1.5rem; border-radius: 8px; border-left: 4px solid var(--primary); margin-top: 1rem; }
        .learning-doc h3 { margin-top: 0; }
        .rss-link { display: inline-block; background: #FEF2F2; color: #DC2626; padding: 0.5rem 1rem; border-radius: 99px; text-decoration: none; font-weight: bold; margin-top: 1rem; }
    </style>
    <script>
        function playShadowing(audioId, start, end) {
            const audio = document.getElementById(audioId);
            if (!audio) return;
            audio.currentTime = start;
            audio.play();
            
            const checkTime = () => {
                if (audio.currentTime >= end) {
                    audio.pause();
                    audio.removeEventListener('timeupdate', checkTime);
                }
            };
            // Remove previous listener if exists
            audio.removeEventListener('timeupdate', checkTime);
            audio.addEventListener('timeupdate', checkTime);
        }
    </script>
</head>
<body>
    <header>
        <h1>虎子老师教英语</h1>
        <p>Daily English Learning Podcast & Study Guides</p>
        <a href="podcast.xml" class="rss-link">🎙️ Subscribe via RSS / Apple Podcasts</a>
    </header>
    <div class="container">
"""
    import os
    editions_dir = "editions"
    if os.path.exists(editions_dir):
        folders = sorted(os.listdir(editions_dir), reverse=True)
        for folder in folders:
            folder_path = os.path.join(editions_dir, folder)
            if not os.path.isdir(folder_path): continue
            
            mp3_files = [f for f in os.listdir(folder_path) if f.endswith('.mp3')]
            doc_file = os.path.join(folder_path, "Learning_Document.md")
            
            if not mp3_files: continue
            
            mp3_file = mp3_files[0]
            mp3_url = f"editions/{folder}/{mp3_file}"
            title = folder.replace('_', ' ')
            
            html_content += f'''
        <div class="episode">
            <h2>{title} Podcast</h2>
            <audio id="audio-{folder}" controls preload="none">
                <source src="{mp3_url}" type="audio/mpeg">
            </audio>'''
            
            if os.path.exists(doc_file):
                with open(doc_file, 'r', encoding='utf-8') as df:
                    md_text = df.read()
                    html_doc = markdown.markdown(md_text)
                    html_content += f'''
            <div class="learning-doc">
                {html_doc}
            </div>'''
            html_content += "\n        </div>"
            
    html_content += """
    </div>
</body>
</html>"""
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("index.html updated successfully.")

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
