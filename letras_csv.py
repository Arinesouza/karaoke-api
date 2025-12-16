import csv
import re
import os
from ytmusicapi import YTMusic

# --- Caminho absoluto do CSV ---
# CORREÇÃO 1: Usando _file_ com dois underlines
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CSV_GLOBAL = os.path.join(BASE_DIR, "musicas.csv")

def buscar_letra_ytmusic(titulo, artista):
    yt = YTMusic()
    termo_busca = f"{titulo} {artista}"
    
    # Busca a música (filtro por 'songs')
    resultados = yt.search(termo_busca, filter="songs")
    if not resultados:
        return None

    video_id = resultados[0]['videoId']
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Pega o objeto 'watch playlist' que contém o ID da letra
    watch_playlist = yt.get_watch_playlist(videoId=video_id)
    lyrics_id = watch_playlist.get('lyrics')
    
    if not lyrics_id:
        # Retorna o vídeo mesmo sem letra, para não quebrar tudo
        return {
            "lyrics": "",
            "video_url": video_url
        }

    lyrics_data = yt.get_lyrics(lyrics_id)
    letra = lyrics_data.get('lyrics', '')

    return {
        "lyrics": letra,
        "video_url": video_url
    }

def gerar_csv_palavras(titulo, artista, letra, arquivo_csv=ARQUIVO_CSV_GLOBAL):
    # Limpeza básica e separação de palavras
    letra_limpa = re.sub(r'\[.*?\]', '', letra)
    palavras = re.findall(r"\b\w+'\w+|\w+\b", letra_limpa.lower())

    escrever_cabecalho = not os.path.exists(arquivo_csv)

    try:
        with open(arquivo_csv, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            if escrever_cabecalho:
                writer.writerow(["id", "titulo", "artista", "palavra"])

            for idx, palavra in enumerate(palavras, 1):
                writer.writerow([idx, titulo, artista, palavra])

        # CORREÇÃO 2: Retorna a lista de palavras (e não apenas True)
        return palavras

    except Exception as e:
        print(f"[Erro CSV] Falha ao escrever: {e}")
        return []

def buscar_e_adicionar_letra(titulo, artista, arquivo_csv=ARQUIVO_CSV_GLOBAL):
    print(f"[LETRA BUSCA] Procurando: {titulo} - {artista}")

    dados = buscar_letra_ytmusic(titulo, artista)
    
    if dados and dados.get("lyrics"):
        letra = dados["lyrics"]
        video_url = dados["video_url"]

        print("[LETRA] Encontrada. Salvando CSV.")
        
        # Pega a lista retornada pela função
        lista_palavras = gerar_csv_palavras(titulo, artista, letra, arquivo_csv)

        # CORREÇÃO 3: Retorna o dicionário COM a chave 'palavras'
        return {
            "sucesso": True,
            "video_url": video_url,
            "palavras": lista_palavras  # O servidor precisa disso!
        }

    print("[LETRA] Não encontrada no YouTube Music.")
    return None

if __name__ == "_main_":
    print("--- Teste Rápido ---")
    titulo = input("Título: ").strip()
    artista = input("Artista: ").strip()

    resultado = buscar_e_adicionar_letra(titulo, artista)
    if resultado and resultado.get("sucesso"):
        print(f"[SUCESSO] {len(resultado['palavras'])} palavras encontradas.")
    else:
        print("[FALHA] Não foi possível salvar a letra.")