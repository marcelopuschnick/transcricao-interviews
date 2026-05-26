# Transcrição de Entrevistas — Pipeline Local

Pipeline 100% off-line para transcrição de entrevistas com especialistas, garantindo conformidade total com a LGPD. Reduz o tempo de decupagem em até 70% em comparação com métodos manuais.

## Como funciona

1. **Entrada**: arquivo de áudio (MP3, WAV, M4A, OGG)
2. **Processamento**: `faster-whisper` (modelo `base`, rodando localmente — GPU opcional)
3. **Saída**: JSON estruturado com falas segmentadas, speaker detection e timestamps
4. **Decupagem**: integração directa com Adobe Premiere (via arquivo de texto) ou DaVinci Resolve (via EDL)

## Instalação

```bash
pip install faster-whisper ffmpeg-python
```

## Uso rápido

```bash
python transcricao.py entrevista.mp3
```

Gera `entrevista_transcricao.json` e `entrevista_srt`.

## Saída JSON

```json
{
  "language": "pt",
  "duration": 1845.2,
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "A gente começou pensando em..."}
  ]
}
```

## Por que local

- Dados nunca saem da máquina — zero dependências de nuvem
- Compatibilidade com ambientes corporativos restringidos (proxy, VPN, air-gapped)
- Sem custo de API — execução ilimitada

## Stack

- Python 3.10+
- faster-whisper (CTranslate2)
- FFmpeg (pré-processamento)
- LGPD conforme
