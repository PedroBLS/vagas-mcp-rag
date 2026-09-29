-- Vagas da Gupy com embeddings para busca semântica (RAG) usando pgvector.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS vagas;

CREATE TABLE IF NOT EXISTS vagas.vagas (
    id          TEXT PRIMARY KEY,         -- id da vaga na Gupy
    titulo      TEXT NOT NULL,
    empresa     TEXT,
    local       TEXT,
    modelo      TEXT,                     -- remote | hybrid | on-site
    publicada   DATE,
    prazo       DATE,
    url         TEXT,
    descricao   TEXT,
    indexada_em TIMESTAMP NOT NULL DEFAULT now()
);

-- A descrição é quebrada em trechos: o modelo de embedding só lê ~128 tokens por vez.
CREATE TABLE IF NOT EXISTS vagas.trechos (
    vaga_id   TEXT NOT NULL REFERENCES vagas.vagas (id) ON DELETE CASCADE,
    ordem     INT  NOT NULL,
    texto     TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    PRIMARY KEY (vaga_id, ordem)
);

-- Índice HNSW para busca por similaridade de cosseno.
CREATE INDEX IF NOT EXISTS ix_trechos_embedding
    ON vagas.trechos USING hnsw (embedding vector_cosine_ops);
