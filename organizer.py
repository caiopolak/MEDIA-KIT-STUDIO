"""
Módulo responsável pela organização de arquivos em pastas
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NexusOrganizer:
    """Classe para organização de arquivos"""
    
    def __init__(self, base_dir: str, folder_structure: Dict = None):
        self.base_dir = base_dir
        self.folder_structure = folder_structure or {
            "artista": True,
            "album": True,
            "genero": False,
            "ano": False
        }
        self._ensure_base_dir()
    
    def _ensure_base_dir(self):
        """Garante que o diretório base existe"""
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)
    
    def _sanitize_folder_name(self, name: str) -> str:
        """Remove caracteres inválidos do nome da pasta"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Remove espaços múltiplos
        name = ' '.join(name.split())
        # Limita tamanho
        if len(name) > 100:
            name = name[:100]
        return name.strip() or "Unknown"
    
    def _build_folder_path(self, metadata: Dict) -> str:
        """Constrói o caminho da pasta baseado na estrutura e metadados"""
        path_parts = [self.base_dir]
        
        # Artista
        if self.folder_structure.get("artista", True):
            artist = self._sanitize_folder_name(
                metadata.get('artist') or metadata.get('uploader') or 'Unknown Artist'
            )
            path_parts.append(artist)
        
        # Gênero
        if self.folder_structure.get("genero", False):
            genre = self._sanitize_folder_name(
                metadata.get('genre') or 'Unknown Genre'
            )
            path_parts.append(genre)
        
        # Ano
        if self.folder_structure.get("ano", False):
            year = metadata.get('year') or metadata.get('upload_date', '')[:4] or 'Unknown'
            if year:
                path_parts.append(str(year))
        
        # Álbum
        if self.folder_structure.get("album", True):
            album = self._sanitize_folder_name(
                metadata.get('album') or 'Unknown Album'
            )
            path_parts.append(album)
        
        return os.path.join(*path_parts)
    
    def organize_file(self, file_path: str, metadata: Dict, 
                     cover_path: Optional[str] = None,
                     playlist_name: Optional[str] = None) -> Dict:
        """Organiza um arquivo na estrutura de pastas
        
        Args:
            file_path: Caminho do arquivo
            metadata: Metadados do arquivo
            cover_path: Caminho da capa (opcional)
            playlist_name: Nome da playlist/álbum/mix (se fornecido, todos vão para a mesma pasta)
        """
        try:
            if not os.path.exists(file_path):
                return {'success': False, 'error': 'Arquivo não encontrado'}
            
            # Se tem playlist_name, organiza todos na mesma pasta
            if playlist_name:
                dest_folder = self._build_playlist_folder_path(playlist_name)
            else:
                # Constrói caminho de destino normal (por artista/álbum)
                dest_folder = self._build_folder_path(metadata)
            
            os.makedirs(dest_folder, exist_ok=True)
            
            # Nome do arquivo
            filename = os.path.basename(file_path)
            
            # Move arquivo
            dest_path = os.path.join(dest_folder, filename)
            
            # Se já existe, adiciona número
            if os.path.exists(dest_path) and dest_path != file_path:
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    new_filename = f"{base} ({counter}){ext}"
                    dest_path = os.path.join(dest_folder, new_filename)
                    counter += 1
            
            # Move ou copia arquivo
            if dest_path != file_path:
                shutil.move(file_path, dest_path)
            
            # NÃO move a cover aqui - ela será aplicada nos metadados e depois deletada
            # Isso evita duplicação de thumbnails
            cover_dest_path = cover_path  # Mantém o caminho original
            
            return {
                'success': True,
                'file_path': dest_path,
                'folder': dest_folder,
                'cover_path': cover_dest_path
            }
            
        except Exception as e:
            logger.error(f"Erro ao organizar arquivo: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_playlist_folder_path(self, playlist_name: str) -> str:
        """Constrói caminho para playlist/álbum/mix (todos na mesma pasta)"""
        sanitized_name = self._sanitize_folder_name(playlist_name)
        return os.path.join(self.base_dir, sanitized_name)
    
    def organize_playlist(self, files: list, playlist_name: str) -> Dict:
        """Organiza múltiplos arquivos de uma playlist na mesma pasta
        
        Args:
            files: Lista de dicts com 'file_path', 'metadata', 'cover_path'
            playlist_name: Nome da playlist/álbum/mix
        
        Returns:
            Dict com resultados da organização
        """
        playlist_folder = self._build_playlist_folder_path(playlist_name)
        os.makedirs(playlist_folder, exist_ok=True)
        
        results = []
        for item in files:
            file_path = item.get('file_path')
            metadata = item.get('metadata', {})
            cover_path = item.get('cover_path')
            
            if not file_path or not os.path.exists(file_path):
                continue
            
            try:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(playlist_folder, filename)
                
                # Se já existe, adiciona número
                if os.path.exists(dest_path) and dest_path != file_path:
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        new_filename = f"{base} ({counter}){ext}"
                        dest_path = os.path.join(playlist_folder, new_filename)
                        counter += 1
                
                # Move arquivo
                if dest_path != file_path:
                    shutil.move(file_path, dest_path)
                
                results.append({
                    'success': True,
                    'file_path': dest_path,
                    'original_path': file_path,
                    'metadata': metadata
                })
                
            except Exception as e:
                logger.error(f"Erro ao organizar arquivo da playlist: {e}")
                results.append({
                    'success': False,
                    'file_path': file_path,
                    'error': str(e)
                })
        
        return {
            'success': len(results) > 0,
            'playlist_folder': playlist_folder,
            'items': results,
            'total': len(files),
            'organized': len([r for r in results if r.get('success')])
        }
    
    def get_organized_path(self, metadata: Dict, filename: str, playlist_name: Optional[str] = None) -> str:
        """Retorna o caminho onde um arquivo deveria ser organizado"""
        if playlist_name:
            dest_folder = self._build_playlist_folder_path(playlist_name)
        else:
            dest_folder = self._build_folder_path(metadata)
        return os.path.join(dest_folder, filename)

