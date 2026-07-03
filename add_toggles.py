import os
import re

def add_toggles(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if "toggleEn()" in content:
        print("Toggles already added.")
        return

    # Patch the speech lines to add classes
    def replacer(match):
        speaker = match.group(1)
        en_text = match.group(2)
        btn_content = match.group(3)
        ipa_style = match.group(4)
        ipa_text = match.group(5)
        zh_style = match.group(6)
        zh_text = match.group(7)
        
        # Add classes to the spans
        ipa_style = "class='ipa-text' style='" + ipa_style + "'"
        zh_style = "class='zh-text' style='" + zh_style + "'"
        
        # Wrap en_text in a span
        en_wrapped = f"<span class='en-text'>{en_text}</span>"
        
        return f"<div class='speech-line'><strong>{speaker}</strong> {en_wrapped} <button class='play-btn'{btn_content}</button><br><span {ipa_style}>{ipa_text}</span><span {zh_style}>{zh_text}</span></div>"

    pattern = re.compile(r"<div class='speech-line'><strong>([^<]+)</strong> (.*?) <button class='play-btn'(.*?)</button><br><span style='(.*?)'>(.*?)</span><span style='(.*?)'>(.*?)</span></div>")
    content = pattern.sub(replacer, content)

    toggle_buttons_html = """
        <div class="control-panel" style="text-align: center; margin-top: 1rem; position: sticky; top: 0; z-index: 101; background: var(--bg); padding: 10px; border-bottom: 1px solid #E5E7EB; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <button id="btn-toggle-en" onclick="toggleEn()" style="padding: 8px 16px; margin: 5px 10px; border-radius: 8px; border: 2px solid #4F46E5; background: white; color: #4F46E5; cursor: pointer; font-weight: bold; transition: all 0.2s;">👀 隐藏英文与音标</button>
            <button id="btn-toggle-zh" onclick="toggleZh()" style="padding: 8px 16px; margin: 5px 10px; border-radius: 8px; border: 2px solid #10B981; background: white; color: #10B981; cursor: pointer; font-weight: bold; transition: all 0.2s;">👀 隐藏中文翻译</button>
        </div>
    """
    
    content = content.replace('<div class="container">', toggle_buttons_html + '\n        <div class="container">')

    js_addition = """
        let enHidden = false;
        let zhHidden = false;
        
        function toggleEn() {
            enHidden = !enHidden;
            if (enHidden) {
                document.body.classList.add('hide-en');
                document.getElementById('btn-toggle-en').innerText = '🙈 显示英文与音标';
                document.getElementById('btn-toggle-en').style.background = '#4F46E5';
                document.getElementById('btn-toggle-en').style.color = 'white';
            } else {
                document.body.classList.remove('hide-en');
                document.getElementById('btn-toggle-en').innerText = '👀 隐藏英文与音标';
                document.getElementById('btn-toggle-en').style.background = 'white';
                document.getElementById('btn-toggle-en').style.color = '#4F46E5';
            }
        }
        
        function toggleZh() {
            zhHidden = !zhHidden;
            if (zhHidden) {
                document.body.classList.add('hide-zh');
                document.getElementById('btn-toggle-zh').innerText = '🙈 显示中文翻译';
                document.getElementById('btn-toggle-zh').style.background = '#10B981';
                document.getElementById('btn-toggle-zh').style.color = 'white';
            } else {
                document.body.classList.remove('hide-zh');
                document.getElementById('btn-toggle-zh').innerText = '👀 隐藏中文翻译';
                document.getElementById('btn-toggle-zh').style.background = 'white';
                document.getElementById('btn-toggle-zh').style.color = '#10B981';
            }
        }
    """
    content = content.replace("document.addEventListener(\"DOMContentLoaded\"", js_addition + "\n        document.addEventListener(\"DOMContentLoaded\"")

    css_addition = """
        body.hide-en .en-text, body.hide-en .ipa-text { filter: blur(6px); opacity: 0.3; transition: all 0.3s; user-select: none; }
        body.hide-en .en-text:hover, body.hide-en .ipa-text:hover { filter: none; opacity: 1; cursor: pointer; }
        body.hide-zh .zh-text { filter: blur(6px); opacity: 0.3; transition: all 0.3s; user-select: none; }
        body.hide-zh .zh-text:hover { filter: none; opacity: 1; cursor: pointer; }
    """
    content = content.replace("</style>", css_addition + "\n    </style>")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Injected toggles into {filepath}")

add_toggles('special_60days.html')
