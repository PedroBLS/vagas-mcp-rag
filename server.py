"""Servidor MCP: dá ao Claude ferramentas para buscar vagas na Gupy e achar vagas parecidas com um CV (RAG)."""
from mcp.server.mcpserver import MCPServer

import gupy
import rag

mcp = MCPServer("vagas")


@mcp.tool()
def buscar_vagas(termo: str, cidade: str | None = None, modelo: str | None = None, limite: int = 10) -> list[dict]:
    """Busca vagas abertas na Gupy.

    Args:
        termo: cargo ou palavra-chave, ex.: "analista de dados".
        cidade: filtra por cidade, ex.: "Brasília".
        modelo: "remote", "hybrid" ou "on-site".
        limite: quantidade máxima de vagas (até 100).
    """
    return gupy.buscar(termo, cidade, modelo, limite)


@mcp.tool()
def detalhe_vaga(vaga_id: str) -> dict | None:
    """Descrição completa de uma vaga da Gupy pelo id (retornado por buscar_vagas)."""
    return gupy.detalhe(vaga_id)


@mcp.tool()
def indexar_vagas(termo: str, cidade: str | None = None, modelo: str | None = None, limite: int = 20) -> dict:
    """Baixa vagas da Gupy e grava embeddings no banco para a busca semântica.

    Rode antes de vagas_parecidas. Ex.: indexar_vagas("analista de dados", modelo="remote").
    """
    return rag.indexar(termo, cidade, modelo, limite)


@mcp.tool()
def vagas_parecidas(texto: str, n: int = 5, somente_remoto: bool = False) -> list[dict]:
    """Encontra as vagas indexadas mais parecidas com um texto (ex.: resumo do CV).

    Retorna, para cada vaga, a similaridade (0 a 1) e o trecho da descrição que mais combinou,
    para você explicar ao usuário por que a vaga combina e quais lacunas existem.
    """
    return rag.parecidas(texto, n, somente_remoto)


if __name__ == "__main__":
    mcp.run()
