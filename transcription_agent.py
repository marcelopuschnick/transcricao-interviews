"""
transcription_agent.py
Agente de extração estrutural de entrevistas via LLM local.
Conecta-se a um modelo Ollama rodando localmente e extrai mapas de montagem,
identificando speakers, cortes principais, inserts e overlays de uma transcrição Whisper.

Uso:
    python transcription_agent.py --input transcricao.json --output mapa.json
"""
import json, os, sys, argparse, requests
from dotenv import load_dotenv

load_dotenv()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL       = os.getenv("OLLAMA_MODEL", "mistral:latest")


def chat(messages, temperature=0.3, max_tokens=2000):
    """Envia mensagens para o Ollama e retorna (resposta_texto, sucesso_bool)."""
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={"model": MODEL, "messages": messages,
                  "options": {"temperature": temperature,
                              "num_predict": max_tokens,
                              "top_p": 0.8},
                  "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"], True
    except Exception as e:
        return f"[ERRO Ollama] {e}", False


def _prompt_sistema():
    """Prompt de sistema para extração de mapa de montagem a partir de transcrição."""
    return "\n".join([
        "Voce e editor de video. Analisa uma transcricao para extrair cortes de um podcast ou entrevista multicamera.",
        "",
        "REGRAS STRICT:",
        "1. TIPOS: corte | insert | overlay | texto",
        "   corte = trecho principal da conversa na cam wide",
        "   insert = reacao/cobertura/close/outra camera ou b-roll",
        "   overlay = texto grafico sobre video (chamada, lower third)",
        "   texto = caption legenda isolada (quote)",
        "",
        "2. Cada corte PRECISA: inicio, fim, descricao, tipo, speaker, principal",
        "   principal: true/false (APENAS UM corte com true, o mais impactante)",
        "   Se insert com reacao: anote 'reacao de X' na descricao",
        "   Se usar b-roll: comece descricao com 'BROLL:'",
        "",
        "3. Speaker: entrevistador | entrevistado | geral",
        "",
        "4. Minimo 1 corte (principal:true). Total entre 3-15 cortes.",
        "5. Corte introducoes enroladas. Mantenha punchline + reacao.",
        "6. Responda APENAS em JSON puro, sem markdown.",
        "",
        'EXEMPLO: {"titulo":"Ep","duracao_total":300,"cortes":',
        '[{"inicio":8,"fim":18,"descricao":"Hook forte","tipo":"corte","speaker":"entrevistado","principal":true},',
        '{"inicio":45,"fim":52,"descricao":"BROLL: Estacionamento vazio","tipo":"insert","speaker":"geral","principal":false}]}',
    ])


def _inferir_fontes_por_tipo(meta_dict):
    """Interpreta meta.fontes para alocar arquivos de midia nos roles certos."""
    fontes_roll  = []
    fontes_close = []
    fontes_broll = []

    if meta_dict and isinstance(meta_dict, dict):
        for f in meta_dict.get("fontes", []):
            arq = f.get("arquivo", "")
            t = (f.get("tipo", "") + " " + f.get("nota", "")).lower()
            if any(k in t for k in ("a-roll", "principal", "main", "wide")):
                fontes_roll.append(arq)
            elif any(k in t for k in ("close", "reacao", "cutaway", "face")):
                fontes_close.append(arq)
            elif any(k in t for k in ("b-roll", "broll")):
                fontes_broll.append(arq)

    # Fallbacks padrao
    if not fontes_roll:  fontes_roll  = ["A001_main.mp4"]
    if not fontes_close: fontes_close = ["A001_close.mp4"]
    if not fontes_broll: fontes_broll = ["B001_broll.mp4"]

    return fontes_roll, fontes_close, fontes_broll


def normalizar_mapa_tracks(mapa, meta=None):
    """Atribui track (V1/V3/V4/V5) e fonte de midia para cada corte do mapa."""
    fontes_roll, fontes_close, fontes_broll = _inferir_fontes_por_tipo(meta)

    for c in mapa.get("cortes", []):
        tipo = c.get("tipo", "corte")
        desc = c.get("descricao", "").lower()

        if tipo == "corte":
            c.setdefault("track", "V1")
            c.setdefault("fonte", fontes_roll[0])
        elif tipo == "insert":
            c.setdefault("track", "V3")
            if any(k in desc for k in ("broll", "b-roll", "externo", "cena", "rua", "imagem", "foto")):
                c.setdefault("fonte", fontes_broll[0])
            else:
                c.setdefault("fonte", fontes_close[0])
        elif tipo == "overlay":
            c.setdefault("track", "V4")
            c.setdefault("fonte", "OVERLAY")
        elif tipo == "texto":
            c.setdefault("track", "V5")
            c.setdefault("fonte", "LEGENDA")
        else:
            c.setdefault("track", "V1")
            c.setdefault("fonte", fontes_roll[0])

    return mapa


def extrair_mapa_montagem(transcricao_json_path, meta=None, output_path=None):
    """
    Le um JSON de transcricao (formato Whisper) e retorna um mapa de montagem
    com cortes, inserts e overlays tipados.
    """
    try:
        with open(transcricao_json_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception as e:
        return {"erro": f"Falha ao carregar JSON: {e}"}

    segments = dados.get("segments", [])
    if not segments:
        return {"erro": "Nenhum segmento encontrado"}

    # Monta texto com timestamps
    linhas = []
    for i, seg in enumerate(segments, 1):
        t0, t1 = seg.get("start", 0), seg.get("end", 0)
        linhas.append(f"[{i}] {t0:.1f}s - {t1:.1f}s | {seg.get('text','').strip()}")
    bloco = "\n".join(linhas)
    duracao_total = segments[-1].get("end", 0)

    # Meta do proprio JSON tem prioridade
    json_meta = dados.get("meta", {})
    if meta is None and json_meta:
        meta = json_meta

    resposta, ok = chat([
        {"role": "system", "content": _prompt_sistema()},
        {"role": "user",   "content": f"Transcricao ({len(segments)} segmentos, {duracao_total:.0f}s):\n\n{bloco}"},
    ], temperature=0.4, max_tokens=2500)

    if not ok:
        return {"erro": resposta}

    # Parse JSON da resposta
    try:
        texto = resposta.strip()
        if "```json" in texto:
            texto = texto.split("```json")[1].split("```")[0].strip()
        elif "```" in texto:
            texto = texto.split("```")[1].split("```")[0].strip()
        mapa = json.loads(texto)

        if "cortes" not in mapa or not isinstance(mapa["cortes"], list):
            return {"erro": "JSON sem campo 'cortes'", "raw": texto}

        mapa = normalizar_mapa_tracks(mapa, meta)
        mapa["source_file"] = transcricao_json_path
        if meta:
            mapa.setdefault("meta", {})
            if "fontes" in meta:
                mapa["meta"]["fontes"] = meta["fontes"]

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(mapa, f, ensure_ascii=False, indent=2)
            print(f"[OK] Mapa salvo: {output_path}")

        return mapa
    except Exception as e:
        return {"erro": f"Falha ao parsear JSON: {e}", "raw": resposta[:500]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai mapa de montagem de transcricao Whisper")
    parser.add_argument("--input",  required=True, help="Caminho para transcricao.json (Whisper)")
    parser.add_argument("--output", default=None,  help="Caminho para salvar mapa_montagem.json")
    parser.add_argument("--meta",   default=None,  help="Caminho para meta.json (fontes multicam)")
    args = parser.parse_args()

    meta = None
    if args.meta:
        with open(args.meta, "r", encoding="utf-8") as f:
            meta = json.load(f)

    resultado = extrair_mapa_montagem(args.input, meta, args.output)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
