import gupy
import rag


def test_para_card_mapeia_campos_e_descarta_invalidos():
    c = gupy.para_card({"id": 12, "name": " Analista de Dados ", "careerPageName": "Afya",
                        "workplaceType": "remote", "publishedDate": "2026-09-28T10:00:00Z",
                        "applicationDeadline": "2026-11-23T00:00:00Z"})
    assert c["id"] == "12" and c["titulo"] == "Analista de Dados"
    assert c["local"] == "Remoto" and c["publicada"] == "2026-09-28" and c["prazo"] == "2026-11-23"
    assert gupy.para_card({"name": "sem id"}) is None


def test_limpar_texto_remove_html_e_entidades():
    assert gupy.limpar_texto("<p>SQL&nbsp;e  <b>Power&nbsp;BI</b></p>") == "SQL e Power BI"


def test_trechos_com_sobreposicao_cobrem_todo_o_texto():
    palavras = [f"p{i}" for i in range(200)]
    trechos = rag.quebrar_em_trechos(" ".join(palavras), tamanho=80, sobreposicao=15)
    assert all(len(t.split()) <= 80 for t in trechos)
    assert trechos[0].split()[0] == "p0" and trechos[-1].split()[-1] == "p199"
    # a sobreposição repete as 15 últimas palavras do trecho anterior
    assert trechos[1].split()[:15] == trechos[0].split()[-15:]


def test_texto_curto_vira_um_trecho_e_vazio_nenhum():
    assert rag.quebrar_em_trechos("SQL Power BI dbt") == ["SQL Power BI dbt"]
    assert rag.quebrar_em_trechos("   ") == []
