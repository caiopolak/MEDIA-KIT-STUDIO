"""
Módulo para processamento de cookies do navegador
Suporta formato Netscape (cookies.txt) usado por extensões como "cookies.txt" e "Get cookies.txt LOCALLY"
"""
import os
import logging
from typing import Optional, Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CookieProcessor:
    """Processa arquivos de cookies do navegador"""
    
    @staticmethod
    def validate_cookies_file(file_path: str) -> bool:
        """Valida se o arquivo de cookies é válido"""
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Lê as primeiras linhas para verificar formato
                lines = [f.readline() for _ in range(5)]
                
                # Verifica formato Netscape
                # Deve começar com comentário ou linha de cabeçalho
                first_lines = ''.join(lines).lower()
                
                # Verifica se contém campos de cookie comuns
                cookie_indicators = ['domain', 'path', 'secure', 'httponly', 'expires']
                if any(indicator in first_lines for indicator in cookie_indicators):
                    return True
                
                # Verifica formato Netscape (começa com comentário #)
                if any(line.strip().startswith('#') for line in lines):
                    # Procura por linhas de cookie (não comentário e tem tabs)
                    content_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                    if content_lines and '\t' in content_lines[0]:
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Erro ao validar arquivo de cookies: {e}")
            return False
    
    @staticmethod
    def get_cookies_file_path() -> Optional[str]:
        """Retorna o caminho do arquivo de cookies se existir"""
        # Procura em locais comuns
        possible_locations = [
            os.path.join(os.path.expanduser("~"), "Downloads", "cookies.txt"),
            os.path.join(os.path.expanduser("~"), "Desktop", "cookies.txt"),
            os.path.join(os.path.dirname(__file__), "cookies.txt"),
        ]
        
        for location in possible_locations:
            if os.path.exists(location) and CookieProcessor.validate_cookies_file(location):
                return location
        
        return None
    
    @staticmethod
    def parse_netscape_cookies(file_path: str) -> Dict:
        """Extrai informações básicas dos cookies para validação"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Conta domínios relevantes
            domains = {
                'youtube.com': 0,
                'google.com': 0,
                'soundcloud.com': 0
            }
            
            for domain in domains.keys():
                domains[domain] = content.lower().count(domain)
            
            return {
                'valid': True,
                'domains': domains,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar cookies: {e}")
            return {'valid': False, 'error': str(e)}
    
    @staticmethod
    def get_domain_from_url(url: str) -> str:
        """Extrai o domínio principal da URL"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube.com'
        elif 'soundcloud.com' in url:
            return 'soundcloud.com'
        return ''

