"""
Módulo responsável pelos downloads de YouTube, YouTube Music e SoundCloud
"""
import os
import re
import yt_dlp
import requests
from pathlib import Path
from typing import Dict, Optional, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NexusDownloader:
    """Classe principal para downloads"""
    
    def __init__(self, download_dir: str, ffmpeg_path: str, progress_callback: Optional[Callable] = None, 
                 cookies_file: Optional[str] = None):
        self.download_dir = download_dir
        self.ffmpeg_path = ffmpeg_path
        self.progress_callback = progress_callback
        self.cookies_file = cookies_file
        self._ensure_download_dir()
    
    def _ensure_download_dir(self):
        """Garante que o diretório de download existe"""
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_platform(self, url: str) -> str:
        """Identifica a plataforma baseado na URL"""
        if "youtube.com" in url or "youtu.be" in url:
            if "music.youtube.com" in url:
                return "youtube_music"
            return "youtube"
        elif "soundcloud.com" in url:
            return "soundcloud"
        return "unknown"
    
    def _get_base_opts(self, use_cookies: bool = True) -> Dict:
        """Retorna opções base do yt-dlp com cookies se disponível e solicitado"""
        opts = {
            'quiet': False,
            'no_warnings': False,
            # User-Agent moderno para evitar bloqueios
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Headers adicionais para simular navegador real
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            # Retry em caso de erro
            'retries': 10,
            'fragment_retries': 10,
            'file_access_retries': 3,
            # Timeout maior para downloads lentos
            'socket_timeout': 30,
            # Ignora erros de certificado SSL (pode ajudar em alguns casos)
            'nocheckcertificate': False,
        }
        
        # Adiciona cookies se fornecido
        if use_cookies and self.cookies_file and os.path.exists(self.cookies_file):
            opts['cookiefile'] = self.cookies_file
            logger.info(f"Usando arquivo de cookies: {self.cookies_file}")
        
        return opts
    
    def _is_playlist(self, url: str) -> bool:
        """Verifica se a URL é uma playlist, mix, set ou radio"""
        playlist_indicators = [
            '/sets/',
            '/playlists/',
            '/albums/',
            '/stations/',
            'list=',
            'playlist',
            'mix',
            'set',
            'radio'
        ]
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in playlist_indicators)
    
    def _get_playlist_info(self, url: str) -> Dict:
        """Obtém informações de uma playlist/mix"""
        ydl_opts = self._get_base_opts()
        ydl_opts.update({
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Não baixa, só lista
            'ignoreerrors': False,
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info and 'entries' in info:
                    entries = [e for e in info.get('entries', []) if e]  # Remove None
                    
                    # Extrai título melhorado da playlist
                    playlist_title = (
                        info.get('title') or 
                        info.get('description') or 
                        info.get('uploader', 'Unknown') + ' - Playlist' or
                        'Unknown Playlist'
                    )
                    
                    # Limpa título para usar como nome de pasta
                    playlist_title = playlist_title.strip()
                    if len(playlist_title) > 100:
                        playlist_title = playlist_title[:100]
                    
                    return {
                        'is_playlist': True,
                        'title': playlist_title,
                        'entry_count': len(entries),
                        'entries': entries,
                        'playlist_id': info.get('id', ''),
                        'uploader': info.get('uploader', 'Unknown'),
                        'original_title': info.get('title', ''),
                    }
                return {'is_playlist': False}
        except Exception as e:
            logger.error(f"Erro ao obter informações da playlist: {e}")
            return {'is_playlist': False, 'error': str(e)}
    
    def _get_video_info(self, url: str) -> Dict:
        """Obtém informações do vídeo sem baixar"""
        # Estratégias seguras para extração
        strategies = [
            (True, "Com cookies"),
            (False, "Sem cookies")
        ]
        
        for use_cookies, strategy_name in strategies:
            ydl_opts = self._get_base_opts(use_cookies=use_cookies)
            ydl_opts.update({
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            })
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Verifica se é playlist que foi extraída como única
                    if info and 'entries' in info and len(info.get('entries', [])) > 1:
                        # É uma playlist, processa de forma diferente
                        return self._get_playlist_info(url)
                    
                    # Extração melhorada de metadados
                    metadata = {
                        'title': info.get('title') or info.get('track') or 'Unknown',
                        'artist': self._extract_artist(info),
                        'album': self._extract_album(info),
                        'duration': info.get('duration', 0),
                        'thumbnail': self._get_best_thumbnail(info),
                        'description': info.get('description', ''),
                        'upload_date': info.get('upload_date', ''),
                        'view_count': info.get('view_count', 0),
                        'tags': info.get('tags', []),
                        'genre': self._extract_genre(info),
                        'year': self._extract_year(info),
                        'creator': info.get('creator') or info.get('uploader', ''),
                        'uploader': info.get('uploader', ''),
                        'uploader_id': info.get('uploader_id', ''),
                        'channel': info.get('channel', ''),
                        'channel_id': info.get('channel_id', ''),
                        'webpage_url': info.get('webpage_url', url),
                        'track': info.get('track', ''),
                    }
                    return metadata
            except Exception as e:
                err_msg = str(e)
                if "Requested format is not available" in err_msg or "Sign in to confirm you're not a bot" in err_msg or "challenge solving failed" in err_msg:
                    continue  # tenta o próximo ciclo
                
                logger.error(f"Erro ao obter informações com estratégia {strategy_name}: {e}")
                continue
                
        return {}

    def _build_metadata_from_info(self, info: Dict, url: str = "") -> Dict:
        """Constrói o dicionário de metadados a partir de um info já extraído."""
        try:
            metadata = {
                'title': info.get('title') or info.get('track') or 'Unknown',
                'artist': self._extract_artist(info),
                'album': self._extract_album(info),
                'duration': info.get('duration', 0),
                'thumbnail': self._get_best_thumbnail(info),
                'description': info.get('description', ''),
                'upload_date': info.get('upload_date', ''),
                'view_count': info.get('view_count', 0),
                'tags': info.get('tags', []),
                'genre': self._extract_genre(info),
                'year': self._extract_year(info),
                'creator': info.get('creator') or info.get('uploader', ''),
                'uploader': info.get('uploader', ''),
                'uploader_id': info.get('uploader_id', ''),
                'channel': info.get('channel', ''),
                'channel_id': info.get('channel_id', ''),
                'webpage_url': info.get('webpage_url', url),
                'track': info.get('track', ''),
            }
            return metadata
        except Exception as e:
            self.log(f"Erro ao construir metadados: {str(e)}", "ERROR")
            return {}

    def _extract_artist(self, info: Dict) -> str:
        """Extrai artista das informações com múltiplas fontes"""
        # Tenta múltiplas fontes
        artist = (info.get('artist') or 
                 info.get('uploader') or 
                 info.get('creator') or 
                 info.get('channel') or 
                 'Unknown')
        
        # Se for uma lista, pega o primeiro
        if isinstance(artist, list):
            artist = artist[0] if artist else 'Unknown'
        
        return str(artist).strip()
    
    def _extract_album(self, info: Dict) -> str:
        """Extrai álbum das informações"""
        album = info.get('album') or info.get('playlist') or 'Unknown Album'
        
        if isinstance(album, list):
            album = album[0] if album else 'Unknown Album'
        
        return str(album).strip()
    
    def _get_best_thumbnail(self, info: Dict) -> str:
        """Obtém a melhor thumbnail disponível"""
        # Tenta diferentes tamanhos de thumbnail
        for key in ['thumbnail', 'thumbnails', 'thumbnail_url']:
            if key in info:
                thumb = info[key]
                if isinstance(thumb, str) and thumb:
                    return thumb
                elif isinstance(thumb, list) and thumb:
                    # Pega a última (geralmente a maior)
                    return thumb[-1].get('url', '') if isinstance(thumb[-1], dict) else str(thumb[-1])
        
        return ''
    
    def _extract_genre(self, info: Dict) -> str:
        """Extrai gênero das informações"""
        genre = info.get('genre') or info.get('category')
        
        if genre:
            if isinstance(genre, list):
                return ', '.join(str(g) for g in genre if g)
            return str(genre)
        
        # Tenta extrair de categorias
        if 'categories' in info:
            categories = info['categories']
            if isinstance(categories, list):
                return ', '.join(str(c) for c in categories if c)
            return str(categories)
        
        return 'Unknown'
    
    def _extract_year(self, info: Dict) -> str:
        """Extrai ano das informações"""
        # Tenta release_date primeiro
        if 'release_date' in info:
            date = str(info['release_date'])
            if len(date) >= 4:
                return date[:4]
        
        # Tenta upload_date
        if 'upload_date' in info:
            date = str(info['upload_date'])
            if len(date) >= 4:
                return date[:4]
        
        # Tenta release_year
        if 'release_year' in info:
            return str(info['release_year'])
        
        # Tenta extrair de data de publicação
        if 'release_timestamp' in info:
            import datetime
            try:
                dt = datetime.datetime.fromtimestamp(info['release_timestamp'])
                return str(dt.year)
            except:
                pass
        
        return ''
    
    def _download_thumbnail(self, url: str, output_path: str) -> bool:
        """Baixa a thumbnail/capa"""
        if not url:
            return False
            
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers, stream=True)
            if response.status_code == 200:
                # Verifica se é uma imagem válida
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type or url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as e:
            logger.error(f"Erro ao baixar thumbnail: {e}")
        return False
    
    def download_audio(self, url: str, output_format: str = "mp3", 
                      output_path: Optional[str] = None,
                      metadata: Optional[Dict] = None,
                      progress_callback_item: Optional[Callable] = None,
                      audio_quality: str = "192") -> Dict:
        """Baixa apenas o áudio (ou playlist completa)"""
        # Verifica se é playlist/mix/set ANTES de processar
        if self._is_playlist(url):
            logger.info("URL identificada como playlist/mix/set - processando como playlist")
            return self._download_playlist_audio(url, output_format, progress_callback_item, audio_quality)
        
        # Se não é playlist, processa como item único
        return self._download_single_audio(url, output_format, output_path, metadata, audio_quality)
    
    def _download_single_audio(self, url: str, output_format: str = "mp3", 
                               output_path: Optional[str] = None,
                               metadata: Optional[Dict] = None,
                               audio_quality: str = "192") -> Dict:
        """Baixa um único arquivo de áudio (não playlist)"""
        platform = self._get_platform(url)
        
        # Determina o nome do arquivo de saída
        if output_path is None:
            info = self._get_video_info(url)
            safe_title = self._sanitize_filename(info.get('title', 'audio'))
            output_path = os.path.join(self.download_dir, f"{safe_title}.{output_format}")
        else:
            # Garante que o formato está correto
            output_path = os.path.splitext(output_path)[0] + f".{output_format}"
        
        # Callback de progresso melhorado
        def progress_hook(d):
            if self.progress_callback:
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    speed = d.get('speed', 0)
                    
                    if total > 0:
                        percent = min(int((downloaded / total) * 100), 50)  # Limita a 50% para o download
                        # Formata tamanho
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        speed_mb = speed / (1024 * 1024) if speed else 0
                        
                        # Estima tempo restante
                        if speed and speed > 0:
                            remaining = (total - downloaded) / speed
                            if remaining < 60:
                                time_str = f"{int(remaining)}s"
                            elif remaining < 3600:
                                time_str = f"{int(remaining // 60)}min {int(remaining % 60)}s"
                            else:
                                time_str = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}min"
                        else:
                            time_str = "calculando..."
                        
                        detail = f"{downloaded_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mb:.1f}MB/s - Restam: {time_str}"
                        self.progress_callback(percent, f"📥 Baixando áudio...", detail)
                    else:
                        # Sem informação de tamanho total ainda
                        downloaded_mb = downloaded / (1024 * 1024) if downloaded else 0
                        self.progress_callback(10, f"📥 Baixando áudio...", f"{downloaded_mb:.1f}MB baixados...")
                elif d['status'] == 'finished':
                    self.progress_callback(50, "✅ Download concluído!", "Iniciando conversão...")
        
        # Estratégias: Com cookies, depois sem cookies
        strategies = [
            (True, "Com cookies"),
        ]
        if self.cookies_file:
            strategies.append((False, "Sem cookies"))
            
        last_error = None
        for use_cookies, strategy_name in strategies:
            try:
                # Opções do yt-dlp para áudio (FORÇA item único, não playlist)
                ydl_opts = self._get_base_opts(use_cookies=use_cookies)
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'outtmpl': output_path.replace(f'.{output_format}', '.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': output_format,
                        'preferredquality': audio_quality,
                    }],
                    'ffmpeg_location': os.path.dirname(self.ffmpeg_path),
                    'extractaudio': True,
                    'audioformat': output_format,
                    # Metadados adicionais
                    'writethumbnail': True,
                    'embedthumbnail': False,  # Vamos fazer isso manualmente depois
                    # IMPORTANTE: força download de item único, não playlist
                    'noplaylist': True,  # Não baixa playlist, apenas item único
                })
                ydl_opts['progress_hooks'] = [progress_hook]
                
                logger.info(f"Tentando download de áudio: {strategy_name}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                
                    # Procura o arquivo baixado
                    base_path = os.path.splitext(output_path)[0]
                    downloaded_file = None
                    
                    # Primeiro tenta o formato desejado
                    if os.path.exists(output_path):
                        downloaded_file = output_path
                    else:
                        # Procura por arquivos com extensões possíveis
                        for ext in [output_format, 'webm', 'm4a', 'mp3', 'opus', 'ogg']:
                            temp_file = f"{base_path}.{ext}"
                            if os.path.exists(temp_file):
                                downloaded_file = temp_file
                                break
                        
                        # Se ainda não encontrou, procura na pasta
                        if not downloaded_file:
                            dir_path = os.path.dirname(output_path)
                            base_name = os.path.basename(base_path)
                            for file in os.listdir(dir_path):
                                if file.startswith(base_name.split('\\')[-1].split('/')[-1]):
                                    downloaded_file = os.path.join(dir_path, file)
                                    break
                    
                    if not downloaded_file or not os.path.exists(downloaded_file):
                        downloaded_file = output_path
                    
                    # Obtém metadados se não foram fornecidos
                    final_metadata = metadata or self._get_video_info(url)
                    
                    # Cria o resultado
                    result = {
                        'success': True,
                        'file_path': downloaded_file if os.path.exists(downloaded_file) else output_path,
                        'metadata': final_metadata,
                        'platform': platform
                    }
                    
                    # Tenta encontrar thumbnail baixado pelo yt-dlp primeiro (mais confiável)
                    # Usa o base_path do arquivo baixado, não do output_path
                    downloaded_base_path = os.path.splitext(downloaded_file)[0]
                    thumbnail_path = None
                    
                    # Procura thumbnail baixado pelo yt-dlp no mesmo diretório do arquivo baixado
                    for ext in ['webp', 'jpg', 'jpeg', 'png']:
                        possible_thumb = f"{downloaded_base_path}.{ext}"
                        if os.path.exists(possible_thumb):
                            thumbnail_path = possible_thumb
                            break
                    
                    # Se não encontrou, tenta no base_path original também
                    if not thumbnail_path:
                        original_base_path = os.path.splitext(output_path)[0]
                        for ext in ['webp', 'jpg', 'jpeg', 'png']:
                            possible_thumb = f"{original_base_path}.{ext}"
                            if os.path.exists(possible_thumb):
                                thumbnail_path = possible_thumb
                                break
                    
                    # Se não encontrou, tenta baixar da URL
                    if not thumbnail_path and final_metadata.get('thumbnail'):
                        thumbnail_path = os.path.splitext(result['file_path'])[0] + '_cover.jpg'
                        if not self._download_thumbnail(final_metadata['thumbnail'], thumbnail_path):
                            thumbnail_path = None
                    
                    # Se encontrou, converte para JPG se necessário (para melhor compatibilidade)
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        if thumbnail_path.lower().endswith('.webp'):
                            # Converte WebP para JPG
                            try:
                                from PIL import Image
                                jpg_path = os.path.splitext(thumbnail_path)[0] + '.jpg'
                                img = Image.open(thumbnail_path)
                                # Converte RGBA para RGB se necessário
                                if img.mode == 'RGBA':
                                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                    rgb_img.paste(img, mask=img.split()[3])
                                    rgb_img.save(jpg_path, 'JPEG', quality=95)
                                else:
                                    img.convert('RGB').save(jpg_path, 'JPEG', quality=95)
                                # Remove WebP original
                                try:
                                    os.remove(thumbnail_path)
                                except:
                                    pass
                                thumbnail_path = jpg_path
                            except Exception as e:
                                logger.warning(f"Erro ao converter thumbnail WebP: {e}")
                        
                        result['thumbnail_path'] = thumbnail_path
                    
                    return result
            except Exception as e:
                error_str = str(e)
                last_error = e
                # Se for erro 403, Sign in ou formato indisponível
                if any(err in error_str for err in ['403', 'Forbidden', 'Requested format is not available', 'Sign in to confirm', 'challenge solving failed']):
                    logger.warning(f"Erro ({error_str.split(':')[0]}) com estratégia {strategy_name}, tentando próxima...")
                    continue  # Tenta próxima estratégia
                
                logger.warning(f"Erro com estratégia {strategy_name}: {e}")
                continue
        
        # Se chegou aqui, todas as tentativas falharam
        return {
            'success': False,
            'error': f"Falha após {len(strategies)} tentativas: {str(last_error) if last_error else 'Erro desconhecido'}",
            'platform': platform
        }
    
    def download_video(self, url: str, output_format: str = "mp4",
                      quality: str = "best",
                      output_path: Optional[str] = None) -> Dict:
        """Baixa vídeo"""
        platform = self._get_platform(url)
        
        if output_path is None:
            info = self._get_video_info(url)
            safe_title = self._sanitize_filename(info.get('title', 'video'))
            output_path = os.path.join(self.download_dir, f"{safe_title}.{output_format}")
        
        # Qualidade de vídeo com prioridade estrita para codec H.264 (ext=mp4) e áudio AAC (ext=m4a)
        # Isso previne que o Windows Media Player trave ao tentar reproduzir VP9 dentro de um container MP4
        format_selector = {
            'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best',
            '1080p': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/bestvideo[height<=1080]+bestaudio/best',
            '720p': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/bestvideo[height<=720]+bestaudio/best',
            '480p': 'bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][height<=480]/bestvideo[height<=480]+bestaudio/best',
            '360p': 'bestvideo[ext=mp4][height<=360]+bestaudio[ext=m4a]/best[ext=mp4][height<=360]/bestvideo[height<=360]+bestaudio/best',
        }
        
        def progress_hook(d):
            if self.progress_callback:
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    speed = d.get('speed', 0)
                    
                    if total > 0:
                        percent = min(int((downloaded / total) * 100), 50)  # Limita a 50% para o download
                        # Formata tamanho
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        speed_mb = speed / (1024 * 1024) if speed else 0
                        
                        # Estima tempo restante
                        if speed and speed > 0:
                            remaining = (total - downloaded) / speed
                            if remaining < 60:
                                time_str = f"{int(remaining)}s"
                            elif remaining < 3600:
                                time_str = f"{int(remaining // 60)}min {int(remaining % 60)}s"
                            else:
                                time_str = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}min"
                        else:
                            time_str = "calculando..."
                        
                        detail = f"{downloaded_mb:.1f}MB / {total_mb:.1f}MB @ {speed_mb:.1f}MB/s - Restam: {time_str}"
                        self.progress_callback(percent, f"📹 Baixando vídeo...", detail)
                    else:
                        downloaded_mb = downloaded / (1024 * 1024) if downloaded else 0
                        self.progress_callback(10, f"📹 Baixando vídeo...", f"{downloaded_mb:.1f}MB baixados...")
                elif d['status'] == 'finished':
                    self.progress_callback(50, "✅ Download concluído!", "Processando vídeo...")
        
        # Estratégias: Com cookies, depois sem cookies
        strategies = [
            (True, "Com cookies"),
        ]
        if self.cookies_file:
            strategies.append((False, "Sem cookies"))
            
        last_error = None
        for use_cookies, strategy_name in strategies:
            try:
                ydl_opts = self._get_base_opts(use_cookies=use_cookies)
                ydl_opts.update({
                    'format': format_selector.get(quality, format_selector['best']),
                    'outtmpl': output_path.replace(f'.{output_format}', '.%(ext)s'),
                    'merge_output_format': output_format,
                    'ffmpeg_location': os.path.dirname(self.ffmpeg_path),
                    'writethumbnail': True,
                    'noplaylist': True,
                    'postprocessors': [
                        {
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': output_format,
                        },
                        {
                            'key': 'FFmpegMetadata',
                            'add_metadata': True,
                        },
                        {
                            'key': 'EmbedThumbnail',
                        }
                    ]
                })
                ydl_opts['progress_hooks'] = [progress_hook]
                
                logger.info(f"Tentando download de vídeo: {strategy_name}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                
                    # Encontra o arquivo baixado
                    downloaded_file = output_path
                    if not os.path.exists(downloaded_file):
                        base_path = os.path.splitext(output_path)[0]
                        for ext in ['mp4', 'webm', 'mkv']:
                            temp_file = f"{base_path}.{ext}"
                            if os.path.exists(temp_file):
                                downloaded_file = temp_file
                                break
                    
                    # Registra a resolução real baixada
                    format_id = info.get('format_id', 'unknown')
                    resolution = info.get('resolution') or f"{info.get('width', '?')}x{info.get('height', '?')}"
                    logger.info(f"✅ Vídeo baixado com sucesso: {resolution} (Qualidade escolhida: {quality})")
                    
                    return {
                        'success': True,
                        'file_path': downloaded_file,
                        'metadata': self._build_metadata_from_info(info, url),
                        'platform': platform
                    }
            except Exception as e:
                error_str = str(e)
                last_error = e
                # Se for erro 403, Sign in ou formato indisponível
                if any(err in error_str for err in ['403', 'Forbidden', 'Requested format is not available', 'Sign in to confirm', 'challenge solving failed']):
                    logger.warning(f"Erro ({error_str.split(':')[0]}) com estratégia {strategy_name}, tentando próxima...")
                    continue  # Tenta próxima estratégia
                
                logger.warning(f"Erro com estratégia {strategy_name}: {e}")
                continue
        
        # Se chegou aqui, todas as tentativas falharam
        return {
            'success': False,
            'error': f"Falha após {len(strategies)} tentativas: {str(last_error) if last_error else 'Erro desconhecido'}",
            'platform': platform
        }
    
    def _download_playlist_audio(self, url: str, output_format: str = "mp3",
                                progress_callback_item: Optional[Callable] = None,
                                audio_quality: str = "192") -> Dict:
        """Baixa todos os itens de uma playlist/mix/set"""
        logger.info(f"Detectada playlist/mix/set: {url}")
        
        # Obtém informações da playlist
        playlist_info = self._get_playlist_info(url)
        if not playlist_info.get('is_playlist'):
            logger.warning("URL não identificada como playlist, tentando download único")
            return self._download_single_audio(url, output_format, None, None, audio_quality)
        
        entries = playlist_info.get('entries', [])
        if not entries:
            return {
                'success': False,
                'error': 'Nenhum item encontrado na playlist',
                'platform': self._get_platform(url)
            }
        
        total_items = len(entries)
        logger.info(f"Playlist contém {total_items} itens")
        
        # Remove duplicados baseado no ID
        seen_ids = set()
        unique_entries = []
        for entry in entries:
            if not entry:
                continue
            entry_id = entry.get('id') or entry.get('url', '')
            if entry_id and entry_id not in seen_ids:
                seen_ids.add(entry_id)
                unique_entries.append(entry)
            elif not entry_id:
                # Se não tem ID, usa título como identificador
                title = entry.get('title', '')
                if title and title not in seen_ids:
                    seen_ids.add(title)
                    unique_entries.append(entry)
        
        if len(unique_entries) < len(entries):
            logger.info(f"Removidos {len(entries) - len(unique_entries)} itens duplicados")
        
        # Baixa cada item
        results = []
        failed = []
        
        for idx, entry in enumerate(unique_entries, 1):
            try:
                # Obtém URL do item
                entry_url = entry.get('url') or entry.get('webpage_url')
                if not entry_url:
                    # Tenta construir URL do ID
                    entry_id = entry.get('id')
                    if entry_id:
                        platform = self._get_platform(url)
                        if 'soundcloud.com' in url.lower():
                            entry_url = f"https://soundcloud.com/{entry_id}"
                        elif 'youtube.com' in url.lower():
                            entry_url = f"https://www.youtube.com/watch?v={entry_id}"
                    else:
                        logger.warning(f"Item {idx} sem URL/ID válida, pulando")
                        failed.append({'index': idx, 'title': entry.get('title', 'Unknown'), 'error': 'URL/ID inválida'})
                        continue
                
                # Callback de progresso por item
                if progress_callback_item:
                    progress_callback_item(
                        idx,
                        total_items,
                        entry.get('title', f'Item {idx}'),
                        'Baixando...'
                    )
                
                # Baixa o item individual (usa função interna para evitar recursão)
                item_result = self._download_single_audio(
                    entry_url,
                    output_format,
                    None,
                    None,
                    audio_quality
                )
                
                if item_result.get('success'):
                    results.append({
                        'index': idx,
                        'title': item_result.get('metadata', {}).get('title', entry.get('title', 'Unknown')),
                        'file_path': item_result.get('file_path'),
                        'metadata': item_result.get('metadata', {})
                    })
                    logger.info(f"✅ Item {idx}/{total_items} baixado: {item_result.get('metadata', {}).get('title', 'Unknown')}")
                else:
                    failed.append({
                        'index': idx,
                        'title': entry.get('title', 'Unknown'),
                        'error': item_result.get('error', 'Erro desconhecido')
                    })
                    logger.warning(f"❌ Falha ao baixar item {idx}/{total_items}: {entry.get('title', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Erro ao processar item {idx}: {e}")
                failed.append({
                    'index': idx,
                    'title': entry.get('title', 'Unknown'),
                    'error': str(e)
                })
        
        return {
            'success': len(results) > 0,
            'is_playlist': True,
            'total_items': total_items,
            'downloaded': len(results),
            'failed': len(failed),
            'results': results,
            'failed_items': failed,
            'playlist_title': playlist_info.get('title', 'Unknown Playlist'),
            'platform': self._get_platform(url)
        }
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Remove caracteres inválidos do nome do arquivo"""
        # Remove caracteres especiais
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Limita o tamanho
        if len(filename) > 200:
            filename = filename[:200]
        return filename.strip()

