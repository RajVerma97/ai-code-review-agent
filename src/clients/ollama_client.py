import ollama


class OllamaClient:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        )
        print(response)
        return response["message"]["content"]


# Singleton instance (optional but convenient)
_llm_client_instance = None


def get_llm_client(model_name: str = "llama3.2") -> OllamaClient:
    """Get or create LLM client singleton"""
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = OllamaClient(model_name=model_name)
    return _llm_client_instance
