"""Native provider adapters; normalized views never replace retained raw responses."""
from __future__ import annotations
from urllib.parse import urlsplit


def make_payload(config: dict, plan: dict, system: str, user: str) -> dict:
    api=config.get("api","groq_chat")
    schema={"type":"object","properties":{"request_id":{"type":"string"},"rewritten_text":{"type":"string"}},
            "required":["request_id","rewritten_text"],"additionalProperties":False}
    if api=="gemini_native":
        return {"systemInstruction":{"parts":[{"text":system}]},
                "contents":[{"role":"user","parts":[{"text":user}]}],
                "generationConfig":{"temperature":plan["temperature"],"topP":plan["top_p"],
                   "maxOutputTokens":plan["max_completion_tokens"],"responseMimeType":"application/json",
                   "responseJsonSchema":schema,"thinkingConfig":{"thinkingLevel":config["thinking_level"]}}}
    if api=="azure_responses":
        payload={"model":config["model"],"instructions":system,"input":user,"temperature":plan["temperature"],
                "top_p":plan["top_p"],"max_output_tokens":plan["max_completion_tokens"],"store":False,
                "text":{"format":{"type":"json_schema","name":"controlled_rewrite","schema":schema,"strict":True}}}
        if "reasoning_effort" in config:
            payload["reasoning"]={"effort":config["reasoning_effort"]}
        return payload
    payload={"model":config["model"],"messages":[{"role":"system","content":system},{"role":"user","content":user}],
             "temperature":plan["temperature"],"top_p":plan["top_p"],"max_completion_tokens":plan["max_completion_tokens"],
             "response_format":{"type":"json_object"}}
    for option in ("reasoning_effort","reasoning_format"):
        if option in config:
            payload[option]=config[option]
    return payload


def connection(config: dict, values: dict) -> tuple[str,dict]:
    key=values.get(config["key_env"],"")
    if not key:
        raise ValueError(f"Missing credential variable {config['key_env']}")
    api=config.get("api","groq_chat")
    if api=="gemini_native":
        return f"https://generativelanguage.googleapis.com/v1beta/models/{config['model']}:generateContent",{"x-goog-api-key":key}
    if api=="azure_responses":
        parts=urlsplit(values.get(config["endpoint_env"],""))
        if parts.scheme!="https" or not (parts.hostname or "").endswith(".openai.azure.com") or parts.username or parts.password:
            raise ValueError("Azure endpoint must be the user's HTTPS Azure OpenAI resource")
        return f"https://{parts.hostname}/openai/v1/responses",{"api-key":key}
    if api=="groq_chat":
        return "https://api.groq.com/openai/v1/chat/completions",{"Authorization":f"Bearer {key}"}
    raise ValueError("Unsupported provider API")


def response_view(request: dict, response: dict) -> dict:
    api=request.get("api","groq_chat")
    if api=="gemini_native":
        candidate=(response.get("candidates") or [{}])[0]
        content="".join(p.get("text","") for p in candidate.get("content",{}).get("parts",[]) if not p.get("thought"))
        finish=candidate.get("finishReason","")
        return {"content":content,"finish_reason":"stop" if finish=="STOP" else finish,
                "native_finish_reason":finish,"model":response.get("modelVersion",""),"id":response.get("responseId","")}
    if api=="azure_responses":
        content="".join(p.get("text","") for item in response.get("output",[]) if item.get("type")=="message"
                        for p in item.get("content",[]) if p.get("type")=="output_text")
        finish=response.get("status","")
        return {"content":content,"finish_reason":"stop" if finish=="completed" else finish,
                "native_finish_reason":finish,"model":response.get("model",""),"id":response.get("id","")}
    choice=(response.get("choices") or [{}])[0]
    return {"content":choice.get("message",{}).get("content") or "","finish_reason":choice.get("finish_reason", ""),
            "native_finish_reason":choice.get("finish_reason",""),"model":response.get("model",""),"id":response.get("id","")}
