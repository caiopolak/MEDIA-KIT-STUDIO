# Nexus Media Studio 🎬🎵

![Versão](https://img.shields.io/badge/Versão-3.0.0-blue.svg)
![Status](https://img.shields.io/badge/Status-Comercial_Ready-success.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-yellow.svg)

O **Nexus Media Studio** (anteriormente Nexus Downloader & Conversor) é uma aplicação desktop comercial premium projetada para DJs, criadores de conteúdo e profissionais de mídia. Ele oferece download rápido, extração de áudio, conversão em múltiplos formatos e organização inteligente de bibliotecas a partir do YouTube, YouTube Music e SoundCloud.

## 🌟 Características Principais

* **Interface de Usuário Premium:** Construída com `CustomTkinter`, apresenta design responsivo, modo claro/escuro, e 4 temas comerciais (YouTube Clássico, SoundCloud, Indigo Premium, Violet Night).
* **Alta Qualidade Sem Compromisso:** Selecione a taxa de bits exata para áudio (até 320kbps) ou faça download de vídeo na melhor resolução possível sem perda de sincronia de áudio (usando FFmpeg).
* **Gestão Inteligente de Metadados:** Auto-preenchimento de ID3 Tags (Artista, Álbum, Gênero) e capa (Thumbnail) incorporada diretamente no arquivo MP3/M4A/FLAC.
* **Organização de Bibliotecas:** Criação automática de árvores de diretórios (ex: `Downloads / Artista / Álbum / Música.mp3`) para manter seu computador sempre organizado.
* **Segurança Baseada em Cookies:** O módulo nativo de cookies resolve o "Erro 403" do YouTube e permite downloads seguros de conteúdo privado e playlists.
* **Downloads em Lote:** Baixe playlists inteiras, álbuns de artistas e mixes pesados em um só clique.

## 🚀 Instalação e Execução

### Pré-requisitos
* Python 3.9 ou superior
* Gerenciador de pacotes `pip`
* (Recomendado) Arquivo de extensão do Chrome **Get cookies.txt LOCALLY** para exportação de sessão.

### Passos de Instalação

1. Clone o repositório ou faça download do pacote comercial:
   ```bash
   git clone https://github.com/caiopolak/MEDIA-KIT-STUDIO.git
   cd MEDIA-KIT-STUDIO
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. (Opcional mas exigido para conversão) Instale o FFmpeg:
   - Se você já tem a pasta `ffmpeg/bin` no diretório do projeto, o Nexus detectará automaticamente (Modo Portable).
   - Caso contrário, instale no seu sistema operacional e o adicione ao PATH global.

4. Execute a aplicação:
   ```bash
   python main.py
   ```

## 📖 Como Usar
Para obter instruções detalhadas sobre cada função, importação de cookies e configuração da organização automática, leia o nosso [Tutorial Completo (TUTORIAL.md)](TUTORIAL.md).

## 🛠 Arquitetura do Software

O software é construído em módulos para facilitar manutenibilidade:
* `main.py` & `gui.py`: Controle da interface e temas.
* `downloader.py`: Lógica de injeção no yt-dlp.
* `converter.py` & `metadata.py`: Processamento via FFmpeg e Mutagen (ID3/Tags).
* `organizer.py`: Gestão de FileSystem e criação de estrutura de pastas.
* `config.py`: Gestão de branding e variáveis de ambiente/caminhos.

## 📄 Direitos Autorais e Licenciamento
© 2024 Nexus Media Studio. Todos os direitos reservados.
Este software é um produto de código fechado. É terminantemente proibida a engenharia reversa, sub-licenciamento, cópia ou distribuição sem a autorização prévia por escrito.
