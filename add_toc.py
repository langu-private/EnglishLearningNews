import os
import re

def add_toc(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if "/* TOC Styles */" in content:
        print("TOC already added.")
        return

    # Find all cards to build TOC
    pattern = re.compile(r"<div class='card' id='([^']+)'>\s*<div class='header-line'>([^<]+)</div>")
    matches = pattern.findall(content)

    toc_html = """
    <div id="mobile-menu-btn" onclick="document.getElementById('toc-sidebar').classList.toggle('open')">☰ 课程目录</div>
    <div id="toc-sidebar">
        <div class="toc-header">
            <h3>📖 目录</h3>
            <button class="close-btn" onclick="document.getElementById('toc-sidebar').classList.remove('open')">✕</button>
        </div>
        <ul class="toc-list">
"""
    for sec_id, title in matches:
        short_title = title.split(' | ')[0]
        if "Vocab" in short_title:
            short_title = "↳ " + short_title.split('· ')[-1][:15] + "..."
        toc_html += f"            <li><a href='#{sec_id}' onclick=\"document.getElementById('toc-sidebar').classList.remove('open')\">{short_title}</a></li>\n"
    toc_html += """        </ul>
    </div>
"""

    css_addition = """
        /* TOC Styles */
        body { display: flex; flex-direction: row; }
        #toc-sidebar {
            width: 260px;
            min-width: 260px;
            background: #ffffff;
            height: 100vh;
            position: sticky;
            top: 0;
            overflow-y: auto;
            box-shadow: 2px 0 8px rgba(0,0,0,0.05);
            z-index: 1000;
            transition: transform 0.3s ease;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #E5E7EB;
        }
        .toc-header {
            padding: 1.2rem;
            background: var(--bg);
            color: var(--text);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #E5E7EB;
        }
        .toc-header h3 { margin: 0; font-size: 1.2rem; }
        .close-btn {
            background: none; border: none; color: var(--text); font-size: 1.5rem; cursor: pointer; display: none;
        }
        .toc-list {
            list-style: none; padding: 0; margin: 0;
        }
        .toc-list li {
            border-bottom: 1px solid #F9FAFB;
        }
        .toc-list a {
            display: block; padding: 0.8rem 1.2rem; color: #4B5563; text-decoration: none; font-size: 0.95rem; transition: background 0.2s;
        }
        .toc-list a:hover {
            background: #F3F4F6; color: var(--primary);
        }
        #mobile-menu-btn {
            position: fixed; bottom: 20px; left: 20px; background: var(--primary); color: white; padding: 12px 20px; border-radius: 99px; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4); cursor: pointer; z-index: 999; display: none; font-weight: bold;
        }
        .main-content {
            flex: 1; width: calc(100% - 260px);
        }

        /* Mobile adaptation */
        @media (max-width: 900px) {
            #toc-sidebar { 
                position: fixed; 
                transform: translateX(-100%); 
                box-shadow: 2px 0 20px rgba(0,0,0,0.2); 
            }
            #toc-sidebar.open { transform: translateX(0); }
            .close-btn { display: block; }
            .main-content { width: 100%; margin-left: 0; }
            #mobile-menu-btn { display: block; }
            body { display: block; }
        }
"""

    content = content.replace("    </style>", css_addition + "    </style>")
    content = content.replace("<body>\n    <header>", f"<body>\n{toc_html}\n    <div class='main-content'>\n    <header>")
    content = content.replace("</body>", "    </div>\n</body>")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Injected TOC into {filepath}")

add_toc('special_60days.html')
