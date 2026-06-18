# 🛶 Canoa Analytics

Gerador de relatório de treino de canoa havaiana a partir de arquivos TCX do Garmin.

## Como usar localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar via linha de comando (gera HTML direto)
python main.py

# Rodar interface web
streamlit run app.py
```

## Como hospedar no Streamlit Cloud (gratuito)

1. Crie uma conta em https://github.com e suba este projeto em um repositório
2. Acesse https://share.streamlit.io e faça login com o GitHub
3. Clique em **New app**
4. Selecione o repositório, branch `main` e arquivo `app.py`
5. Clique em **Deploy** — em poucos minutos o app estará online

O link gerado pode ser compartilhado com qualquer pessoa pelo WhatsApp.

## Estrutura do projeto

```
canoa_analytics/
├── app.py              ← Interface web (Streamlit)
├── main.py             ← Execução via terminal
├── requirements.txt    ← Dependências
├── inputs/
│   └── config.py       ← Configurações para uso local
├── core/
│   ├── parser.py       ← Leitura do TCX
│   ├── enricher.py     ← Velocidade suavizada e aceleração
│   ├── detector.py     ← Detecção dos tiros
│   └── analyzer.py     ← Score, sustentação, consistência, retidão
└── report/
    └── builder.py      ← Geração do HTML
```

## Parâmetros configuráveis

| Parâmetro | Descrição |
|---|---|
| TCX_FILE | Arquivo exportado do Garmin Connect |
| NOME_CLUB | Nome do clube |
| CANOA_TIPO | Tipo de canoa (OC1, OC6, etc.) |
| NOMES_MEMBROS | Atletas em ordem Voga → Leme |
| DISTANCIA_SPRINT | Distância de cada tiro em metros |
| NUMERO_PARTES | Divisão de cada tiro em 2 ou 4 partes |
| QTD_TIROS | Quantidade de tiros realizados |
| PESO_VELOCIDADE | Peso da velocidade no Score (%) |
| PESO_SUSTENTACAO | Peso da sustentação no Score (%) |
| PESO_CONSISTENCIA | Peso da consistência no Score (%) |
