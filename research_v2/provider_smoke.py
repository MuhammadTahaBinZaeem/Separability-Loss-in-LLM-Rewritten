"""Tiny non-study capability checks; never choose models by attribution outcomes."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit

from .credentials import read_env
from .provider_probe import request_json
from .io import OUT,write_json


def smoke(provider,values,requested_model=None):
    prompt='Return JSON with exactly two strings: request_id="connectivity-only" and rewritten_text="The door was open."'
    if provider=="gemini":
        model=requested_model or "gemini-2.5-flash"
        payload={"contents":[{"role":"user","parts":[{"text":prompt}]}],
                 "generationConfig":{"temperature":0.2,"maxOutputTokens":128,"responseMimeType":"application/json","thinkingConfig":{"thinkingBudget":0}}}
        if model.startswith("gemini-3"):
            payload["generationConfig"]["thinkingConfig"]={"thinkingLevel":"minimal"}
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers={"x-goog-api-key":values["gemchat"]}
    else:
        model=requested_model or values.get("AZURE_MODEL_OR_DEPLOYMENT","gpt-4.1-mini")
        parts=urlsplit(values["open_url"])
        if parts.scheme!="https" or not (parts.hostname or "").endswith(".openai.azure.com"):
            raise ValueError("Unexpected Azure endpoint")
        url=f"https://{parts.hostname}/openai/v1/responses"
        headers={"api-key":values["open_key"]}
        payload={"model":model,"input":prompt,"max_output_tokens":128,"temperature":0.2,"store":False,"text":{"format":{"type":"json_object"}}}
    status,response=request_json(url,headers,payload)
    record={"provider":provider,"requested_model":model,"checked_utc":datetime.now(timezone.utc).isoformat(),
            "primary_experiment":False,"purpose":"connection_and_format_only","request":payload,"status":status,"response":response}
    safe_model=model.replace("/","_").replace("\\","_")
    write_json(OUT / f"access/{provider}_{safe_model}_smoke.json",record)
    print({"provider":provider,"requested_model":model,"status":status,"returned_model":response.get("model",response.get("modelVersion",""))},flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file",type=Path,required=True)
    parser.add_argument("--provider",choices=["azure","gemini"])
    parser.add_argument("--model")
    args=parser.parse_args()
    values=read_env(args.env_file)
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda provider:smoke(provider,values,args.model),[args.provider] if args.provider else ["azure","gemini"]))


if __name__=="__main__":
    main()
