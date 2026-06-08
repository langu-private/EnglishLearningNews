#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Replace with your actual LLM API key and configuration
# For example, using DeepSeek or OpenAI:
API_KEY="your-api-key-here"
BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL="gemini-3.1-pro"

# Replace with your GitHub Pages URL
GITHUB_URL="https://langu-private.github.io/EnglishLearningNews"

echo "Running Evening Edition Workflow..."
python generate_podcast.py --edition Evening --api-key "$API_KEY" --base-url "$BASE_URL" --model "$MODEL" --github-url "$GITHUB_URL"

echo "Workflow complete. Check the 'editions' folder."

echo "Syncing to GitHub Pages..."
git add .
git commit -m "Auto-update Evening Edition: $(date)"
git push origin main
echo "GitHub Pages sync complete!"
