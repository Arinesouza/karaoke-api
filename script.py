import os
import csv
import re
import whisper
import torch
from sentence_transformers import SentenceTransformer, util
from ytmusicapi import YTMusic
import pandas as pd

# ======================================================
# CONFIGURAÇÕES GERAIS
# ======================================================

ARQUIVO_CSV_GLOBAL = "musicas.csv"

# Força CPU (Render não tem GPU)
DEVICE = "cpu"

# ======================================================
# CARREGAMENTO DE MODELOS (CACHE GLOBAL)
# ======================================================

print("[INFO] Carregando modelo Whisper (tiny)...")
whisper_model = whisper.load_model("tiny", device=DEVICE)

print("[INFO] Carregando modelo SBERT (leve)...")
sbert = SentenceTransformer("paraphrase-MiniLM-L3-v2", device=DEVICE)

print("[OK] Modelos carregados com sucesso!")

# ======================================================
# FUNÇÕES DE INFRA
# ======================================================

def configurar_ffmpeg_local():
    """
    Em produção (Render), o ffmpeg já existe no sistema.
    """
    print("[FFMPEG] Usando ffmpeg do sistema")
    return True


def load_models():
    """
    Fornece exatamente o que servidor.py espera.
    """
    return whisper_model, sbert

# ======================================================
# ÁUDIO / TRANSCRIÇÃO
# ======================================================

def transcrever_audio(modelo_whisper, caminho_audio):
    """
    Transcreve áudio usando Whisper.
    """
    print(f"[TRANSCRIÇÃO] Processando {caminho_audio}")
    result = modelo_whisper.transcribe(
        caminho_audio,
        fp16=False,
        language="en"
    )
    return result.get("text", "").strip()

# ======================================================
# LETRAS (YouTube Music)
# ======================================================

def buscar_letra_ytmusic(titulo, artista):
    """
    Busca letra no YouTube Music.
    """
    yt = YTMusic()
    termo = f"{titulo} {artista}"

    resultados = yt.search(termo, filter="songs")
    if not resultados:
        return None

    video_id = resultados[0].get("videoId")
    if not video_id:
        return None

    playlist = yt.get_watch_playlist(videoId=video_id)
    lyrics_id = playlist.get("lyrics")

    if not lyrics_id:
        return None

    lyrics_data = yt.get_lyrics(lyrics_id)
    return lyrics_data.get("lyrics", "")


def gerar_csv_palavras(titulo, artista, letra, arquivo_csv=ARQUIVO_CSV_GLOBAL):
    palavras = re.findall(r"\b\w+'\w+|\w+\b", letra.lower())
    escrever_cabecalho = not os.path.exists(arquivo_csv)

    with open(arquivo_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if escrever_cabecalho:
            writer.writerow(["titulo", "artista", "palavra"])
        for palavra in palavras:
            writer.writerow([titulo, artista, palavra])

    return palavras


def buscar_e_adicionar_letra(titulo, artista, arquivo_csv=ARQUIVO_CSV_GLOBAL):
    """
    Retorna:
    {
        "palavras": [...],
        "video_url": None
    }
    """
    print(f"[LETRA] Buscando letra: {titulo} - {artista}")
    letra = buscar_letra_ytmusic(titulo, artista)

    if not letra:
        print("[LETRA] Não encontrada.")
        return None

    palavras = gerar_csv_palavras(titulo, artista, letra, arquivo_csv)

    return {
        "palavras": palavras,
        "video_url": None
    }

# ======================================================
# CSV
# ======================================================

def carregar_csv_palavras(arquivo_csv):
    if not os.path.exists(arquivo_csv):
        return None
    return pd.read_csv(arquivo_csv)


def montar_letra_por_palavras(df, titulo):
    df_musica = df[df["titulo"].str.lower() == titulo.lower()]
    if df_musica.empty:
        return None
    return df_musica["palavra"].tolist()

# ======================================================
# IA — ALINHAMENTO E AVALIAÇÃO
# ======================================================

def alinhar_inteligente(modelo_sbert, palavras_original, palavras_usuario):
    alinh_o = []
    alinh_u = []

    for p in palavras_original:
        melhor_score = -1
        melhor_u = ""

        for u in palavras_usuario:
            emb1 = modelo_sbert.encode(p, convert_to_tensor=True)
            emb2 = modelo_sbert.encode(u, convert_to_tensor=True)
            sim = util.cos_sim(emb1, emb2).item()

            if sim > melhor_score:
                melhor_score = sim
                melhor_u = u

        alinh_o.append(p)
        alinh_u.append(melhor_u)

    return alinh_o, alinh_u


def comparar_palavras(modelo_sbert, palavras_o, palavras_u):
    scores = []

    for o, u in zip(palavras_o, palavras_u):
        emb1 = modelo_sbert.encode(o, convert_to_tensor=True)
        emb2 = modelo_sbert.encode(u, convert_to_tensor=True)
        score = util.cos_sim(emb1, emb2).item()
        scores.append(score)

    media = sum(scores) / len(scores) if scores else 0
    return media, scores


def calcular_nota(media):
    return int(media * 99)


def detectar_palavras_faltantes(lista_original, lista_usuario):
    usuario = set([p.lower() for p in lista_usuario])
    faltantes = [p for p in lista_original if p.lower() not in usuario]

    cobertura = (1 - len(faltantes) / len(lista_original)) * 100 if lista_original else 0

    return {
        "faltantes": faltantes,
        "cobertura": round(cobertura, 2)
    }
