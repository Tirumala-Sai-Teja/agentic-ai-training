"""
Known working Groq models based on documentation
Based on: https://docs.litellm.ai/docs/providers/groq
"""

AVAILABLE_GROQ_MODELS = [
    # Llama Models
    "groq/llama-3.1-8b-instant",
    "groq/llama-3.3-70b-versatile",
    "groq/llama3-8b-8192",
    "groq/llama3-70b-8192",
    
    # Llama 4 Models
    "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    "groq/meta-llama/llama-guard-4-12b",
    
    # Qwen Models
    "groq/qwen/qwen3-32b",
    "groq/qwen-qwq-32b",
    "groq/qwen-2.5-32b",
    
    # Moonshot AI
    "groq/moonshotai/kimi-k2-instruct-0905",
    
    # OpenAI OSS Models
    "groq/openai/gpt-oss-120b",
    "groq/openai/gpt-oss-20b",
    "groq/openai/gpt-oss-safeguard-20b",
    
    # Other Models
    "groq/gemma2-9b-it",
    "groq/mixtral-8x7b-32768",
    "groq/deepseek-r1-distill-qwen-32b",
    "groq/deepseek-r1-distill-llama-70b",
]

print("Known Available Groq Models:")
print("=" * 60)
for model in AVAILABLE_GROQ_MODELS:
    print(f"• {model}")

print("\nRecommended for basic usage:")
print("• groq/llama-3.1-8b-instant (fast, cost-effective)")
print("• groq/llama-3.3-70b-versatile (more capable)")

print("\nTo use in your agent:")
print('model = LiteLlm(model="groq/llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))')
