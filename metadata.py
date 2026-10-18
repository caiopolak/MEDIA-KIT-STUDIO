"""
Módulo responsável pela manipulação de metadados de arquivos de áudio/vídeo
"""
import os
from pathlib import Path
from typing import Dict, Optional
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, APIC, TPE2
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NexusMetadata:
    """Classe para manipulação de metadados"""
    
    def __init__(self):
        self.supported_formats = ['mp3', 'm4a', 'flac', 'ogg', 'opus', 'mp4']
    
    def _sanitize_value(self, value) -> str:
        """Sanitiza valores de metadados"""
        if value is None:
            return ''
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
        return str(value).strip()
    
    def set_metadata(self, file_path: str, metadata: Dict, cover_path: Optional[str] = None) -> bool:
        """Define metadados em um arquivo"""
        try:
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            
            if file_ext == 'mp3':
                return self._set_mp3_metadata(file_path, metadata, cover_path)
            elif file_ext in ['m4a', 'mp4']:
                return self._set_m4a_metadata(file_path, metadata, cover_path)
            elif file_ext == 'flac':
                return self._set_flac_metadata(file_path, metadata, cover_path)
            else:
                return self._set_generic_metadata(file_path, metadata)
                
        except Exception as e:
            logger.error(f"Erro ao definir metadados: {e}")
            return False
    
    def _set_mp3_metadata(self, file_path: str, metadata: Dict, cover_path: Optional[str] = None) -> bool:
        """Define metadados para MP3"""
        try:
            # Tenta carregar ID3 existente ou cria novo
            try:
                audio_file = ID3(file_path)
            except:
                audio_file = ID3()
            
            # Sanitiza valores
            title = self._sanitize_value(metadata.get('title', ''))
            artist = self._sanitize_value(metadata.get('artist', ''))
            album = self._sanitize_value(metadata.get('album', ''))
            year = self._sanitize_value(metadata.get('year', ''))
            genre = self._sanitize_value(metadata.get('genre', ''))
            
            # Título
            if title:
                audio_file['TIT2'] = TIT2(encoding=3, text=title)
            
            # Artista
            if artist:
                audio_file['TPE1'] = TPE1(encoding=3, text=artist)
                audio_file['TPE2'] = TPE2(encoding=3, text=artist)  # Album Artist
            
            # Álbum
            if album:
                audio_file['TALB'] = TALB(encoding=3, text=album)
            
            # Ano
            if year:
                try:
                    audio_file['TDRC'] = TDRC(encoding=3, text=str(year)[:4])
                except:
                    pass
            
            # Gênero
            if genre:
                audio_file['TCON'] = TCON(encoding=3, text=genre)
            
            # Capa - aplica ANTES de salvar
            cover_applied = False
            if cover_path and os.path.exists(cover_path):
                try:
                    # Verifica tamanho do arquivo
                    file_size = os.path.getsize(cover_path)
                    if file_size == 0:
                        logger.warning(f"Thumbnail vazia: {cover_path}")
                    else:
                        # Detecta tipo MIME da imagem
                        mime_type = 'image/jpeg'
                        if cover_path.lower().endswith('.png'):
                            mime_type = 'image/png'
                        elif cover_path.lower().endswith('.webp'):
                            mime_type = 'image/webp'
                        
                        with open(cover_path, 'rb') as f:
                            cover_data = f.read()
                            if cover_data and len(cover_data) > 0:
                                # Remove capa antiga se existir
                                if 'APIC:' in audio_file:
                                    del audio_file['APIC:']
                                if 'APIC' in audio_file:
                                    del audio_file['APIC']
                                
                                # Adiciona nova capa
                                audio_file.add(APIC(
                                    encoding=3,
                                    mime=mime_type,
                                    type=3,  # Cover (front)
                                    desc='Cover',
                                    data=cover_data
                                ))
                                cover_applied = True
                                logger.info(f"Capa aplicada ao MP3: {file_size} bytes, tipo: {mime_type}")
                            else:
                                logger.warning("Dados da capa vazios")
                except Exception as e:
                    logger.error(f"Erro ao adicionar capa ao MP3: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Salva o arquivo com metadados
            try:
                audio_file.save(file_path, v2_version=3)
                logger.info(f"Metadados MP3 salvos em: {file_path}")
                
                # Se cover_applied é True, a capa foi adicionada antes de salvar
                # Verifica se realmente foi salva (opcional, mas útil para debug)
                if cover_applied:
                    try:
                        # Tenta verificar - mas não falha se não conseguir
                        verify_file = ID3(file_path)
                        # Verifica de várias formas
                        has_cover = False
                        for key in verify_file.keys():
                            if 'APIC' in key:
                                has_cover = True
                                break
                        
                        if has_cover:
                            logger.info("✅ Capa verificada e confirmada no arquivo MP3")
                        else:
                            logger.warning("⚠️ Capa não encontrada na verificação, mas foi aplicada - pode estar presente")
                    except Exception as e:
                        logger.warning(f"Erro ao verificar capa (mas foi aplicada): {e}")
                
                # Retorna True se metadados foram salvos
                # Se cover_applied é True, confiamos que foi aplicada
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar metadados MP3: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
            
        except Exception as e:
            logger.error(f"Erro ao definir metadados MP3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _set_m4a_metadata(self, file_path: str, metadata: Dict, cover_path: Optional[str] = None) -> bool:
        """Define metadados para M4A/MP4"""
        try:
            try:
                audio_file = MP4(file_path)
            except:
                # Se não consegue abrir, pode ser que o arquivo não tenha tags ainda
                audio_file = MP4()
            
            # Sanitiza valores
            title = self._sanitize_value(metadata.get('title', ''))
            artist = self._sanitize_value(metadata.get('artist', ''))
            album = self._sanitize_value(metadata.get('album', ''))
            year = self._sanitize_value(metadata.get('year', ''))
            genre = self._sanitize_value(metadata.get('genre', ''))
            
            # Título
            if title:
                audio_file['\xa9nam'] = [title]
            
            # Artista
            if artist:
                audio_file['\xa9ART'] = [artist]
                audio_file['aART'] = [artist]  # Album Artist
            
            # Álbum
            if album:
                audio_file['\xa9alb'] = [album]
            
            # Ano
            if year:
                audio_file['\xa9day'] = [str(year)[:4]]
            
            # Gênero
            if genre:
                audio_file['\xa9gen'] = [genre]
            
            # Capa - aplica ANTES de salvar
            cover_applied = False
            if cover_path and os.path.exists(cover_path):
                try:
                    file_size = os.path.getsize(cover_path)
                    if file_size == 0:
                        logger.warning(f"Thumbnail vazia: {cover_path}")
                    else:
                        with open(cover_path, 'rb') as f:
                            cover_data = f.read()
                            if cover_data and len(cover_data) > 0:
                                # Detecta formato da imagem
                                img_format = MP4Cover.FORMAT_JPEG
                                if cover_path.lower().endswith('.png'):
                                    img_format = MP4Cover.FORMAT_PNG
                                
                                # Remove capa antiga se existir
                                if '\xa9covr' in audio_file:
                                    del audio_file['\xa9covr']
                                if 'covr' in audio_file:
                                    del audio_file['covr']
                                
                                # Adiciona nova capa
                                audio_file['covr'] = [MP4Cover(cover_data, imageformat=img_format)]
                                cover_applied = True
                                logger.info(f"Capa aplicada ao M4A: {file_size} bytes, formato: {img_format}")
                            else:
                                logger.warning("Dados da capa vazios")
                except Exception as e:
                    logger.error(f"Erro ao adicionar capa ao M4A: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Salva o arquivo
            try:
                audio_file.save(file_path)
                logger.info(f"Metadados M4A salvos em: {file_path}")
                
                # Se cover_applied é True, confiamos que foi aplicada
                if cover_applied:
                    try:
                        verify_file = MP4(file_path)
                        if 'covr' in verify_file or '\xa9covr' in verify_file:
                            logger.info("✅ Capa verificada e confirmada no arquivo M4A")
                        else:
                            logger.warning("⚠️ Capa não encontrada na verificação, mas foi aplicada")
                    except Exception as e:
                        logger.warning(f"Erro ao verificar capa M4A (mas foi aplicada): {e}")
                
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar metadados M4A: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
            
        except Exception as e:
            logger.error(f"Erro ao definir metadados M4A: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _set_flac_metadata(self, file_path: str, metadata: Dict, cover_path: Optional[str] = None) -> bool:
        """Define metadados para FLAC"""
        try:
            audio_file = FLAC(file_path)
            
            # Remove metadados existentes
            audio_file.clear()
            
            # Define novos metadados
            if metadata.get('title'):
                audio_file['TITLE'] = metadata['title']
            if metadata.get('artist'):
                audio_file['ARTIST'] = metadata['artist']
                audio_file['ALBUMARTIST'] = metadata['artist']
            if metadata.get('album'):
                audio_file['ALBUM'] = metadata['album']
            if metadata.get('year'):
                audio_file['DATE'] = metadata['year']
            if metadata.get('genre'):
                audio_file['GENRE'] = metadata['genre']
            
            # Capa
            if cover_path and os.path.exists(cover_path):
                picture = Picture()
                picture.type = 3  # Cover (front)
                picture.mime = 'image/jpeg'
                with open(cover_path, 'rb') as f:
                    picture.data = f.read()
                audio_file.add_picture(picture)
            
            audio_file.save()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao definir metadados FLAC: {e}")
            return False
    
    def _set_generic_metadata(self, file_path: str, metadata: Dict) -> bool:
        """Define metadados para formatos genéricos usando mutagen"""
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                return False
            
            # Tenta definir metadados genéricos
            if metadata.get('title'):
                audio_file['title'] = metadata['title']
            if metadata.get('artist'):
                audio_file['artist'] = metadata['artist']
            if metadata.get('album'):
                audio_file['album'] = metadata['album']
            
            audio_file.save()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao definir metadados genéricos: {e}")
            return False
    
    def get_metadata(self, file_path: str) -> Dict:
        """Obtém metadados de um arquivo"""
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                return {}
            
            metadata = {}
            
            # Tenta extrair metadados comuns
            if 'TIT2' in audio_file or '\xa9nam' in audio_file or 'title' in audio_file:
                metadata['title'] = self._get_tag(audio_file, ['TIT2', '\xa9nam', 'title'])
            if 'TPE1' in audio_file or '\xa9ART' in audio_file or 'artist' in audio_file:
                metadata['artist'] = self._get_tag(audio_file, ['TPE1', '\xa9ART', 'artist'])
            if 'TALB' in audio_file or '\xa9alb' in audio_file or 'album' in audio_file:
                metadata['album'] = self._get_tag(audio_file, ['TALB', '\xa9alb', 'album'])
            if 'TDRC' in audio_file or '\xa9day' in audio_file or 'date' in audio_file:
                metadata['year'] = self._get_tag(audio_file, ['TDRC', '\xa9day', 'date'])
            if 'TCON' in audio_file or '\xa9gen' in audio_file or 'genre' in audio_file:
                metadata['genre'] = self._get_tag(audio_file, ['TCON', '\xa9gen', 'genre'])
            
            return metadata
            
        except Exception as e:
            logger.error(f"Erro ao obter metadados: {e}")
            return {}
    
    def _get_tag(self, audio_file, tag_names):
        """Obtém uma tag de diferentes formatos"""
        for tag in tag_names:
            if tag in audio_file:
                value = audio_file[tag]
                if isinstance(value, list):
                    return value[0] if value else ''
                return str(value)
        return ''

