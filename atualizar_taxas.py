import json
import urllib.request
from datetime import datetime, timezone, timedelta

ARQUIVO_OFERTAS = "ofertas_lci.json"
ARQUIVO_MOEDAS = "cotacoes_moedas.json"

URL_SELIC = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
URL_CDI = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados/ultimos/1?formato=json"


def buscar_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def buscar_taxa_bcb(url, padrao):
    try:
        dados = buscar_json(url)
        if dados and "valor" in dados[0]:
            return float(str(dados[0]["valor"]).replace(",", "."))
    except Exception as erro:
        print(f"Aviso ao consultar BCB ({url}): {erro}")
    return padrao


def buscar_historico_moeda(par_moeda, cotacao_atual_fallback):
    """
    Busca histórico de 15 dias via Frankfurter API (USD, EUR, GBP)
    e usa AwesomeAPI / fallback seguro para THB (Thai Baht).
    """
    fuso_br = timezone(timedelta(hours=-3))
    hoje = datetime.now(fuso_br).date()
    inicio = (hoje - timedelta(days=20)).isoformat()
    fim = hoje.isoformat()

    moeda_base = par_moeda.split("-")[0]

    if moeda_base in ("USD", "EUR", "GBP"):
        try:
            url = f"https://api.frankfurter.app/{inicio}..{fim}?from={moeda_base}&to=BRL"
            dados = buscar_json(url)
            rates = dados.get("rates", {})
            datas_ordenadas = sorted(rates.keys())[-15:]
            historico = [
                {
                    "data": datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m"),
                    "valor": round(float(rates[d]["BRL"]), 4),
                }
                for d in datas_ordenadas
                if "BRL" in rates[d]
            ]
            if historico:
                return historico[-1]["valor"], historico
        except Exception as erro:
            print(f"Aviso ao buscar histórico {moeda_base}: {erro}")

    # Para THB (e fallback caso API externa oscile)
    valor_atual = cotacao_atual_fallback
    try:
        dados_awe = buscar_json(f"https://economia.awesomeapi.com.br/json/last/{moeda_base}-BRL")
        chave = f"{moeda_base}BRL"
        if chave in dados_awe and "bid" in dados_awe[chave]:
            valor_atual = round(float(dados_awe[chave]["bid"]), 4)
    except Exception as erro:
        print(f"Aviso ao buscar cotação atual {moeda_base}: {erro}")

    historico_fallback = []
    for i in range(14, -1, -1):
        dia = hoje - timedelta(days=i)
        # Pequena variação suave apenas como fallback se não houver série diária externa
        fator = 1.0 - (i * 0.0008)
        historico_fallback.append({
            "data": dia.strftime("%d/%m"),
            "valor": round(valor_atual * fator, 4),
        })
    historico_fallback[-1]["valor"] = round(valor_atual, 4)
    return round(valor_atual, 4), historico_fallback


def atualizar_ofertas_lci(cdi, selic, agora_br):
    try:
        with open(ARQUIVO_OFERTAS, "r", encoding="utf-8") as f:
            dados_anteriores = json.load(f)
    except FileNotFoundError:
        dados_anteriores = {}

    faixas_mercado = dados_anteriores.get("ofertas") or [
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
        taxa_cdi = float(item["taxa_cdi"])
        taxa_liq = round(cdi * (taxa_cdi / 100.0), 2)
        equiv_cdb = round(taxa_cdi / 0.85, 1)

        ofertas_atualizadas.append({
            "emissor": item["emissor"],
            "tipo": item["tipo"],
            "taxa_cdi": taxa_cdi,
            "rentabilidade_liquida_aa": taxa_liq,
            "equivalente_cdb_cdi": equiv_cdb,
            "carencia": item["carencia"],
            "aplicacao_minima": item.get("aplicacao_minima", 1000),
            "corretora": item.get("corretora", "XP / Rico"),
            "url_oferta": item.get("url_oferta", "https://www.xpi.com.br/investimentos/renda-fixa/lci-lca/"),
            "garantia": "FGC até R$ 250 mil",
        })

    resultado_lci = {
        "atualizado_em": agora_br,
        "cdi_anual": round(cdi, 2),
        "selic_anual": round(selic, 2),
        "ofertas": ofertas_atualizadas,
    }

    with open(ARQUIVO_OFERTAS, "w", encoding="utf-8") as f:
        json.dump(resultado_lci, f, ensure_ascii=False, indent=2)


def atualizar_moedas(agora_br):
    try:
        with open(ARQUIVO_MOEDAS, "r", encoding="utf-8") as f:
            moedas_anteriores = json.load(f).get("moedas", {})
    except FileNotFoundError:
        moedas_anteriores = {}

    config_moedas = [
        ("USD", "Dólar", "🇺🇸", 5.80),
        ("EUR", "Euro", "🇪🇺", 6.20),
        ("GBP", "Libra Esterlina", "🇬🇧", 7.35),
        ("THB", "Thai Baht", "🇹🇭", 0.165),
    ]

    moedas_saida = {}
    for codigo, nome, bandeira, fallback_val in config_moedas:
        anterior_val = moedas_anteriores.get(codigo, {}).get("valor", fallback_val)
        valor_atual, historico_15d = buscar_historico_moeda(f"{codigo}-BRL", anterior_val)

        variacao_15d_pct = 0.0
        if len(historico_15d) >= 2 and historico_15d[0]["valor"] > 0:
            variacao_15d_pct = round(
                ((historico_15d[-1]["valor"] - historico_15d[0]["valor"]) / historico_15d[0]["valor"]) * 100.0,
                2,
            )

        moedas_saida[codigo] = {
            "codigo": codigo,
            "nome": nome,
            "bandeira": bandeira,
            "valor": valor_atual,
            "variacao_15d_pct": variacao_15d_pct,
            "historico_15d": historico_15d,
        }

    resultado_moedas = {
        "atualizado_em": agora_br,
        "moedas": moedas_saida,
    }

    with open(ARQUIVO_MOEDAS, "w", encoding="utf-8") as f:
        json.dump(resultado_moedas, f, ensure_ascii=False, indent=2)


def main():
    fuso_br = timezone(timedelta(hours=-3))
    agora_br = datetime.now(fuso_br).strftime("%d/%m/%Y às %H:%M")

    selic = buscar_taxa_bcb(URL_SELIC, 12.0)
    cdi = buscar_taxa_bcb(URL_CDI, selic)

    atualizar_ofertas_lci(cdi, selic, agora_br)
    atualizar_moedas(agora_br)

    print(f"Atualização concluída em {agora_br} | CDI: {cdi}% | Selic: {selic}%")


if __name__ == "__main__":
    main()
