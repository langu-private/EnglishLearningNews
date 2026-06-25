import os
import re
import eng_to_ipa as ipa

def add_linking(ipa_text):
    vowels = set('aæɑəɛeɪiɒɔʊuʌo')
    consonants = set('pbtdkɡfvθðszʃʒhmnŋlrjw')
    
    words = ipa_text.split()
    if not words:
        return ""
    
    linked = []
    for i in range(len(words)-1):
        w1 = words[i]
        w2 = words[i+1]
        
        has_punctuation = bool(re.search(r'[.,!?;\:]$', w1))
        
        w1_clean = re.sub(r'[^a-zæɑəɛɪɒɔʊʌʒʃθðŋɡ*]', '', w1.lower())
        w2_clean = re.sub(r'[^a-zæɑəɛɪɒɔʊʌʒʃθðŋɡ*]', '', w2.lower())
        
        linked.append(w1)
        
        if w1_clean and w2_clean and not has_punctuation:
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
            
    linked.append(words[-1])
    return "".join(linked).replace(' ‿ ', '‿').replace('‿ ', '‿').replace(' ‿', '‿')

def process_html_add_ipa(html_file):
    if not os.path.exists(html_file):
        return
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to find:
    # <strong>Speaker:</strong> English text <button ...>...</button><br><span style='font-size: 0.85em; color: #6B7280; display: block; margin-top: 4px;'>Chinese text</span>
    
    pattern = re.compile(r"^(.*<div class='speech-line'><strong>[^<]+:</strong>\s*)(.+?)(\s*<button class='play-btn'[^>]*>.*?</button><br>)(<span style='font-size: 0.85em; color: #6B7280; display: block; margin-top: 4px;'>.+?</span></div>.*)$", re.MULTILINE)
    
    def replacer(match):
        prefix = match.group(1)
        en_text = match.group(2)
        mid_suffix = match.group(3)
        zh_span = match.group(4)
        
        clean_text = en_text.replace("&apos;", "'").replace("&quot;", '"').strip()
        ipa_trans = ipa.convert(clean_text)
        linked_ipa = add_linking(ipa_trans)
        
        # check if already added IPA
        if "color: #10B981;" in zh_span or "color: #10B981;" in mid_suffix:
            return match.group(0) # Already added
            
        ipa_span = f"<span style='font-size: 0.8em; color: #10B981; display: block; margin-top: 2px; font-family: monospace;'>/ {linked_ipa} /</span>"
        
        return f"{prefix}{en_text}{mid_suffix}{ipa_span}{zh_span}"
    
    new_content = pattern.sub(replacer, content)
    
    # Also update generate_specials.py behavior for missing translations? No, we just run this script over the HTMLs.
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Injected IPA into {html_file}")

process_html_add_ipa('special_life.html')
process_html_add_ipa('special_travel.html')
