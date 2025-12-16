import letras_csv
print("USANDO:", letras_csv.__file__)

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
import sys

try:
    import script
    import audio_converter
except ImportError as e:
    print(f"[ERRO DE IMPORTAÇÃO] Falha ao importar módulos: {e}")
    sys.exit(1)

app = Flask(__name__)
CORS(app)

PASTA_AUDIOS = "audios"
ARQUIVO_CSV = "musicas.csv"
os.makedirs(PASTA_AUDIOS, exist_ok=True)

print("\n" + "="*50)
print("[SERVIDOR] Inicializando e carregando modelos de IA...")
script.configurar_ffmpeg_local()
stt_model, sim_model = script.load_models()
print("[SERVIDOR] Modelos carregados!")
print("="*50 + "\n")

@app.route('/analisar', methods=['POST'])
def analisar_karaoke():
    caminho_temp = None
    caminho_wav = None

    try:
        titulo = request.form.get("titulo")
        artista = request.form.get("artista")

        if not titulo or not artista:
            return jsonify({"erro": "Campos 'titulo' e 'artista' são obrigatórios"}), 400
        
        if 'audio' not in request.files:
            return jsonify({"erro": "Nenhum arquivo de áudio enviado"}), 400

        arquivo = request.files["audio"]
        print(f"\n[REQ] Nova análise: {titulo} - {artista}")

        nome_unico = f"upload_{uuid.uuid4().hex}"
        ext = os.path.splitext(arquivo.filename)[1] or ".m4a"

        caminho_temp = os.path.join(PASTA_AUDIOS, nome_unico + ext)
        caminho_wav = os.path.join(PASTA_AUDIOS, nome_unico + ".wav")

        arquivo.save(caminho_temp)
        print(f"[ARQUIVO] Salvo em {caminho_temp}")

        if not audio_converter.converter_audio(caminho_temp, caminho_wav):
            return jsonify({"erro": "Falha ao converter o áudio"}), 500

        df = None
        palavras_original = None
        video_url = None

        try:
            df = script.carregar_csv_palavras(ARQUIVO_CSV)
            palavras_original = script.montar_letra_por_palavras(df, titulo)
            video_url = letras_csv.buscar_video_no_csv(ARQUIVO_CSV, titulo)
        except Exception:
            pass

        if palavras_original is None:
            print(f"[LETRA] Buscando online: {titulo}")
            resultado = letras_csv.buscar_e_adicionar_letra(titulo, artista, ARQUIVO_CSV)
            if not resultado:
                return jsonify({"erro": "Letra não encontrada online."}), 404

            palavras_original = resultado["palavras"]
            video_url = resultado["video_url"]

        print("[IA] Transcrevendo áudio...")
        texto_usuario = script.transcrever_audio(stt_model, caminho_wav)
        palavras_usuario = texto_usuario.split()

        p_o, p_u = script.alinhar_inteligente(sim_model, palavras_original, palavras_usuario)
        media_sim, scores = script.comparar_palavras(sim_model, p_o, p_u)
        nota_final = script.calcular_nota(media_sim)
        info_faltantes = script.detectar_palavras_faltantes(palavras_original, palavras_usuario)

        detalhes = []
        for o, u, s in zip(p_o, p_u, scores):
            if s > 0.85: status = "otimo"
            elif s > 0.60: status = "bom"
            else: status = "ruim"

            detalhes.append({
                "original": o,
                "usuario": u,
                "score": float(f"{s:.4f}"),
                "status": status
            })

        resposta = {
            "sucesso": True,
            "musica": titulo,
            "artista": artista,
            "video_url": video_url,
            "nota_final": nota_final,
            "similaridade_media": float(f"{media_sim:.4f}"),
            "cobertura_letra": info_faltantes["cobertura"],
            "palavras_nao_cantadas": info_faltantes["faltantes"],
            "analise_detalhada": detalhes
        }

        print(f"[OK] Análise concluída. Nota {nota_final}/99")
        return jsonify(resposta)

    except Exception as e:
        print(f"[ERRO CRÍTICO] {e}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

    finally:
        if caminho_temp and os.path.exists(caminho_temp):
            os.remove(caminho_temp)
        if caminho_wav and os.path.exists(caminho_wav):
            os.remove(caminho_wav)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

