import os
import re
import tempfile
import subprocess
import time

def parse_vtt(vtt_file, time_offset):
    segments = []
    if not os.path.exists(vtt_file):
        return segments
    with open(vtt_file, 'r', encoding='utf-8') as f:
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
                start_t = parse_time(times[0]) + time_offset
                end_t = parse_time(times[1]) + time_offset
                segments.append({
                    'start': round(start_t, 3),
                    'end': round(end_t, 3),
                    'text': sentence_text
                })
            except Exception as e:
                pass
    return segments

def get_mp3_duration(filepath):
    res = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath])
    return float(res.decode('utf-8').strip())

def process_file(input_file, title, output_name):
    print(f"Processing {title}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    structured_content = []
    
    current_speaker = None
    current_speech = []
    
    def commit_speech():
        nonlocal current_speaker, current_speech
        if current_speaker and current_speech:
            structured_content.append({
                'type': 'speech',
                'speaker': current_speaker,
                'text': " ".join(current_speech)
            })
        current_speaker = None
        current_speech = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if it's a speaker line
        if line.startswith("Aria:") or line.startswith("Andrew:"):
            commit_speech()
            parts = line.split(":", 1)
            current_speaker = parts[0].strip()
            current_speech.append(parts[1].strip())
        elif line.startswith("=") or line.startswith("---") or "Travel English" in line:
            commit_speech()
            structured_content.append({
                'type': 'header',
                'text': line
            })
        else:
            # Maybe continuation of speech or text
            if current_speaker:
                current_speech.append(line)
            else:
                structured_content.append({
                    'type': 'header',
                    'text': line
                })
                
    commit_speech()
    
    # Generate audio
    temp_files = []
    current_time_offset = 0.0
    
    for block in structured_content:
        if block['type'] == 'speech':
            voice = "en-US-AriaNeural" if block['speaker'] == "Aria" else "en-US-AndrewNeural"
            
            tmp_mp3 = tempfile.mktemp(suffix=".mp3")
            tmp_vtt = tempfile.mktemp(suffix=".vtt")
            temp_files.append(tmp_mp3)
            temp_files.append(tmp_vtt)
            
            cmd = ["edge-tts", "--voice", voice, "--text", block['text'], "--write-media", tmp_mp3, "--write-subtitles", tmp_vtt]
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    time.sleep(0.5)
                    break
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")
                    time.sleep(2)
            
            # Parse VTT
            segs = parse_vtt(tmp_vtt, current_time_offset)
            block['segments'] = segs
            
            try:
                duration = get_mp3_duration(tmp_mp3)
                current_time_offset += duration
            except:
                if segs:
                    current_time_offset = segs[-1]['end']
                    
    mp3_output = f"{output_name}.mp3"
    if temp_files:
        list_file = tempfile.mktemp(suffix=".txt")
        with open(list_file, 'w') as lf:
            for f in temp_files:
                if f.endswith('.mp3'):
                    lf.write(f"file '{f}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", mp3_output], check=True, capture_output=True)
    
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)
            
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 单句跟读</title>
    <style>
        :root {{ --primary: #4F46E5; --bg: #F3F4F6; --card: #FFFFFF; --text: #1F2937; }}
        body {{ font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; line-height: 1.6; }}
        header {{ background: linear-gradient(135deg, #4F46E5, #7C3AED); color: white; padding: 3rem 2rem; text-align: center; }}
        header h1 {{ margin: 0; font-size: 2.5rem; }}
        .container {{ max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .nav-link {{ display: inline-block; color: white; margin-top: 1rem; text-decoration: underline; }}
        .header-line {{ font-weight: bold; color: #4B5563; margin-top: 2rem; padding-bottom: 0.5rem; border-bottom: 2px solid #E5E7EB; }}
        .speech-line {{ margin: 1rem 0; padding: 1rem; background: #F9FAFB; border-radius: 8px; border-left: 4px solid var(--primary); }}
        .play-btn {{ margin-left: 10px; cursor: pointer; padding: 4px 10px; border-radius: 6px; border: 1px solid #D1D5DB; background: #FFFFFF; font-size: 0.9rem; transition: background 0.2s; }}
        .play-btn:hover {{ background: #F3F4F6; }}
        audio {{ width: 100%; position: sticky; top: 0; z-index: 100; background: white; padding: 10px 0; }}
    </style>
    <script>
        function playShadowing(start, end) {{
            const audio = document.getElementById('main-audio');
            if (!audio) return;
            audio.currentTime = start;
            audio.play();
            
            const checkTime = () => {{
                if (audio.currentTime >= end) {{
                    audio.pause();
                    audio.removeEventListener('timeupdate', checkTime);
                }}
            }};
            audio.removeEventListener('timeupdate', checkTime);
            audio.addEventListener('timeupdate', checkTime);
        }}
    </script>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <a href="index.html" class="nav-link">← 返回主页 (Back to Home)</a>
    </header>
    <div class="container">
        <audio id="main-audio" controls preload="metadata">
            <source src="{output_name}.mp3" type="audio/mpeg">
        </audio>
        <div class="card">
"""
    for block in structured_content:
        if block['type'] == 'header':
            html += f"            <div class='header-line'>{block['text']}</div>\n"
        elif block['type'] == 'speech':
            speaker = block['speaker']
            segments = block.get('segments', [])
            if not segments:
                html += f"            <div class='speech-line'><strong>{speaker}:</strong> {block['text']}</div>\n"
            else:
                for seg in segments:
                    text = seg['text'].replace("'", "&apos;").replace('"', "&quot;")
                    start = seg['start']
                    end = seg['end']
                    html += f"            <div class='speech-line'><strong>{speaker}:</strong> {text} <button class='play-btn' onclick=\"playShadowing({start}, {end})\">🎵 播放本句</button></div>\n"
    
    html += """        </div>
    </div>
</body>
</html>"""

    with open(f"{output_name}.html", 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Finished {title}")

if __name__ == "__main__":
    process_file("/Users/langu/Documents/4-能力提升/850/life.txt", "Basic English 850: Daily Life", "special_life")
    process_file("/Users/langu/Documents/4-能力提升/850/travel.txt", "Travel English 1000", "special_travel")
