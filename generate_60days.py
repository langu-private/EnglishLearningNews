import os
import re
import tempfile
import subprocess
import time
import json
from deep_translator import GoogleTranslator
import nltk
from nltk.corpus import cmudict

# Ensure cmudict is downloaded
try:
    d = cmudict.dict()
except:
    nltk.download('cmudict')
    d = cmudict.dict()

arpabet_to_kk = {
    'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AH0': 'ə', 'AO': 'ɔ', 'AW': 'aʊ', 'AY': 'aɪ',
    'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'EH': 'ɛ', 'ER': 'ɚ', 'ER0': 'ɚ', 'ER1': 'ɝ',
    'EY': 'e', 'F': 'f', 'G': 'ɡ', 'HH': 'h', 'IH': 'ɪ', 'IY': 'i', 'JH': 'dʒ',
    'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ŋ', 'OW': 'o', 'OY': 'ɔɪ',
    'P': 'p', 'R': 'r', 'S': 's', 'SH': 'ʃ', 'T': 't', 'TH': 'θ', 'UH': 'ʊ',
    'UW': 'u', 'V': 'v', 'W': 'w', 'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'
}

def get_kk(word):
    clean_word = re.sub(r'[^a-z\']', '', word.lower())
    if clean_word in d:
        phones = d[clean_word][0]
        result = []
        for p in phones:
            base = p.strip('012')
            if '1' in p or '2' in p:
                stress_mark = 'ˈ' if '1' in p else 'ˌ'
                insert_idx = len(result)
                while insert_idx > 0 and result[insert_idx-1] not in ['ɑ', 'æ', 'ʌ', 'ə', 'ɔ', 'aʊ', 'aɪ', 'ɛ', 'ɚ', 'ɝ', 'e', 'ɪ', 'i', 'o', 'ɔɪ', 'ʊ', 'u']:
                    insert_idx -= 1
                result.insert(insert_idx, stress_mark)
                
            if p == 'AH0':
                result.append('ə')
            elif p in ['ER0', 'ER1', 'ER2']:
                result.append('ɚ' if '0' in p else 'ɝ')
            else:
                result.append(arpabet_to_kk.get(base, base))
        suffix = re.search(r'[^a-z\']*$', word.lower()).group()
        return "".join(result) + suffix
    return word

def sentence_to_kk_linked(sentence):
    words = sentence.split()
    if not words: return ""
    vowels = set('ɑæʌəɔaɛɚɝeɪioʊu')
    consonants = set('btʃdðfɡhkʒlmnŋprsʃtθvwjz')
    words_kk = [get_kk(w) for w in words]
    linked = []
    for i in range(len(words_kk)-1):
        w1 = words_kk[i]
        w2 = words_kk[i+1]
        has_punct = bool(re.search(r'[.,!?;\:]$', w1))
        linked.append(w1)
        w1_clean = re.sub(r'[^a-zɑæʌəɔɛɚɝeɪioʊuθðʃʒŋɡ]', '', w1.lower().replace('ˈ','').replace('ˌ',''))
        w2_clean = re.sub(r'[^a-zɑæʌəɔɛɚɝeɪioʊuθðʃʒŋɡ]', '', w2.lower().replace('ˈ','').replace('ˌ',''))
        if w1_clean and w2_clean and not has_punct:
            last_char = w1_clean[-1]
            first_char = w2_clean[0]
            if last_char in consonants and first_char in vowels:
                linked.append('‿')
            elif last_char in consonants and first_char == last_char:
                linked.append('‿')
            else:
                linked.append(' ')
        else:
            linked.append(' ')
    linked.append(words_kk[-1])
    return "".join(linked).replace(' ‿ ', '‿').replace('‿ ', '‿').replace(' ‿', '‿')

translator = GoogleTranslator(source='en', target='zh-CN')

def get_translation(text, cache):
    if text in cache:
        return cache[text]
    try:
        time.sleep(0.1) # to prevent rate limit
        res = translator.translate(text)
        cache[text] = res
        return res
    except Exception as e:
        print(f"Translation failed for '{text}': {e}")
        time.sleep(1)
        return text

def parse_vtt(vtt_file, time_offset):
    segments = []
    if not os.path.exists(vtt_file): return segments
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
            except:
                pass
    return segments

def get_mp3_duration(filepath):
    res = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath])
    return float(res.decode('utf-8').strip())

def process_60days(input_file, output_html):
    # Load translation cache
    trans_cache = {}
    if os.path.exists('translations_60days.json'):
        with open('translations_60days.json', 'r', encoding='utf-8') as f:
            trans_cache = json.load(f)
            
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    sections = [] # will hold dicts: {title: "...", type: "dialogue"/"vocab", id: "day01_dialogue", blocks: [...]}
    current_section = None
    
    # regex
    re_day = re.compile(r'----------\s+(Day \d+ .*?)\s+----------')
    re_vocab = re.compile(r'\[\s*(Vocab Card .*?)\s*\]')
    re_dialogue = re.compile(r'^([A-Z]):\s*(.+)')
    re_word = re.compile(r'^\d+\.\s+([a-zA-Z\s]+?)\s+([^\x00-\x7F]+.*)$') # matches "1. eye  眼睛"
    re_example = re.compile(r'^→\s*(.+)')
    
    day_counter = 0
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        m_day = re_day.search(line)
        if m_day:
            day_counter += 1
            current_section = {
                'title': m_day.group(1),
                'type': 'dialogue',
                'id': f'day{day_counter:02d}_dialogue',
                'blocks': []
            }
            sections.append(current_section)
            continue
            
        m_vocab = re_vocab.search(line)
        if m_vocab:
            current_section = {
                'title': m_vocab.group(1),
                'type': 'vocab',
                'id': f'day{day_counter:02d}_vocab',
                'blocks': []
            }
            sections.append(current_section)
            continue
            
        if not current_section:
            continue
            
        # Parse blocks
        if current_section['type'] == 'dialogue':
            m_dia = re_dialogue.match(line)
            if m_dia:
                speaker = m_dia.group(1)
                text = m_dia.group(2)
                zh = get_translation(text, trans_cache)
                current_section['blocks'].append({
                    'speaker': 'Aria' if speaker == 'A' else 'Andrew',
                    'en': text,
                    'zh': zh
                })
        elif current_section['type'] == 'vocab':
            m_word = re_word.match(line)
            if m_word:
                en = m_word.group(1).strip()
                zh = m_word.group(2).strip()
                current_section['blocks'].append({
                    'speaker': 'Aria',
                    'en': en,
                    'zh': zh,
                    'is_word': True
                })
            else:
                m_ex = re_example.match(line)
                if m_ex:
                    en = m_ex.group(1).strip()
                    zh = get_translation(en, trans_cache)
                    current_section['blocks'].append({
                        'speaker': 'Aria',
                        'en': en,
                        'zh': zh,
                        'is_word': False
                    })
    
    # Save cache
    with open('translations_60days.json', 'w', encoding='utf-8') as f:
        json.dump(trans_cache, f, ensure_ascii=False, indent=2)
        
    print(f"Parsed {len(sections)} sections.")
    
    # Generate Audio and HTML
    
    # Pre-build TOC
    toc_html = """
    <div id="mobile-menu-btn" onclick="document.getElementById('toc-sidebar').classList.toggle('open')">☰ 课程目录</div>
    <div id="toc-sidebar">
        <div class="toc-header">
            <h3>📖 目录</h3>
            <button class="close-btn" onclick="document.getElementById('toc-sidebar').classList.remove('open')">✕</button>
        </div>
        <ul class="toc-list">
"""
    for sec in sections:
        short_title = sec['title'].split(' | ')[0]
        if "Vocab" in short_title:
            short_title = "↳ " + short_title.split('· ')[-1][:15] + "..."
        toc_html += f"            <li><a href='#{sec['id']}' onclick=\"document.getElementById('toc-sidebar').classList.remove('open')\">{short_title}</a></li>\n"
    toc_html += """        </ul>
    </div>
"""

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Basic English 850: 60 Days - 连读伴学</title>
    <style>
        :root {{ --primary: #4F46E5; --bg: #F3F4F6; --card: #FFFFFF; --text: #1F2937; }}
        body {{ font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; line-height: 1.6; display: flex; flex-direction: row; }}
        header {{ background: linear-gradient(135deg, #4F46E5, #7C3AED); color: white; padding: 3rem 2rem; text-align: center; }}
        header h1 {{ margin: 0; font-size: 2.5rem; }}
        .container {{ max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); scroll-margin-top: 20px; }}
        .nav-link {{ display: inline-block; color: white; margin-top: 1rem; text-decoration: underline; }}
        .header-line {{ font-weight: bold; color: #4B5563; margin-top: 1rem; padding-bottom: 0.5rem; text-align: center; font-size: 1.2rem; border-bottom: 2px solid #E5E7EB; margin-bottom: 1rem; }}
        .speech-line {{ margin: 1rem 0; padding: 1rem; background: #F9FAFB; border-radius: 8px; border-left: 4px solid var(--primary); transition: all 0.2s; }}
        .speech-line.highlight {{ background-color: #E0E7FF; transform: scale(1.02); box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2); border-left: 6px solid var(--primary); }}
        .play-btn {{ margin-left: 10px; cursor: pointer; padding: 4px 10px; border-radius: 6px; border: 1px solid #D1D5DB; background: #FFFFFF; font-size: 0.9rem; transition: background 0.2s; }}
        .play-btn:hover {{ background: #F3F4F6; }}
        .main-audio {{ width: 100%; position: sticky; top: 0; z-index: 100; background: white; padding: 10px 0; border-radius: 8px; margin-bottom: 1rem; }}
        
        #toc-sidebar {{ width: 260px; min-width: 260px; background: #ffffff; height: 100vh; position: sticky; top: 0; overflow-y: auto; box-shadow: 2px 0 8px rgba(0,0,0,0.05); z-index: 1000; transition: transform 0.3s ease; display: flex; flex-direction: column; border-right: 1px solid #E5E7EB; }}
        .toc-header {{ padding: 1.2rem; background: var(--bg); color: var(--text); display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #E5E7EB; }}
        .toc-header h3 {{ margin: 0; font-size: 1.2rem; }}
        .close-btn {{ background: none; border: none; color: var(--text); font-size: 1.5rem; cursor: pointer; display: none; }}
        .toc-list {{ list-style: none; padding: 0; margin: 0; }}
        .toc-list li {{ border-bottom: 1px solid #F9FAFB; }}
        .toc-list a {{ display: block; padding: 0.8rem 1.2rem; color: #4B5563; text-decoration: none; font-size: 0.95rem; transition: background 0.2s; }}
        .toc-list a:hover {{ background: #F3F4F6; color: var(--primary); }}
        #mobile-menu-btn {{ position: fixed; bottom: 20px; left: 20px; background: var(--primary); color: white; padding: 12px 20px; border-radius: 99px; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4); cursor: pointer; z-index: 999; display: none; font-weight: bold; }}
        .main-content {{ flex: 1; width: calc(100% - 260px); }}
        @media (max-width: 900px) {{
            #toc-sidebar {{ position: fixed; transform: translateX(-100%); box-shadow: 2px 0 20px rgba(0,0,0,0.2); }}
            #toc-sidebar.open {{ transform: translateX(0); }}
            .close-btn {{ display: block; }}
            .main-content {{ width: 100%; margin-left: 0; }}
            #mobile-menu-btn {{ display: block; }}
            body {{ display: block; }}
        }}
    </style>
    <script>
        function playShadowing(btn, start, end) {{
            const card = btn.closest('.card');
            const audio = card.querySelector('.main-audio');
            if (!audio) return;
            
            // Apply 0.5s offset backwards to prevent cutoff
            const adjustedStart = Math.max(0, start - 0.5);
            const adjustedEnd = end + 0.2;
            
            audio.currentTime = adjustedStart;
            audio.play();
            
            const checkTime = () => {{
                if (audio.currentTime >= adjustedEnd) {{
                    audio.pause();
                    audio.removeEventListener('timeupdate', checkTime);
                }}
            }};
            audio.removeEventListener('timeupdate', checkTime);
            audio.addEventListener('timeupdate', checkTime);
        }}

        document.addEventListener("DOMContentLoaded", () => {{
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                const audio = card.querySelector('.main-audio');
                if (!audio) return;
                
                const lines = card.querySelectorAll('.speech-line');
                const segments = [];
                lines.forEach(line => {{
                    const btn = line.querySelector('.play-btn');
                    if (btn) {{
                        const match = btn.getAttribute('onclick').match(/playShadowing\\(this,\\s*([\\d.]+),\\s*([\\d.]+)\\)/);
                        if (match) {{
                            segments.push({{
                                element: line,
                                start: parseFloat(match[1]),
                                end: parseFloat(match[2])
                            }});
                        }}
                    }}
                }});

                audio.addEventListener('timeupdate', () => {{
                    const t = audio.currentTime;
                    segments.forEach(seg => {{
                        if (t >= seg.start && t < seg.end) {{
                            if (!seg.element.classList.contains('highlight')) {{
                                seg.element.classList.add('highlight');
                                seg.element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                            }}
                        }} else {{
                            seg.element.classList.remove('highlight');
                        }}
                    }});
                }});
            }});
        }});
    </script>
</head>
<body>
{toc_html}
    <div class='main-content'>
        <header>
            <h1>Basic English 850: 60 Days</h1>
            <a href="index.html" class="nav-link">← 返回主页 (Back to Home)</a>
        </header>
        <div class="container">
"""
    
    # Create dir for audio
    os.makedirs('60days_audio', exist_ok=True)
    
    for sec in sections:
        title = sec['title']
        sec_id = sec['id']
        blocks = sec['blocks']
        print(f"Generating audio for {title} ({sec_id})...")
        
        mp3_out = f"60days_audio/{sec_id}.mp3"
        
        html_out += f"        <div class='card' id='{sec_id}'>\n"
        html_out += f"            <div class='header-line'>{title}</div>\n"
        html_out += f"            <audio controls class='main-audio'>\n"
        html_out += f"                <source src='{mp3_out}' type='audio/mpeg'>\n"
        html_out += f"            </audio>\n"
        
        # Audio generation loop
        temp_files = []
        current_time_offset = 0.0
        
        for block in blocks:
            voice = "en-US-AriaNeural" if block['speaker'] == "Aria" else "en-US-AndrewNeural"
            
            tmp_mp3 = tempfile.mktemp(suffix=".mp3")
            tmp_vtt = tempfile.mktemp(suffix=".vtt")
            tmp_wav = tempfile.mktemp(suffix=".wav")
            temp_files.extend([tmp_mp3, tmp_vtt, tmp_wav])
            
            # The text to synthesize
            tts_text = block['en']
            
            cmd = ["edge-tts", "--voice", voice, "--text", tts_text, "--write-media", tmp_mp3, "--write-subtitles", tmp_vtt]
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    subprocess.run(["ffmpeg", "-y", "-i", tmp_mp3, tmp_wav], check=True, capture_output=True)
                    time.sleep(0.1)
                    break
                except Exception as e:
                    print(f"TTS Error: {e}")
                    time.sleep(1)
            
            segs = parse_vtt(tmp_vtt, current_time_offset)
            # Find exact start and end for the WHOLE block because we map 1 block = 1 sentence mostly
            if segs:
                block['start'] = segs[0]['start']
                block['end'] = segs[-1]['end']
            else:
                block['start'] = current_time_offset
                block['end'] = current_time_offset
                
            try:
                duration = get_mp3_duration(tmp_wav)
                current_time_offset += duration
            except:
                if segs:
                    current_time_offset = segs[-1]['end']
                    
            # Generate HTML for block
            en_clean = block['en'].replace("'", "&apos;").replace('"', "&quot;")
            kk_ipa = sentence_to_kk_linked(block['en'])
            speaker_label = f"<strong>{block['speaker']}:</strong> " if not block.get('is_word') else "<strong>Word:</strong> "
            
            html_out += f"            <div class='speech-line'>{speaker_label}{en_clean} <button class='play-btn' onclick=\"playShadowing(this, {block['start']}, {block['end']})\">🎵 播放本句</button><br><span style='font-size: 0.8em; color: #10B981; display: block; margin-top: 2px; font-family: monospace;'>/ {kk_ipa} /</span><span style='font-size: 0.85em; color: #6B7280; display: block; margin-top: 4px;'>{block['zh']}</span></div>\n"
            
        # Concat all wavs for this section
        if temp_files:
            list_file = tempfile.mktemp(suffix=".txt")
            with open(list_file, 'w') as lf:
                for f in temp_files:
                    if f.endswith('.wav'):
                        lf.write(f"file '{f}'\n")
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-b:a", "128k", mp3_out], check=True, capture_output=True)
            
        for f in temp_files:
            if os.path.exists(f): os.remove(f)
            
        html_out += "        </div>\n" # end card
        
    html_out += """    </div>
</body>
</html>"""

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_out)
    print(f"Finished generating {output_html}")

if __name__ == "__main__":
    process_60days("/Users/langu/Desktop/BE850_60Days_Full.txt", "special_60days.html")
