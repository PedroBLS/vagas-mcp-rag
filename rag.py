"""Indexação e busca semântica de vagas (RAG) com fastembed + pgvector."""
import os
from functools import lru_cache
from pathlib import Path

import psycopg
from dotenv import load_dotenv

import gupy

BASE = Path(__file__).resolve().parent
MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 384 dim, bom em português
PALAVRAS_POR_TRECHO = 80  # o modelo lê ~128 tokens; 80 palavras em PT cabem com folga


def quebrar_em_trechos(texto: str, tamanho: int = PALAVRAS_POR_TRECHO, sobreposicao: int = 15) -> list[str]:
    """Janelas de palavras com sobreposição, para não cortar um requisito no meio."""
    palavras = texto.split()
    if not palavras:
        return []
    passo = tamanho - sobreposicao
    return [" ".join(palavras[i:i + tamanho]) for i in range(0, max(len(palavras) - sobreposicao, 1), passo)]


@lru_cache(maxsize=1)
def _modelo():
    from fastembed import TextEmbedding  # import tardio: o modelo (~220 MB) só carrega quando usado
    cache = BASE / ".cache"
    # Com o modelo já baixado, não consulta o Hugging Face a cada início (evita rede e avisos de antivírus).
    ja_baixado = any(cache.glob("models--*/snapshots/*/tokenizer.json"))
    return TextEmbedding(MODELO, cache_dir=str(cache), local_files_only=ja_baixado)


def embed(textos: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _modelo().embed(textos)]


def _vetor(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def conectar():
    load_dotenv(BASE / ".env")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Defina DATABASE_URL no .env (veja .env.example).")
    return psycopg.connect(url)


def criar_schema():
    with conectar() as c:
        c.execute((BASE / "schema.sql").read_text(encoding="utf-8"))


def indexar(termo: str, cidade: str | None = None, modelo: str | None = None, limite: int = 20) -> dict:
    """Busca vagas na Gupy, baixa a descrição completa e grava trechos + embeddings."""
    criar_schema()
    vagas = [v for c in gupy.buscar(termo, cidade, modelo, limite) if (v := gupy.detalhe(c["id"]))]
    trechos_total = 0
    with conectar() as c:
        for v in vagas:
            trechos = quebrar_em_trechos(f"{v['titulo']}. {v['descricao']}")
            if not trechos:
                continue
            c.execute(
                """INSERT INTO vagas.vagas (id, titulo, empresa, local, modelo, publicada, prazo, url, descricao)
                   VALUES (%(id)s, %(titulo)s, %(empresa)s, %(local)s, %(modelo)s, %(publicada)s, %(prazo)s,
                           %(url)s, %(descricao)s)
                   ON CONFLICT (id) DO UPDATE SET descricao = EXCLUDED.descricao, prazo = EXCLUDED.prazo,
                       indexada_em = now()""", v)
            c.execute("DELETE FROM vagas.trechos WHERE vaga_id = %s", (v["id"],))
            with c.cursor() as cur:
                cur.executemany(
                    "INSERT INTO vagas.trechos (vaga_id, ordem, texto, embedding) VALUES (%s, %s, %s, %s::vector)",
                    [(v["id"], i, t, _vetor(e)) for i, (t, e) in enumerate(zip(trechos, embed(trechos)))])
            trechos_total += len(trechos)
    return {"vagas_indexadas": len(vagas), "trechos": trechos_total}


def parecidas(texto: str, n: int = 5, somente_remoto: bool = False) -> list[dict]:
    """Quebra o texto (ex.: um CV) em trechos e, para cada vaga, guarda o trecho mais parecido.

    Nota da vaga = maior similaridade de cosseno entre qualquer trecho do texto e qualquer trecho da vaga.
    """
    consultas = quebrar_em_trechos(texto) or [texto]
    melhores: dict[str, dict] = {}
    filtro = "AND v.modelo = 'remote'" if somente_remoto else ""
    with conectar() as c, c.cursor() as cur:
        for vetor in embed(consultas):
            cur.execute(f"""
                SELECT v.id, v.titulo, v.empresa, v.local, v.modelo, v.url, v.prazo, t.texto,
                       1 - (t.embedding <=> %s::vector) AS similaridade
                FROM vagas.trechos t JOIN vagas.vagas v ON v.id = t.vaga_id
                WHERE true {filtro}
                ORDER BY t.embedding <=> %s::vector
                LIMIT 50""", (_vetor(vetor), _vetor(vetor)))
            for id_, titulo, empresa, local, modelo, url, prazo, trecho, sim in cur.fetchall():
                if id_ not in melhores or sim > melhores[id_]["similaridade"]:
                    melhores[id_] = {"id": id_, "titulo": titulo, "empresa": empresa, "local": local,
                                     "modelo": modelo, "url": url, "prazo": str(prazo) if prazo else None,
                                     "similaridade": round(float(sim), 3), "trecho_mais_parecido": trecho}
    return sorted(melhores.values(), key=lambda x: x["similaridade"], reverse=True)[:n]
