"""
Nexus Downloader - Aplicativo Principal
Downloader, conversor e organizador de mídia para YouTube, YouTube Music e SoundCloud
"""
import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from gui import NexusDownloaderApp
    import config
    
    def main():
        """Função principal"""
        print(f"Iniciando {config.APP_NAME} v{config.APP_VERSION}...")
        
        # Verifica se FFmpeg existe
        if not os.path.exists(config.FFMPEG_PATH):
            print(f"⚠️ Aviso: FFmpeg não encontrado em {config.FFMPEG_PATH}")
            print("Algumas funcionalidades podem não funcionar corretamente.")
        
        # Cria e executa aplicativo
        app = NexusDownloaderApp()
        app.run()
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print("Por favor, instale as dependências executando:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erro ao iniciar aplicativo: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

