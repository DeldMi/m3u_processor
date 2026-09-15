import re
from typing import Dict, Any

class StreamClassifier:
    # Mapeamento de siglas federativas brasileiras para estados
    UFS_BRASIL = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
        "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
        "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
        "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
        "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
        "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
        "SE": "Sergipe", "TO": "Tocantins"
    }

    @classmethod
    def classify(cls, name: str, group: str, url: str) -> Dict[str, str]:
        target = f"{name} {group} {url}".lower()
        
        # 1. Identificacao de Natureza do Fluxo (Se e canal ao vivo ou VOD/Midia)
        category = "tv"
        if re.search(r'(\.mp4|\.mkv|\.avi|\/movie\/|\/filmes?\/|\/series\/|vod)', target):
            category = "series" if re.search(r'(s\d{1,2}e\d{1,2}|temporada|\/series\/)', target) else "vod"
        elif re.search(r'(\.aac|\.mp3|\.ogg|radio|fm\b)', target):
            category = "radio"
        elif "24/7" in target or "desenhos" in target:
            category = "outros"

        # 2. Identificacao de Pais (Norma ISO 3166 ou tokens de grupo)
        country = "Brasil"
        if re.search(r'\b(usa|eua|united states|us)\b', target):
            country = "Estados Unidos"
        elif re.search(r'\b(portugal|pt)\b', target):
            country = "Portugal"
        elif re.search(r'\b(espanha|spain|es)\b', target):
            country = "Espanha"
        elif re.search(r'\b(uk|reino unido)\b', target):
            country = "Reino Unido"

        # 3. Identificacao de Estado e Cidade (Brasil prioritario)
        state = "Nacional/Geral"
        city = "Geral"

        if country == "Brasil":
            for uf, estado_extenso in cls.UFS_BRASIL.items():
                if re.search(rf'[\s\-\|\(]{uf}[\s\-\|\)]', name, re.IGNORECASE) or estado_extenso.lower() in target:
                    state = estado_extenso
                    break

            # Extracao heuristica de cidades notaveis
            cidades_map = {
                "Recife": ["recife", "olinda"],
                "São Paulo": ["sao paulo", "sp capital", "campinas", "santos"],
                "Rio de Janeiro": ["rio de janeiro", "niteroi"],
                "Belo Horizonte": ["belo horizonte", "bh"],
                "Salvador": ["salvador"],
                "Curitiba": ["curitiba"],
                "Porto Alegre": ["porto alegre"]
            }
            for cidade_nome, tokens in cidades_map.items():
                if any(t in target for t in tokens):
                    city = cidade_nome
                    break

        return {
            "category": category,
            "country": country,
            "state": state,
            "city": city
        }