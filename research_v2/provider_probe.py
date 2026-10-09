"""Read-only provider access checks; never print/store credentials or error bodies."""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .credentials import read_env
from .io import OUT, write_json


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def request_json(url: str, headers: dict, payload: dict | None=None) -> tuple[dict,dict]:
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"SeparabilityResearch/2.1",**headers},
                               data=json.dumps(payload).encode() if payload is not None else None)
    if payload is not None:
        req.add_header("Content-Type","application/json")
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=40) as response:
            raw=response.read()
            return {"http_status":response.status,"ok":True},json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw=exc.read()
        try:
            obj=json.loads(raw)
            error=obj.get("error",{})
            code=error.get("code",error.get("status","")) if isinstance(error,dict) else ""
            # Whitelist token-shaped codes; no free-text provider messages/account details.
            safe_code=str(code) if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}",str(code)) else "withheld"
            details=error.get("details",[]) if isinstance(error,dict) else []
            reasons=[d["reason"] for d in details if isinstance(d,dict) and re.fullmatch(r"[A-Z_]{1,80}",str(d.get("reason","")))]
        except (ValueError,AttributeError):
            safe_code="unparsed_error"; reasons=[]
        return {"http_status":exc.code,"ok":False,"error_code":safe_code,"reasons":reasons},{}
    except (urllib.error.URLError,TimeoutError,ValueError):
        return {"ok":False,"error_code":"connection_or_invalid_json"},{}


def probe(name: str, values: dict) -> dict:
    result={"provider":name,"checked_utc":datetime.now(timezone.utc).isoformat(),"read_only":True}
    if name=="featherless":
        key=values.get("FEATHERLESS_API_KEY","")
        if not key:
            return {**result,"ok":False,"reason":"missing_key"}
        status,plan=request_json("https://api.featherless.ai/v1/plan",{"Authorization":f"Bearer {key}"})
        result.update(status)
        if status["ok"]:
            result["plan"]={k:plan[k] for k in ("name","max_context_length","max_model_size","concurrency") if k in plan}
            status,models=request_json("https://api.featherless.ai/v1/models?available_on_current_plan=true&per_page=1000",{"Authorization":f"Bearer {key}"})
            result["catalogue_status"]=status
            result["models"]=[{k:r[k] for k in ("id","context_length","max_completion_tokens","available_on_current_plan","is_gated") if k in r} for r in models.get("data",[])]
    elif name=="azure":
        key=values.get("open_key",values.get("AZURE_API_KEY",""))
        endpoint=values.get("open_url",values.get("AZURE_ENDPOINT",""))
        parts=urllib.parse.urlsplit(endpoint)
        if not key or parts.scheme!="https" or not (parts.hostname or "").endswith((".openai.azure.com",".services.ai.azure.com")) or parts.username or parts.password:
            return {**result,"ok":False,"reason":"missing_key_or_invalid_azure_endpoint"}
        origin=f"https://{parts.hostname}"
        status,data=request_json(origin+"/openai/v1/models",{"api-key":key})
        result.update(status)
        result["endpoint_route"]=parts.path # no account hostname, query, or credential
        result["models"]=[r["id"] for r in data.get("data",[]) if "id" in r]
    elif name=="gemini":
        key=values.get("gemchat",values.get("GEMINI_API_KEY",""))
        if not key:
            return {**result,"ok":False,"reason":"missing_key"}
        status,data=request_json("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",{"x-goog-api-key":key})
        result.update(status)
        result["credential_variable"]="gemchat" if "gemchat" in values else "GEMINI_API_KEY"
        result["models"]=[{k:r[k] for k in ("name","version","supportedGenerationMethods","inputTokenLimit","outputTokenLimit") if k in r} for r in data.get("models",[])]
        result["other_keys_not_tested"]=True
    elif name=="zenodo":
        key=values.get("zenodo_token",values.get("ZENODO_TOKEN",""))
        if not key:
            return {**result,"ok":False,"reason":"missing_token"}
        status,_=request_json("https://zenodo.org/api/deposit/depositions?size=1",{"Authorization":f"Bearer {key}"})
        result.update(status)
        result["write_permissions_verified"]=False
        result["publication_attempted"]=False
    else:
        raise ValueError("Unknown provider")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file",type=Path,required=True)
    args=parser.parse_args()
    values=read_env(args.env_file)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(lambda name:probe(name,values),["azure","featherless","gemini","zenodo"]))
    for result in results:
        write_json(OUT / f"access/{result['provider']}.json",result)
        print(json.dumps({**{k:v for k,v in result.items() if k!="models"},"model_count":len(result.get("models",[]))}))


if __name__=="__main__":
    main()
