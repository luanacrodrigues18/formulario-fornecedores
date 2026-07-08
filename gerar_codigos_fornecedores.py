"""Gera fornecedores_codigos.json a partir dos nomes únicos da planilha FUP."""

import json
from pathlib import Path

from planilha import carregar_base_fup, garantir_arquivo_fup

ARQUIVO_JSON = Path(__file__).parent / "fornecedores_codigos.json"
ARQUIVO_LISTA = Path(__file__).parent / "fornecedores_codigos_lista.txt"


def main() -> None:
    garantir_arquivo_fup()
    fornecedores = sorted(
        {r["fornecedor"] for r in carregar_base_fup() if r.get("fornecedor")}
    )
    mapa = {str(indice): nome for indice, nome in enumerate(fornecedores, start=1)}

    ARQUIVO_JSON.write_text(
        json.dumps(mapa, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with ARQUIVO_LISTA.open("w", encoding="utf-8") as arquivo:
        arquivo.write("ID\tFORNECEDOR\n")
        for codigo, nome in mapa.items():
            arquivo.write(f"{codigo}\t{nome}\n")

    print(f"✓ {len(mapa)} fornecedores em {ARQUIVO_JSON.name}")
    print(f"✓ Lista para envio em {ARQUIVO_LISTA.name}")


if __name__ == "__main__":
    main()
