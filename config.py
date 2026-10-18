"""
Configurações globais do aplicativo
"""
import os
from pathlib import Path

# Caminho do FFmpeg

# Diretório padrão de downloads
DEFAULT_DOWNLOAD_DIR = os.path.join(Path.home(), "Downloads", "NexusDownloads")

# Estrutura padrão de pastas
FOLDER_STRUCTURE = {
    "artista": True,
    "album": True,
    "genero": False,
    "ano": False
}

# Formatos de saída suportados
AUDIO_FORMATS = ["mp3", "m4a", "flac", "opus", "ogg", "wav"]
VIDEO_FORMATS = ["mp4", "webm", "mkv"]

# Qualidade padrão
DEFAULT_AUDIO_QUALITY = "best"
DEFAULT_VIDEO_QUALITY = "best"

# Configurações de metadados
METADATA_ENABLED = True
COVER_ART_ENABLED = True

# Timeout para downloads (segundos)
DOWNLOAD_TIMEOUT = 300

# Configurações da interface
APP_NAME = "NEXUS MEDIA STUDIO"
APP_VERSION = "3.0.0"
APP_COPYRIGHT = "© 2026 Nexus Media Studio. Todos os direitos reservados."
ONBOARDING_VERSION = 1
THEME_MODE = "light"
COLOR_THEME = "blue"

# Tema de site padrão (controle de look geral do app)
# Valores possíveis: "youtube", "soundcloud"
DEFAULT_SITE_THEME = "youtube"

# Arquivo de configurações do usuário (preferências persistentes)
USER_SETTINGS_FILE = os.path.join(Path.home(), ".nexus_media_studio_settings.json")


# Auto-detecção de FFmpeg (prioriza local, depois system)
import sys

def get_ffmpeg_path():
    # Tenta FFmpeg local na pasta do executável
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    local_ffmpeg = os.path.join(base_path, 'ffmpeg', 'bin', 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    
    # Tenta caminho padrão
    if os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe"):
        return r"C:\ffmpeg\bin\ffmpeg.exe"
    
    # Procura no PATH
    import shutil
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        return system_ffmpeg
    
    return r"C:\ffmpeg\bin\ffmpeg.exe"  # fallback

FFMPEG_PATH = get_ffmpeg_path()
