import subprocess
import os

def converter_para_wav(input_audio, output_audio="audios/input.wav"):
    """
    Converte qualquer arquivo de áudio para WAV usando FFmpeg.
    """

    # Garante que a pasta existe
    os.makedirs(os.path.dirname(output_audio), exist_ok=True)

    comando = [
        "ffmpeg",
        "-y",                 
        "-i", input_audio,    
        "-ar", "16000",       
        "-ac", "1",           
        output_audio          
    ]

    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[OK] Áudio convertido para: {output_audio}")
        return output_audio

    except subprocess.CalledProcessError as e:
        print("[ERRO] Falha na conversão FFmpeg")
        print(e.stderr.decode())
        return None


# Alias para manter compatibilidade com chamadas antigas
def converter_audio(input_audio, output_audio="audios/input.wav"):
    return converter_para_wav(input_audio, output_audio)
