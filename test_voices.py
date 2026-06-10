import re
import tempfile
import subprocess
import os

def generate_voice_demo(text, output_mp3, female_voice, male_voice):
    print(f"Generating demo {output_mp3} with {female_voice} and {male_voice}...")
    blocks = re.split(r'\[(Aria|Guy)\]', text)
    temp_files = []
    
    try:
        for i in range(1, len(blocks), 2):
            speaker = blocks[i].strip()
            speech = blocks[i+1].strip()
            
            if not speech:
                continue
                
            voice = female_voice if speaker == "Aria" else male_voice
            
            tmp_mp3 = tempfile.mktemp(suffix=".mp3")
            temp_files.append(tmp_mp3)
            
            cmd = ["edge-tts", "--voice", voice, "--text", speech, "--write-media", tmp_mp3]
            subprocess.run(cmd, check=True)
            
        if temp_files:
            with open(output_mp3, 'wb') as outfile:
                for f in temp_files:
                    with open(f, 'rb') as infile:
                        outfile.write(infile.read())
            print(f"Demo {output_mp3} complete.")
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    with open("editions/2026-06-09_Evening/audio_script.txt", "r") as f:
        text = f.read()
    
    generate_voice_demo(text, "editions/2026-06-09_Evening/Evening_Demo_Emma_Andrew.mp3", "en-US-EmmaNeural", "en-US-AndrewNeural")
    generate_voice_demo(text, "editions/2026-06-09_Evening/Evening_Demo_Jenny_Christopher.mp3", "en-US-JennyNeural", "en-US-ChristopherNeural")
