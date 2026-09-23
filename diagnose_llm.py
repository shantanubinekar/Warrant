import os, traceback
from dotenv import load_dotenv

load_dotenv()

print("=== 1. Env vars ===")
key = os.environ.get("GROQ_API_KEY")
model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
print("GROQ_API_KEY set:", bool(key), "len:", len(key) if key else 0)
print("GROQ_MODEL:", model)

print("\n=== 2. groq import ===")
try:
    from groq import Groq
    import groq as groq_pkg
    print("OK — imported from:", groq_pkg.__file__)
except Exception as e:
    print("IMPORT FAILED:", repr(e))
    traceback.print_exc()

print("\n=== 3. Client init + live call ===")
try:
    from groq import Groq
    client = Groq(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say OK"}],
    )
    print("LIVE CALL SUCCEEDED. Response text:", resp.choices[0].message.content)
except Exception as e:
    print("LIVE CALL FAILED:", repr(e))
    traceback.print_exc()
