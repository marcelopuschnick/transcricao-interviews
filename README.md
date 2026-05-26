# Pipeline de Transcrição de Entrevistas

Extrai mapas de montagem de transcrições **Whisper** usando **LLMs locais** (Ollama). Automatiza a identificação de cortes, inserts, overlays e speakers que antes eram feitos manualmente.

---

## O que faz

1. Recebe um JSON de transcrição (saída do Whisper com timestamps)
2. Envia para um modelo LLM rodando **localmente** via Ollama
3. Extrai um **mapa de montagem estruturado** com:
   - Cortes principais (`corte`)
   - Reações/Inserts (`insert`)
   - Overlays gráficos (`overlay`)
   - Legendas isoladas (`texto`)
   - Identificação de speaker
   - Flags de "corte principal" do episódio
4. Normaliza tracks (V1=Vídeo principal, V3=Inserts, V4=Overlays, V5=Texto)
5. Dá match com arquivos de fonte via `meta.fontes`

---

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.com) rodando localmente
- Modelo recomendado: `mistral:latest` ou `llama3.2:3b`

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Extrair mapa de montagem de uma transcrição
python transcription_agent.py --input entrevista.json --output mapa.json

# Com metadados de fontes multicam
python transcription_agent.py --input entrevista.json --meta fontes.json --output mapa.json
```

## Estrutura do projeto

```
.
├── transcription_agent.py    # Agente de extração via LLM local
├── requirements.txt
└── README.md
```

## Exemplo de saída

```json
{
  "titulo": "Entrevista 01",
  "duracao_total": 300,
  "cortes": [
    {"inicio": 8, "fim": 18, "descricao": "Hook forte", "tipo": "corte", "speaker": "entrevistado", "principal": true, "track": "V1", "fonte": "A001_main.mp4"},
    {"inicio": 45, "fim": 52, "descricao": "BROLL: Ambiente externo", "tipo": "insert", "speaker": "geral", "principal": false, "track": "V3", "fonte": "B001_broll.mp4"}
  ]
}
```

## LGPD & Compliance

- **100% local** — nenhum áudio ou transcrição sai da máquina
- O LLM roda via Ollama na própria rede — zero envio para APIs externas
- Dados sensíveis (entrevistas, pesquisas) nunca tocam a nuvem

---

**Stack:** Python, Ollama, JSON, Whisper (pré-processamento)
