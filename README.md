# Assistente de Vagas com MCP + RAG

Servidor **MCP** (Model Context Protocol) em Python que dá ao Claude ferramentas para buscar vagas na Gupy e encontrar as vagas **mais parecidas com um currículo**, por busca semântica (**RAG**) com embeddings no **PostgreSQL + pgvector** (Supabase).

```
Claude Code / Claude Desktop ──MCP──► server.py (MCPServer)
                                        ├─ buscar_vagas      → API pública da Gupy
                                        ├─ detalhe_vaga      → descrição completa
                                        ├─ indexar_vagas     → trechos + embeddings → pgvector
                                        └─ vagas_parecidas   → busca por similaridade (cosseno)
```

**Divisão de papéis no RAG:**
- O servidor faz a parte de **recuperação**: encontra as vagas e os trechos mais parecidos com o texto do CV.
- O **Claude**, como cliente MCP, faz a parte de **geração**: explica por que cada vaga combina e quais são as lacunas.

Por isso o projeto não precisa de chave de API de LLM.

## Como funciona o RAG

1. **Indexação:** `indexar_vagas` busca vagas na Gupy, baixa a descrição completa e a quebra em **trechos de 80 palavras com sobreposição de 15**. O modelo de embedding lê cerca de 128 tokens por vez, e a sobreposição evita cortar um requisito no meio.
2. **Embeddings:** gerados **localmente** com `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões, bom em português), via `fastembed` com ONNX, sem PyTorch e sem custo por chamada.
3. **Armazenamento:** a tabela `vagas.trechos` guarda o `vector(384)`, com um índice **HNSW** por distância de cosseno (`schema.sql`).
4. **Busca:**
   - o texto do CV também é quebrado em trechos;
   - para cada trecho, o pgvector devolve os trechos de vaga mais próximos;
   - a nota de cada vaga é a **maior similaridade** entre qualquer par de trechos, e o resultado inclui o **trecho da vaga que mais combinou**, que é o que o Claude usa para explicar o encaixe.

### Exemplo real (29/09/2026)

Resultado com 21 vagas indexadas (126 trechos) e o texto *"Formado em Administração, pós em Ciência de Dados. SQL e PostgreSQL, Power BI com DAX, dbt com testes de qualidade, Python com Pandas…"*:

| Similaridade | Vaga | Trecho que mais combinou |
|---|---|---|
| 0,695 | Analista de Dados Pleno/Sênior | "consultas SQL complexas e eficientes para transformação, validação e análise…" |
| 0,674 | Banco de talentos: Analista de Dados | "…em SQL. Experiência com análise, tratamento e interpretação de dados…" |
| 0,653 | Analista de Dados Júnior | "Experiência em análise de dados e gestão de KPIs…" |
| 0,650 | Analista de Dados Júnior | "O QUE BUSCAMOS…" |

As vagas de suporte técnico indexadas no mesmo banco ficaram fora do top, como esperado para um CV de dados.

## Como executar

```bash
python -m venv .venv                 # Python 3.11+ (fastembed/onnxruntime)
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env               # e preencha DATABASE_URL (Supabase com pgvector)
pytest                               # testes offline (sem rede)
```

Registrar o servidor no **Claude Code**:
```bash
claude mcp add vagas -- C:\caminho\vagas-mcp-rag\.venv\Scripts\python.exe C:\caminho\vagas-mcp-rag\server.py
```

Exemplos de pedido ao Claude:
- "Indexe vagas remotas de analista de dados."
- "Quais vagas combinam com este resumo do meu CV? Explique o encaixe e as lacunas."

## Decisões e limites

- **Modelo local em vez de API de embeddings:** não tem custo nem chave e roda offline depois do primeiro download (cerca de 220 MB). A qualidade é menor que a dos modelos grandes, mas suficiente para ordenar vagas.
- **Máximo por vaga, em vez de média:** uma vaga longa não é penalizada por ter muitos trechos genéricos (benefícios, cultura).
- **Limite:** similaridade semântica não é a mesma coisa que requisito atendido. Por isso a ferramenta devolve o trecho, e o Claude confere o encaixe de fato.

## Tecnologias

Python, MCP (SDK oficial, `MCPServer`), fastembed (ONNX), PostgreSQL + pgvector (Supabase), psycopg, pytest.

Desenvolvido por Pedro Brandão Leal dos Santos, com apoio do **Claude Code** na escrita do código.
