"""Cliente mínimo da API pública da Gupy (a mesma que portal.gupy.io usa)."""
import html
import re
import time

import requests

SEARCH_URL = "https://portal.gupy.io/api/job-search/jobs"
DETAIL_URL = "https://employability-portal.gupy.io/api/v1/jobs"


def _get(url: str, params: dict | None = None, tentativas: int = 5):
    espera = 1
    for tentativa in range(tentativas):
        try:
            r = requests.get(url, params=params, timeout=30,
                             headers={"User-Agent": "vagas-mcp-rag/1.0", "Accept": "application/json"})
            if r.status_code == 404:
                return None
            if r.status_code < 500 and r.status_code != 429:
                r.raise_for_status()
                return r.json()
        except (requests.Timeout, requests.ConnectionError):
            pass
        if tentativa == tentativas - 1:
            raise RuntimeError(f"Gupy não respondeu após {tentativas} tentativas: {url}")
        time.sleep(espera)
        espera = min(espera * 2, 16)


def para_card(r: dict):
    """Registro da API -> dicionário enxuto. None se faltar id ou título."""
    if not r or r.get("id") is None or not r.get("name"):
        return None
    local = ", ".join(x for x in (r.get("city"), r.get("state")) if x) or (
        "Remoto" if r.get("workplaceType") == "remote" else None)
    return {
        "id": str(r["id"]),
        "titulo": r["name"].strip(),
        "empresa": r.get("careerPageName"),
        "local": local,
        "modelo": r.get("workplaceType"),
        "publicada": (r.get("publishedDate") or "")[:10] or None,
        "prazo": (r.get("applicationDeadline") or "")[:10] or None,
        "url": r.get("jobUrl") or f"https://portal.gupy.io/job/{r['id']}",
    }


def limpar_texto(s: str | None) -> str:
    """Descrições da Gupy vêm com entidades HTML e espaços repetidos."""
    if not s:
        return ""
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).strip()


def buscar(termo: str, cidade: str | None = None, modelo: str | None = None, limite: int = 20) -> list[dict]:
    params = {"jobName": termo, "limit": min(limite, 100), "offset": 0}
    if cidade:
        params["city"] = cidade
    if modelo:
        params["workplaceType"] = modelo
    dados = _get(SEARCH_URL, params) or {}
    return [c for r in dados.get("data") or [] if (c := para_card(r))]


def detalhe(vaga_id: str):
    r = _get(f"{DETAIL_URL}/{vaga_id}")
    if not r:
        return None
    card = para_card(r)
    if card:
        card["descricao"] = limpar_texto(r.get("description"))
    return card
