"""
Módulo responsável pela conversão de formatos usando FFmpeg
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NexusConverter:
    """Classe para conversão de formatos de mídia"""
    
    def __init__(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path
        if not os.path.exists(ffmpeg_path):
            raise FileNotFoundError(f"FFmpeg não encontrado em: {ffmpeg_path}")
    
    def convert_audio(self, input_path: str, output_path: str, 
                     output_format: str = "mp3", bitrate: str = "192k",
                     progress_callback: Optional[Callable] = None) -> bool:
        """Converte arquivo de áudio para outro formato"""
        try:
            # Cria diretório de saída se não existir
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Parâmetros do FFmpeg baseado no formato de saída
            codec_map = {
                'mp3': ['-codec:a', 'libmp3lame', '-b:a', bitrate],
                'm4a': ['-codec:a', 'aac', '-b:a', bitrate],
                'flac': ['-codec:a', 'flac', '-compression_level', '5'],
                'opus': ['-codec:a', 'libopus', '-b:a', bitrate],
                'ogg': ['-codec:a', 'libvorbis', '-b:a', bitrate],
                'wav': ['-codec:a', 'pcm_s16le'],
            }
            
            codec_params = codec_map.get(output_format.lower(), codec_map['mp3'])
            
            # Comando FFmpeg
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                *codec_params,
                '-y',  # Sobrescrever arquivo de saída
                output_path
            ]
            
            # Executa conversão
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Processa saída para extrair progresso (se necessário)
            if progress_callback:
                progress_callback(0, "Iniciando conversão...")
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback(100, "Conversão concluída!")
                return os.path.exists(output_path)
            else:
                logger.error(f"Erro na conversão: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao converter áudio: {e}")
            return False
    
    def convert_video(self, input_path: str, output_path: str,
                     output_format: str = "mp4", quality: str = "high",
                     progress_callback: Optional[Callable] = None) -> bool:
        """Converte arquivo de vídeo para outro formato"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Presets de qualidade
            quality_presets = {
                'high': ['-crf', '18'],
                'medium': ['-crf', '23'],
                'low': ['-crf', '28'],
            }
            
            quality_params = quality_presets.get(quality, quality_presets['medium'])
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-codec:v', 'libx264' if output_format == 'mp4' else 'libvpx-vp9',
                '-codec:a', 'aac' if output_format == 'mp4' else 'libopus',
                *quality_params,
                '-preset', 'medium',
                '-y',
                output_path
            ]
            
            if progress_callback:
                progress_callback(0, "Iniciando conversão de vídeo...")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback(100, "Conversão concluída!")
                return os.path.exists(output_path)
            else:
                logger.error(f"Erro na conversão de vídeo: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao converter vídeo: {e}")
            return False
    
    def extract_audio_from_video(self, input_path: str, output_path: str,
                                output_format: str = "mp3", bitrate: str = "192k") -> bool:
        """Extrai áudio de um arquivo de vídeo"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            codec_map = {
                'mp3': ['-codec:a', 'libmp3lame', '-b:a', bitrate],
                'm4a': ['-codec:a', 'aac', '-b:a', bitrate],
                'flac': ['-codec:a', 'flac'],
                'wav': ['-codec:a', 'pcm_s16le'],
            }
            
            codec_params = codec_map.get(output_format.lower(), codec_map['mp3'])
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-vn',  # Sem vídeo
                *codec_params,
                '-y',
                output_path
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            stdout, stderr = process.communicate()
            return process.returncode == 0 and os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"Erro ao extrair áudio: {e}")
            return False

