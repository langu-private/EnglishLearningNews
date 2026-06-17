import os
import sys
import argparse
from openai import OpenAI
from generate_podcast import generate_learning_document, update_index_html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", default="gemini-3.5-flash")
    parser.add_argument("--base-url", default="https://generativelanguage.googleapis.com/v1beta/openai/")
    args = parser.parse_args()

    editions_dir = "editions"
    folders = sorted(os.listdir(editions_dir), reverse=True)
    latest_folder = folders[0]
    folder_path = os.path.join(editions_dir, latest_folder)
    
    script_path = os.path.join(folder_path, "audio_script.txt")
    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read()
        
    print(f"Generating learning doc for {latest_folder}...")
    
    # Simple retry block just in case of 503 since we just want it to succeed once
    client = OpenAI(api_key=args.api_key, base_url=args.base_url, timeout=180.0)
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
    doc_md = ""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            doc_md = response.choices[0].message.content
            break
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            import time
            time.sleep(30)
            
    if not doc_md:
        print("Failed to generate doc. Exiting.")
        sys.exit(1)
        
    doc_path = os.path.join(folder_path, "Learning_Document.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(doc_md)
        
    update_index_html()
    print("Done.")

if __name__ == "__main__":
    main()
