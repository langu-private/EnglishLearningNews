import os
import re
import nltk
from nltk.corpus import cmudict

# Ensure dictionary is downloaded
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
        phones = d[clean_word][0] # use first variant
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
                
        # Preserve original punctuation at the end for the linking logic
        suffix = re.search(r'[^a-z\']*$', word.lower()).group()
        return "".join(result) + suffix
    return word

def sentence_to_kk_linked(sentence):
    words = sentence.split()
    if not words:
        return ""
        
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
    # clean up the output to remove any spaces around the tie
    final_str = "".join(linked)
    final_str = final_str.replace(' ‿ ', '‿').replace('‿ ', '‿').replace(' ‿', '‿')
    return final_str

def update_html_ipa(html_file):
    if not os.path.exists(html_file):
        return
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to match the entire line and extract the English text, and replace the IPA span.
    # Pattern to match a line that already has an IPA span
    pattern = re.compile(r"^(.*<div class='speech-line'><strong>[^<]+:</strong>\s*)(.+?)(\s*<button class='play-btn'[^>]*>.*?</button><br>)<span style='font-size: 0\.8em; color: #10B981; display: block; margin-top: 2px; font-family: monospace;'>/ .+? /</span>(<span style='font-size: 0\.85em; color: #6B7280; display: block; margin-top: 4px;'>.+?</span></div>.*)$", re.MULTILINE)
    
    count = 0
    def replacer(match):
        nonlocal count
        prefix = match.group(1)
        en_text = match.group(2)
        mid_suffix = match.group(3)
        zh_span = match.group(4)
        
        clean_text = en_text.replace("&apos;", "'").replace("&quot;", '"').strip()
        linked_kk = sentence_to_kk_linked(clean_text)
        
        new_ipa_span = f"<span style='font-size: 0.8em; color: #10B981; display: block; margin-top: 2px; font-family: monospace;'>/ {linked_kk} /</span>"
        count += 1
        return f"{prefix}{en_text}{mid_suffix}{new_ipa_span}{zh_span}"
    
    new_content = pattern.sub(replacer, content)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated {count} IPAs in {html_file}")

update_html_ipa('special_life.html')
update_html_ipa('special_travel.html')
