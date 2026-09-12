import os
import requests

# Read .env file manually
env_path = os.path.join(os.path.dirname(__file__), ".env")
api_key = None

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('GROQ_API_KEY='):
                api_key = line.strip().split('=', 1)[1]
                break

if not api_key:
    print("Error: GROQ_API_KEY not found in .env file")
    exit(1)

url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json()
        print("Available Groq Models:")
        print("=" * 50)
        for model in models.get("data", []):
            print(f"ID: {model['id']}")
            print(f"Created: {model['created']}")
            print(f"Owned by: {model['owned_by']}")
            print("-" * 30)
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
except Exception as e:
    print(f"Error: {e}")
