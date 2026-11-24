import json
import urllib.request
from datetime import datetime, timezone, timedelta

ARQUIVO_SAIDA = "ofertas_lci.json"

URL_SELIC = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
URL_CDI = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados/ultimos/1?formato=json"


def buscar_taxa_bcb(url, padrao):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
            if dados and "valor" in dados[0]:
                return float(dados[0]["valor"])
    except Exception as erro:
        print(f"Aviso ao consultar BCB ({url}): {erro}")
    return padrao


def main():
    try:
        with open(ARQUIVO_SAIDA, "r", encoding="utf-8") as f:
            dados_anteriores = json.load(f)
    except FileNotFoundError:
        dados_anteriores = {"cdi_anual": 12.0, "selic_anual": 12.0}

    selic = buscar_taxa_bcb(URL_SELIC, dados_anteriores.get("selic_anual", 12.0))
    cdi = buscar_taxa_bcb(URL_CDI, dados_anteriores.get("cdi_anual", 12.0))

    faixas_mercado = [
        {
            "emissor": "Banco Daycoval / Banco ABC",
            "tipo": "LCA",
            "taxa_cdi": 90.0,
            "carencia": "9 meses (270 dias)",
            "aplicacao_minima": 1000,
            "corretora": "Rico",
            "url_oferta": "https://www.rico.com.vc/investimentos/renda-fixa/lci-e-lca/",
        },
        {
            "emissor": "BTG Pactual / Banco Inter",
            "tipo": "LCI",
            "taxa_cdi": 92.0,
            "carencia": "12 meses (365 dias)",
            "aplicacao_minima": 5000,
            "corretora": "XP Investimentos",
            "url_oferta": "https://www.xpi.com.br/investimentos/renda-fixa/lci-lca/",
        },
        {
            "emissor": "Banco Pine / Banco Bari",
            "tipo": "LCI",
            "taxa_cdi": 94.5,
            "carencia": "24 meses (720 dias)",
            "aplicacao_minima": 10000,
            "corretora": "XP / Rico",
            "url_oferta": "https://www.xpi.com.br/investimentos/renda-fixa/lci-lca/",
        },
    ]

    ofertas_atualizadas = []
    for item in faixas_mercado:
        taxa_liq = round(cdi * (item["taxa_cdi"] / 100.0), 2)
        equiv_cdb = round(item["taxa_cdi"] / 0.85, 1)

        ofertas_atualizadas.append({
            "emissor": item["emissor"],
            "tipo": item["tipo"],
            "taxa_cdi": item["taxa_cdi"],
            "rentabilidade_liquida_aa": taxa_liq,
            "equivalente_cdb_cdi": equiv_cdb,
            "carencia": item["carencia"],
            "aplicacao_minima": item["aplicacao_minima"],
            "corretora": item["corretora"],
            "url_oferta": item["url_oferta"],
            "garantia": "FGC até R$ 250 mil",
        })

    fuso_br = timezone(timedelta(hours=-3))
    agora_br = datetime.now(fuso_br).strftime("%d/%m/%Y às %H:%M")

    resultado = {
        "atualizado_em": agora_br,
        "cdi_anual": round(cdi, 2),
        "selic_anual": round(selic, 2),
        "ofertas": ofertas_atualizadas,
    }

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Atualizado com sucesso em {agora_br} | CDI: {cdi}% | Selic: {selic}%")


if __name__ == "__main__":
    main()
