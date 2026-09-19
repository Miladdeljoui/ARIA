import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:1.7b"


def ask_aria(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


if __name__ == "__main__":
    answer = ask_aria("سلام آریا. خودت را در یک جمله معرفی کن.")
    print(answer)
