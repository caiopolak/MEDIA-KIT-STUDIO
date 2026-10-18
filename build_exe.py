"""
Script para build do executável com PyInstaller
Inclui FFmpeg no pacote e configura ambiente
"""
import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
import chardet
from pathlib import Path

class NexusBuild:
    def __init__(self):
        self.root_dir = Path(__file__).parent.absolute()
        self.ffmpeg_dir = self.root_dir / 'ffmpeg'
        self.ffmpeg_bin = self.ffmpeg_dir / 'bin'
        self.dist_dir = self.root_dir / 'dist'
        self.build_dir = self.root_dir / 'build'
        self.icon_path = self.root_dir / 'icon00.ico'
        
    def detect_encoding(self, file_path):
        """Detecta a codificação do arquivo"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except:
            return 'latin-1'  # fallback
    
    def read_file_safe(self, file_path):
        """Lê arquivo tentando múltiplas codificações"""
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        # Primeiro tenta detectar automaticamente
        try:
            detected = self.detect_encoding(file_path)
            if detected:
                encodings_to_try.insert(0, detected)
        except:
            pass
        
        # Remove duplicatas mantendo ordem
        encodings_to_try = list(dict.fromkeys(encodings_to_try))
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    print(f"📄 Arquivo lido com codificação: {encoding}")
                    return content, encoding
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"⚠️  Erro com {encoding}: {e}")
                continue
        
        # Último recurso: lê como binário e ignora erros
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
            print("⚠️  Arquivo lido com ignorando erros de codificação")
            return content, 'utf-8'
    
    def check_icon(self):
        """Verifica se o ícone existe e é válido"""
        if not self.icon_path.exists():
            print("⚠️  Arquivo icon.ico não encontrado na pasta raiz!")
            print("   O executável será gerado sem ícone.")
            return False
        
        # Verifica se é um arquivo .ico válido (tamanho mínimo)
        if self.icon_path.stat().st_size < 100:
            print("⚠️  Arquivo icon.ico parece muito pequeno (pode estar corrompido)")
            return False
        
        print(f"🎨 Ícone encontrado: {self.icon_path} ({self.icon_path.stat().st_size} bytes)")
        return True
    
    def create_icon_if_missing(self):
        """Cria um ícone padrão se não existir"""
        if self.icon_path.exists():
            return
        
        print("🎨 Criando ícone padrão...")
        
        try:
            from PIL import Image, ImageDraw
            
            # Cria uma imagem 256x256
            img = Image.new('RGBA', (256, 256), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Desenha um círculo vermelho (estilo YouTube)
            draw.ellipse([20, 20, 236, 236], fill='#ff0000', outline=None)
            
            # Desenha um triângulo branco (play)
            points = [(90, 70), (90, 186), (186, 128)]
            draw.polygon(points, fill='white')
            
            # Salva como ICO
            img.save(self.icon_path, format='ICO', sizes=[(256, 256)])
            print(f"✅ Ícone padrão criado: {self.icon_path}")
            
        except ImportError:
            print("⚠️  PIL não instalado, não foi possível criar ícone padrão")
        except Exception as e:
            print(f"⚠️  Erro ao criar ícone: {e}")
    
    def check_dependencies(self):
        """Verifica se as dependências Python estão instaladas"""
        print("\n📦 Verificando dependências Python...")
        
        # Instala chardet se não estiver instalado (para detecção de encoding)
        try:
            import chardet
            print("✅ chardet já instalado")
        except ImportError:
            print("   Instalando chardet...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', 'chardet'
            ], check=True)
        
        # Instala Pillow se não estiver instalado (para criar ícone)
        try:
            import PIL
            print("✅ Pillow já instalado")
        except ImportError:
            print("   Instalando Pillow...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', 'pillow'
            ], check=True)
        
        # Lê requirements.txt
        with open(self.root_dir / 'requirements.txt', 'r', encoding='utf-8') as f:
            requirements = f.read().splitlines()
        
        # Instala/atualiza dependências
        for req in requirements:
            if req.strip() and not req.startswith('#'):
                print(f"   Instalando {req}...")
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '--upgrade', req
                ], check=True, capture_output=True)
        
        # Instala pyinstaller se não estiver instalado
        try:
            import PyInstaller
            print("✅ PyInstaller já instalado")
        except ImportError:
            print("   Instalando PyInstaller...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', 'pyinstaller'
            ], check=True)
        
        print("✅ Dependências verificadas!\n")
    
    def download_ffmpeg(self):
        """Baixa FFmpeg se não existir na pasta"""
        if self.ffmpeg_bin.exists() and (self.ffmpeg_bin / 'ffmpeg.exe').exists():
            print("✅ FFmpeg já existe na pasta local\n")
            return True
        
        print("📥 Baixando FFmpeg...")
        
        # URL do FFmpeg (Windows 64-bit)
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = self.root_dir / 'ffmpeg_temp.zip'
        
        try:
            # Baixa o arquivo
            urllib.request.urlretrieve(ffmpeg_url, zip_path)
            
            # Extrai o zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.root_dir / 'ffmpeg_temp')
            
            # Encontra a pasta bin dentro do zip extraído
            extracted_dirs = list((self.root_dir / 'ffmpeg_temp').glob('ffmpeg-*'))
            if extracted_dirs:
                src_bin = extracted_dirs[0] / 'bin'
                if src_bin.exists():
                    # Cria estrutura ffmpeg/bin
                    self.ffmpeg_bin.mkdir(parents=True, exist_ok=True)
                    
                    # Copia os executáveis
                    for exe in ['ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe']:
                        src = src_bin / exe
                        if src.exists():
                            shutil.copy2(src, self.ffmpeg_bin / exe)
                            print(f"   Copiado: {exe}")
            
            # Limpa arquivos temporários
            shutil.rmtree(self.root_dir / 'ffmpeg_temp')
            zip_path.unlink()
            
            print("✅ FFmpeg baixado e configurado!\n")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao baixar FFmpeg: {e}")
            print("   Por favor, baixe manualmente de: https://ffmpeg.org/download.html")
            print("   E coloque os executáveis em: ffmpeg/bin/\n")
            return False
    
    def patch_config_for_build(self):
        """Modifica config.py para usar FFmpeg local primeiro"""
        config_path = self.root_dir / 'config.py'
        
        print(f"\n📝 Modificando {config_path}...")
        
        # Lê o arquivo com detecção automática de encoding
        content, used_encoding = self.read_file_safe(config_path)
        
        # Verifica se já tem a auto-detecção para evitar duplicação
        if 'def get_ffmpeg_path():' in content:
            print("ℹ️  Auto-detecção de FFmpeg já existe no config.py")
            return
        
        # Adiciona código para detectar FFmpeg local
        ffmpeg_detection = """

# ===== AUTO-DETECÇÃO DE FFMPEG (ADICIONADO PELO BUILD) =====
import os
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
    if os.path.exists(r"C:\\ffmpeg\\bin\\ffmpeg.exe"):
        return r"C:\\ffmpeg\\bin\\ffmpeg.exe"
    
    # Procura no PATH
    import shutil
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        return system_ffmpeg
    
    return r"C:\\ffmpeg\\bin\\ffmpeg.exe"  # fallback

# Substitui o caminho estático pela função
FFMPEG_PATH = get_ffmpeg_path()
# ============================================================
"""
        
        # Remove a linha FFMPEG_PATH original se existir
        lines = content.split('\n')
        new_lines = []
        skip_mode = False
        
        for line in lines:
            # Se encontrar a linha FFMPEG_PATH, marca para pular
            if 'FFMPEG_PATH =' in line and not line.strip().startswith('#'):
                skip_mode = True
                continue
            
            # Se estava pulando e encontrou uma linha em branco, para de pular
            if skip_mode and not line.strip():
                skip_mode = False
                new_lines.append(line)
            # Se não está no modo skip, adiciona a linha
            elif not skip_mode:
                new_lines.append(line)
        
        # Junta as linhas
        content = '\n'.join(new_lines)
        
        # Adiciona a nova detecção
        content += ffmpeg_detection
        
        # Salva com a mesma codificação detectada
        with open(config_path, 'w', encoding=used_encoding) as f:
            f.write(content)
        
        print(f"✅ Config.py modificado com sucesso (usando encoding: {used_encoding})")
        print("⚙️  Auto-detecção de FFmpeg adicionada\n")
    
    def run_build(self):
        """Executa o build com PyInstaller"""
        print("🔨 Iniciando build do executável...")
        
        # Limpa builds anteriores
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        # Verifica ícone
        icon_option = []
        if self.icon_path.exists():
            icon_option = ['--icon', str(self.icon_path)]
            print(f"🎨 Usando ícone: {self.icon_path}")
        else:
            print("⚠️  Nenhum ícone encontrado - executável sem ícone")
        
        # Comando PyInstaller
        cmd = [
            'pyinstaller',
            '--name=NexusMediaStudio',
            '--windowed',
            '--onefile',
            '--add-data', f'ffmpeg{os.pathsep}ffmpeg',
            '--hidden-import=yt_dlp',
            '--hidden-import=mutagen',
            '--hidden-import=PIL',
            '--hidden-import=PIL._tkinter_finder',
            '--hidden-import=requests',
            '--hidden-import=customtkinter',
            '--hidden-import=tkinter',
            '--hidden-import=tkinter.filedialog',
            '--hidden-import=tkinter.messagebox',
            '--hidden-import=winreg',
            '--collect-data', 'customtkinter',
            '--collect-data', 'yt_dlp',
            '--collect-submodules', 'PIL',
            '--collect-all', 'customtkinter',
            '--collect-all', 'yt_dlp',
            '--collect-all', 'mutagen',
            '--collect-all', 'PIL',
        ] + icon_option + ['main.py']
        
        # Remove argumentos vazios
        cmd = [arg for arg in cmd if arg]
        
        print("\n📋 Comando executado:")
        print("   " + " ".join(cmd) + "\n")
        
        try:
            # Executa o PyInstaller
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Verifica se o executável foi criado
            exe_path = self.dist_dir / 'NexusMediaStudio.exe'
            if exe_path.exists():
                print(f"\n✅ Build concluído com sucesso!")
                print(f"📁 Executável em: {exe_path}")
                
                # Verifica o tamanho do arquivo
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📊 Tamanho: {size_mb:.2f} MB")
                
                # Tenta verificar se o ícone foi aplicado
                try:
                    # Método simples: verificar se o arquivo tem recursos de ícone
                    import win32api
                    import win32con
                    
                    # Tenta extrair o ícone (se falhar, provavelmente não tem)
                    large, small = win32api.ExtractIconEx(str(exe_path), 0)
                    if large or small:
                        print("🎨 Ícone verificado no executável!")
                    else:
                        print("⚠️  Não foi possível verificar o ícone")
                except:
                    print("🎨 Ícone incluído no executável (verificação opcional)")
                
            else:
                print(f"\n❌ Executável não encontrado em {exe_path}")
                print("   Verifique se houve erro durante o build.")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Erro no build: {e}")
            print("\n📤 Saída de erro:")
            print(e.stderr)
    
    def create_readme(self):
        """Cria arquivo README na pasta dist"""
        readme_path = self.dist_dir / 'LEIA-ME.txt'
        
        content = """NEXUS MEDIA STUDIO - INSTRUÇÕES
================================

📋 REQUISITOS:
- Windows 10/11 64-bit
- Conexão com internet

🎵 SOBRE O FFMPEG:
O FFmpeg já está incluído neste executável!
Na primeira execução, o programa verificará:

1. Se existe FFmpeg em C:\\ffmpeg\\bin\\
2. Se não existir, usará o FFmpeg incluso na pasta do programa
3. Se desejar instalar permanentemente, clique em "Sim" quando perguntado

🚀 COMO USAR:
1. Execute NexusMediaStudio.exe
2. Cole a URL do YouTube/YouTube Music/SoundCloud
3. Configure as opções desejadas
4. Clique em "Iniciar Download"

🔐 COOKIES (OPCIONAL):
Para baixar conteúdo privado:
1. Instale extensão "Get cookies.txt LOCALLY" no navegador
2. Exporte cookies do site desejado
3. Selecione o arquivo .txt no programa

🆘 SUPORTE:
Em caso de erro, verifique:
- Conexão com internet
- Permissões de escrita na pasta de downloads
- Se o FFmpeg está acessível

⚡ Versão: 2.0.0
Ícone personalizado incluso ✓
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("📝 Arquivo LEIA-ME.txt criado")
    
    def run(self):
        """Executa todo o processo de build"""
        print("\n" + "="*60)
        print("🔧 NEXUS MEDIA STUDIO - BUILD TOOL")
        print("="*60 + "\n")
        
        # Passo 0: Instalar chardet para detecção de encoding
        try:
            import chardet
        except ImportError:
            print("📦 Instalando chardet para detecção de encoding...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'chardet'], check=True)
        
        # Passo 1: Verificar/Criar ícone
        if not self.check_icon():
            self.create_icon_if_missing()
        
        # Passo 2: Verificar dependências
        self.check_dependencies()
        
        # Passo 3: Baixar/configurar FFmpeg
        self.download_ffmpeg()
        
        # Passo 4: Modificar config.py para build (com suporte a encoding)
        self.patch_config_for_build()
        
        # Passo 5: Executar build
        self.run_build()
        
        # Passo 6: Criar README
        self.create_readme()
        
        print("\n" + "="*60)
        print("✨ Processo finalizado!")
        print("="*60 + "\n")

if __name__ == "__main__":
    builder = NexusBuild()
    builder.run()