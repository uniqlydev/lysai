import os, json 
from core.llm_client import get_llm


def llm_json(system: str, user: str) -> dict:
    """
    Ask LLm to respond in JSON only. If it fails, we try to recover
    """

    model = get_llm()

    resp = model.generate(user)

    text = resp.text.strip() or "{}"

    try:
        return json.loads(text)
    except Exception:
        import re 

        m = re.search(r"(\{.*\})", text, re.S)

        if m: 
            m = re.search(r"(\{.*\})", text, re.S)
            
            try: 
                return json.loads(m.group(0))
            except Exception:
                pass

        return {}
