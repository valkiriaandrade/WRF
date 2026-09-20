# Validação da refatoração

- Python 3.11 no Windows: testes de conversão, leitura, erro de seleção e mapa offline.
- GRIB original lido com ecCodes: grade 243 × 214, validade 26/08/2024 09:00 UTC.
- Mapa gerado em `output/temperatura.png` com o dado real e limites estaduais locais.
- Instalação editável do pacote e verificação Ruff executadas.

A API exige um único campo de temperatura a 2 m por arquivo. Grades reduzidas não
são suportadas. A máscara por shapefile é opcional; o mapa padrão mantém a área do
GRIB. A renderização foi padronizada e não reproduz a paleta histórica pixel a pixel.

