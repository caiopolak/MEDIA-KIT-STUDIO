"""
Interface gráfica moderna usando CustomTkinter
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime
import sys

from downloader import NexusDownloader
from converter import NexusConverter
from metadata import NexusMetadata
from organizer import NexusOrganizer
from cookies import CookieProcessor
import config

# Import para verificação de capa
try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogHandler(logging.Handler):
    """Handler customizado para capturar logs e enviar para a interface"""
    def __init__(self, log_callback):
        super().__init__()
        self.log_callback = log_callback
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
    
    def emit(self, record):
        try:
            msg = self.format(record)
            if self.log_callback:
                self.log_callback(msg, record.levelname)
        except:
            pass


class NexusDownloaderApp:
    """Aplicativo principal com interface gráfica"""
    
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(f"{config.APP_NAME} v{config.APP_VERSION}")

        # Estado de tema (claro/escuro) – controlado por toggle no header
        self.current_theme = config.THEME_MODE

        # Preferências persistentes do usuário
        self.user_settings = self._load_user_settings()
        self.site_theme = self.user_settings.get("site_theme", config.DEFAULT_SITE_THEME)

        # Configurar tema do CustomTkinter (YouTube‑like / SoundCloud‑like)
        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme(config.COLOR_THEME)

        # Cor de fundo geral
        self.root.configure(fg_color=("#f9f9f9", "#0f0f0f"))
        
        # Detecta tamanho da tela e ajusta
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Tamanho adaptável baseado na tela
        if screen_width < 1366:  # Tela pequena
            width = int(screen_width * 0.95)
            height = int(screen_height * 0.9)
        else:  # Tela normal/grande
            width = 1000
            height = 700
        
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(600, 500)  # Tamanho mínimo menor
        self.root.maxsize(screen_width, screen_height)
        
        # Centraliza na tela
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Inicializar componentes
        self.downloader = None
        self.converter = NexusConverter(config.FFMPEG_PATH)
        self.metadata_manager = NexusMetadata()
        self.organizer = None

        # Variáveis do conversor de mídia
        self.converter_source_path = None
        self.converter_output_path = None
        self.converter_running = False

        # Variáveis de controle
        self.download_dir = config.DEFAULT_DOWNLOAD_DIR
        self.current_url = ""
        self.download_type = "audio"  # audio ou video
        self.output_format = "mp3"
        self.video_quality = "best"
        self.cookies_file = None
        self.cookies_provider = None  # "youtube" ou "soundcloud"
        
        # Carrega cookies salvos automaticamente
        saved_cookies = self.user_settings.get("cookies", {})
        if saved_cookies:
            self.cookies_file = saved_cookies.get("file_path")
            self.cookies_provider = saved_cookies.get("provider")
        
        # Configurar handler de logs
        self.log_handler = None
        self.log_messages = []  # passa a armazenar dicts: {"text": str, "level": str}
        self.max_log_lines = 500
        
        # Criar interface
        self._create_widgets()
        # Aplica tema visual baseado na preferência/último site
        self._set_site_theme(self.site_theme, save_default=False)
        self._setup_logging()
        self._create_onboarding()
        
    def _create_onboarding(self):
        """Cria janela de onboarding na primeira execução"""
        if self.user_settings.get("onboarding_completed") == getattr(config, 'ONBOARDING_VERSION', 1):
            return
            
        self.onboarding = ctk.CTkToplevel(self.root)
        self.onboarding.title(f"Bem-vindo ao {config.APP_NAME}!")
        self.onboarding.geometry("650x550")
        self.onboarding.transient(self.root)
        self.onboarding.grab_set()
        
        # Centralizar janela
        self.onboarding.update_idletasks()
        x = (self.onboarding.winfo_screenwidth() // 2) - (650 // 2)
        y = (self.onboarding.winfo_screenheight() // 2) - (550 // 2)
        self.onboarding.geometry(f"650x550+{x}+{y}")
        
        # Estrutura dos slides
        self.current_slide = 0
        self.slides = []
        
        container = ctk.CTkFrame(self.onboarding, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Slide 1: Bem-vindo
        slide1 = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(slide1, text="🎵", font=ctk.CTkFont(size=64)).pack(pady=(20, 10))
        ctk.CTkLabel(slide1, text=f"Bem-vindo ao {config.APP_NAME}", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=10)
        ctk.CTkLabel(
            slide1, 
            text="Seu estúdio completo para download, conversão e organização de mídia com qualidade profissional.",
            font=ctk.CTkFont(size=14), text_color="gray", wraplength=500, justify="center"
        ).pack(pady=20)
        self.slides.append(slide1)
        
        # Slide 2: Funcionalidades
        slide2 = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(slide2, text="✨ Como Funciona", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 20))
        
        features_frame = ctk.CTkFrame(slide2, fg_color=("gray90", "gray15"), corner_radius=15)
        features_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        features = [
            ("1. Cole a URL", "Suporte nativo para YouTube, YT Music e SoundCloud."),
            ("2. Escolha o Formato", "Áudio (MP3, FLAC, WAV...) ou Vídeo (até 4K)."),
            ("3. Organização Automática", "Metadados, capas de álbum e pastas criadas para você.")
        ]
        
        for title, desc in features:
            f = ctk.CTkFrame(features_frame, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=15)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(f, text=desc, font=ctk.CTkFont(size=13), text_color="gray", anchor="w").pack(fill="x")
            
        self.slides.append(slide2)
        
        # Slide 3: Cookies
        slide3 = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(slide3, text="🔐 Downloads Privados", font=ctk.CTkFont(size=24, weight="bold"), text_color=("#dc2626", "#fca5a5")).pack(pady=(20, 15))
        
        ctk.CTkLabel(
            slide3,
            text="Para baixar playlists privadas, músicas curtidas ou vídeos com restrição de idade, o Nexus precisa da sua autorização através de Cookies.",
            font=ctk.CTkFont(size=14), wraplength=550, justify="center"
        ).pack(pady=10)
        
        cookies_frame = ctk.CTkFrame(slide3, fg_color=("gray90", "gray15"), corner_radius=10)
        cookies_frame.pack(fill="x", padx=30, pady=15)
        
        steps = [
            "1. Use a extensão 'Get cookies.txt LOCALLY' no seu navegador",
            "2. Exporte os cookies do YouTube ou SoundCloud",
            "3. Clique em 'Importar Cookies' no painel principal do Nexus"
        ]
        
        for step in steps:
            ctk.CTkLabel(cookies_frame, text=step, font=ctk.CTkFont(size=13), anchor="w").pack(fill="x", padx=15, pady=8)
            
        self.slides.append(slide3)
        
        # Navegação
        self.nav_frame = ctk.CTkFrame(self.onboarding, fg_color="transparent", height=60)
        self.nav_frame.pack(fill="x", side="bottom", padx=30, pady=20)
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="Voltar", command=self._prev_slide, width=100, fg_color="gray")
        self.btn_prev.pack(side="left")
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="Próximo", command=self._next_slide, width=120)
        self.btn_next.pack(side="right")
        
        # Mostra o primeiro slide
        self._show_slide(0)
        
    def _show_slide(self, index):
        for i, slide in enumerate(self.slides):
            if i == index:
                slide.pack(fill="both", expand=True)
            else:
                slide.pack_forget()
                
        self.btn_prev.configure(state="normal" if index > 0 else "disabled")
        
        palette = self._get_site_palette(self.site_theme)
        if index == len(self.slides) - 1:
            self.btn_next.configure(text="Começar!", fg_color=palette["accent"], hover_color=palette["accent_hover"])
        else:
            self.btn_next.configure(text="Próximo", fg_color=("#3b82f6", "#2563eb"), hover_color=("#2563eb", "#1d4ed8"))
            
    def _next_slide(self):
        if self.current_slide < len(self.slides) - 1:
            self.current_slide += 1
            self._show_slide(self.current_slide)
        else:
            self._finish_onboarding()
            
    def _prev_slide(self):
        if self.current_slide > 0:
            self.current_slide -= 1
            self._show_slide(self.current_slide)
            
    def _finish_onboarding(self):
        self.user_settings["onboarding_completed"] = getattr(config, 'ONBOARDING_VERSION', 1)
        self._save_user_settings()
        self.onboarding.destroy()
    
    def _create_widgets(self):
        """Cria todos os widgets da interface"""
        
        # Frame principal com scroll (usando CTkScrollableFrame)
        main_frame = ctk.CTkScrollableFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header principal
        self.header_frame = ctk.CTkFrame(
            main_frame,
            fg_color=("#ffffff", "#181818"),
            corner_radius=12
        )
        self.header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # “Logo” estilo app (YouTube-like)
        logo_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        logo_frame.pack(side="left", padx=20, pady=10)

        self.logo_icon = ctk.CTkLabel(
            logo_frame,
            text="▶",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=("#dc2626", "#f97373")
        )
        self.logo_icon.pack(side="left", padx=(0, 6))

        title_label = ctk.CTkLabel(
            logo_frame,
            text="Nexus",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#000000", "#ffffff")
        )
        title_label.pack(side="left")

        subtitle_label = ctk.CTkLabel(
            logo_frame,
            text="Downloader & Converter",
            font=ctk.CTkFont(size=11),
            text_color=("#6b7280", "#9ca3af")
        )
        subtitle_label.pack(anchor="w")

        # Container à direita do header (versão + sobre + toggle de tema)
        header_right = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_right.pack(side="right", padx=20, pady=10)

        about_btn = ctk.CTkButton(
            header_right,
            text="ℹ Sobre",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._show_about,
            fg_color=("gray90", "#202020"),
            hover_color=("gray80", "#303030"),
            text_color=("#000000", "#ffffff"),
            corner_radius=20,
            border_width=1,
            border_color=("#d0d0d0", "#404040")
        )
        about_btn.pack(side="right", padx=(0, 8))

        # Toggle claro/escuro no header
        self.theme_toggle_btn = ctk.CTkButton(
            header_right,
            text="🌙 Escuro" if self.current_theme == "dark" else "☀️ Claro",
            command=self._toggle_theme,
            width=100,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray90", "#202020"),
            hover_color=("gray80", "#303030"),
            text_color=("#000000", "#ffffff"),
            corner_radius=20,
            border_width=1,
            border_color=("#d0d0d0", "#404040")
        )
        self.theme_toggle_btn.pack(side="right", padx=(0, 10))

        version_label = ctk.CTkLabel(
            header_right,
            text=f"v{config.APP_VERSION}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#b0b0b0", "#aaaaaa"),
            fg_color=("#f1f1f1", "#202020"),
            corner_radius=8,
            width=70,
            height=25
        )
        version_label.pack(side="right")

        # CARD 0 – Cookies (PRIMEIRO E MAIS VISÍVEL)
        cookies_card = ctk.CTkFrame(
            main_frame,
            fg_color=("#fff5f5", "#1f1f1f"),
            corner_radius=12,
            border_width=2,
            border_color=("#fecaca", "#7f1d1d")
        )
        cookies_card.pack(fill="x", padx=10, pady=(0, 10))

        cookies_header = ctk.CTkFrame(cookies_card, fg_color="transparent")
        cookies_header.pack(fill="x", padx=18, pady=(18, 8))

        cookies_title = ctk.CTkLabel(
            cookies_header,
            text="🔐 Importar Cookies",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#dc2626", "#fca5a5")
        )
        cookies_title.pack(side="left")

        # Badge de status dos cookies
        self.cookies_status_badge = ctk.CTkLabel(
            cookies_header,
            text="⚠️ Não configurado",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#fee2e2", "#7f1d1d"),
            text_color=("#b91c1c", "#fca5a5"),
            corner_radius=12,
            padx=10,
            pady=4
        )
        self.cookies_status_badge.pack(side="right")

        cookies_info_label = ctk.CTkLabel(
            cookies_card,
            text="Os cookies são obrigatórios para evitar erros HTTP e acessar conteúdo privado. Eles são salvos automaticamente para uso futuro.",
            font=ctk.CTkFont(size=12),
            text_color=("#6b7280", "#9ca3af"),
            anchor="w",
            justify="left",
            wraplength=800
        )
        cookies_info_label.pack(anchor="w", padx=18, pady=(0, 12))

        cookies_input_frame = ctk.CTkFrame(cookies_card, fg_color="transparent")
        cookies_input_frame.pack(fill="x", padx=18, pady=(0, 18))

        self.cookies_entry = ctk.CTkEntry(
            cookies_input_frame,
            placeholder_text="Nenhum arquivo de cookies selecionado",
            height=42,
            font=ctk.CTkFont(size=12),
            fg_color=("white", "gray25"),
            border_color=("#d1d5d6", "gray40"),
            border_width=2
        )
        self.cookies_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Se já tem cookies carregados, mostra no entry
        if self.cookies_file and os.path.exists(self.cookies_file):
            self.cookies_entry.insert(0, os.path.basename(self.cookies_file))
            provider_name = "YouTube" if self.cookies_provider == "youtube" else "SoundCloud" if self.cookies_provider == "soundcloud" else "Desconhecido"
            self.cookies_status_badge.configure(
                text=f"✅ {provider_name}",
                fg_color=("#d1fae5", "#064e3b"),
                text_color=("#065f46", "#6ee7b7")
            )

        self.cookies_browse_btn = ctk.CTkButton(
            cookies_input_frame,
            text="📁 Selecionar",
            command=self._browse_cookies_file,
            width=130,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#ef4444", "#dc2626"),
            hover_color=("#dc2626", "#b91c1c"),
            corner_radius=8
        )
        self.cookies_browse_btn.pack(side="right", padx=(0, 10))
        
        cookies_clear_btn = ctk.CTkButton(
            cookies_input_frame,
            text="🗑️ Limpar",
            command=self._clear_cookies_file,
            width=100,
            height=42,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            corner_radius=8
        )
        cookies_clear_btn.pack(side="right")

        # Pequeno texto de ajuda
        cookies_help_text = ctk.CTkLabel(
            cookies_card,
            text="💡 Use extensões como 'cookies.txt' ou 'Get cookies.txt LOCALLY' para exportar cookies do navegador",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
            anchor="w",
            justify="left"
        )
        cookies_help_text.pack(anchor="w", padx=18, pady=(0, 18))

        # Faixa de “status rápido”
        self.status_frame = ctk.CTkFrame(
            main_frame,
            fg_color=("#f1f1f1", "#202020"),
            corner_radius=10
        )
        self.status_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=f"📂 Pasta atual: {self.download_dir}",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.status_label.pack(fill="x", padx=15, pady=(8, 2))
        
        # CARD 1 – Download Rápido (URL + opções básicas)
        quick_card = ctk.CTkFrame(
            main_frame,
            fg_color=("white", "gray19"),
            corner_radius=12,
            border_width=1,
            border_color=("#e5e7eb", "gray30")
        )
        quick_card.pack(fill="x", padx=10, pady=(0, 10))

        # URL Input Section dentro do card
        url_frame = ctk.CTkFrame(quick_card, fg_color="transparent")
        url_frame.pack(fill="x", padx=0, pady=(10, 5))
        
        url_label = ctk.CTkLabel(
            url_frame,
            text="🔗 URL do Vídeo/Música",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#2c3e50", "#ecf0f1")
        )
        url_label.pack(anchor="w", padx=18, pady=(18, 8))
        
        url_input_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        url_input_frame.pack(fill="x", padx=18, pady=(0, 18))
        
        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="Cole a URL do YouTube, YouTube Music ou SoundCloud aqui...",
            height=42,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            border_width=2,
            fg_color=("white", "gray25"),
            border_color=("gray80", "gray40")
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.fetch_info_btn = ctk.CTkButton(
            url_input_frame,
            text="🔍 Buscar",
            command=self._fetch_info,
            width=130,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#ef4444", "#dc2626"),  # vermelho estilo YouTube
            hover_color=("#dc2626", "#b91c1c"),
            corner_radius=8
        )
        self.fetch_info_btn.pack(side="right")
        
        # Info Display – fica logo abaixo do card de download rápido
        self.info_frame = ctk.CTkFrame(
            main_frame,
            fg_color=("white", "gray19"),
            corner_radius=12,
            border_width=1,
            border_color=("#e5e7eb", "gray30")
        )
        # Inicialmente vazio e escondido - será preenchido após buscar info
        self.info_frame.pack_forget()
        
        # CARD 2 – Opções de Download (básicas + avançadas)
        options_frame = ctk.CTkFrame(
            main_frame,
            fg_color=("white", "gray19"),
            corner_radius=12,
            border_width=1,
            border_color=("#e5e7eb", "gray30")
        )
        options_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        options_title = ctk.CTkLabel(
            options_frame,
            text="⚙️ Opções de Download",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#2c3e50", "#ecf0f1")
        )
        options_title.pack(anchor="w", padx=18, pady=(18, 4))

        # Subtítulo e toggle de avançado
        options_header = ctk.CTkFrame(options_frame, fg_color="transparent")
        options_header.pack(fill="x", padx=18, pady=(0, 8))

        basic_label = ctk.CTkLabel(
            options_header,
            text="🎯 Básico",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray20", "gray80")
        )
        basic_label.pack(side="left", padx=(0, 10))

        self.advanced_visible = False
        self.advanced_toggle_btn = ctk.CTkButton(
            options_header,
            text="➕ Mostrar avançado",
            command=self._toggle_advanced_options,
            width=140,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("gray92", "gray24"),
            hover_color=("gray85", "gray30"),
            text_color=("black", "white"),
            corner_radius=20,
            border_width=1,
            border_color=("gray80", "gray40")
        )
        self.advanced_toggle_btn.pack(side="right")

        # Linha separadora
        separator_basic = ctk.CTkFrame(options_frame, fg_color=("gray80", "gray30"), height=1)
        separator_basic.pack(fill="x", padx=18, pady=(0, 8))

        # Tipo de download (básico)
        type_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        type_frame.pack(fill="x", padx=18, pady=8)
        
        type_label = ctk.CTkLabel(
            type_frame,
            text="Tipo:",
            width=100,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        type_label.pack(side="left", padx=(0, 10))
        
        self.download_type_var = ctk.StringVar(value="audio")
        audio_radio = ctk.CTkRadioButton(
            type_frame,
            text="🎵 Áudio",
            variable=self.download_type_var,
            value="audio",
            command=self._on_type_change
        )
        audio_radio.pack(side="left", padx=10)
        
        video_radio = ctk.CTkRadioButton(
            type_frame,
            text="🎬 Vídeo",
            variable=self.download_type_var,
            value="video",
            command=self._on_type_change
        )
        video_radio.pack(side="left", padx=10)
        
        # Formato (básico)
        format_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        format_frame.pack(fill="x", padx=18, pady=8)
        
        format_label = ctk.CTkLabel(
            format_frame,
            text="Formato:",
            width=100,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        format_label.pack(side="left", padx=(0, 10))
        
        self.format_var = ctk.StringVar(value="mp3")
        self.format_menu = ctk.CTkOptionMenu(
            format_frame,
            variable=self.format_var,
            values=config.AUDIO_FORMATS,
            command=self._on_format_change,
            width=150
        )
        self.format_menu.pack(side="left", padx=10)
        
        # Qualidade de vídeo (básico, mas só aparece em modo vídeo)
        self.quality_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        self.quality_frame.pack_forget()
        
        quality_label = ctk.CTkLabel(
            self.quality_frame,
            text="Qualidade:",
            width=100,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        quality_label.pack(side="left", padx=(0, 10))
        
        self.quality_var = ctk.StringVar(value="best")
        quality_menu = ctk.CTkOptionMenu(
            self.quality_frame,
            variable=self.quality_var,
            values=["best", "1080p", "720p", "480p", "360p"],
            width=150
        )
        quality_menu.pack(side="left", padx=10)
        
        # Diretório de download (básico)
        dir_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        dir_frame.pack(fill="x", padx=18, pady=(8, 18))
        
        dir_label = ctk.CTkLabel(
            dir_frame,
            text="📂 Pasta:",
            width=100,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        dir_label.pack(side="left", padx=(0, 10))
        
        self.dir_entry = ctk.CTkEntry(
            dir_frame,
            textvariable=ctk.StringVar(value=self.download_dir),
            height=35
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.browse_btn = ctk.CTkButton(
            dir_frame,
            text="📂 Procurar",
            command=self._browse_directory,
            width=110,
            height=37,
            font=ctk.CTkFont(size=12),
            fg_color=("#ef4444", "#dc2626"),
            hover_color=("#dc2626", "#b91c1c"),
            corner_radius=8
        )
        self.browse_btn.pack(side="right")

        # Atualiza status rápido quando diretório muda
        self.dir_entry.bind("<FocusOut>", lambda e: self._update_status_directory())

        # Área AVANÇADA (inicialmente escondida)
        self.advanced_frame = ctk.CTkFrame(
            options_frame,
            fg_color=("#f9fafb", "gray22"),
            corner_radius=10,
            border_width=1,
            border_color=("#e5e7eb", "gray35")
        )
        self.advanced_frame.pack_forget()

        advanced_label = ctk.CTkLabel(
            self.advanced_frame,
            text="🧠 Opções avançadas",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray25", "gray80")
        )
        advanced_label.pack(anchor="w", padx=15, pady=(10, 5))

        # Seletor manual de tema (YouTube / SoundCloud) – preferência do usuário
        theme_label = ctk.CTkLabel(
            self.advanced_frame,
            text="🎨 Tema visual",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray25", "gray80")
        )
        theme_label.pack(anchor="w", padx=15, pady=(0, 2))

        current_theme_name = "YouTube"
        if self.site_theme == "soundcloud": current_theme_name = "SoundCloud"
        elif self.site_theme == "indigo": current_theme_name = "Indigo Premium"
        elif self.site_theme == "violet": current_theme_name = "Violet Night"
        self.site_theme_var = ctk.StringVar(value=current_theme_name)
        
        theme_switch = ctk.CTkSegmentedButton(
            self.advanced_frame,
            values=["YouTube", "SoundCloud", "Indigo Premium", "Violet Night"],
            variable=self.site_theme_var,
            command=self._on_site_theme_manual_change
        )
        theme_switch.pack(fill="x", padx=15, pady=(0, 10))

        # Organização (avançado)
        org_frame = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        org_frame.pack(fill="x", padx=15, pady=5)
        
        self.organize_var = ctk.BooleanVar(value=True)
        organize_check = ctk.CTkCheckBox(
            org_frame,
            text="📁 Organizar automaticamente em pastas (Artista/Álbum)",
            variable=self.organize_var
        )
        organize_check.pack(side="left", padx=10, pady=10)

        # Botão de ajuda de organização
        org_help_btn = ctk.CTkButton(
            org_frame,
            text="❔",
            width=28,
            height=28,
            command=self._show_organize_help,
            fg_color=("gray80", "gray30"),
            hover_color=("gray70", "gray40")
        )
        org_help_btn.pack(side="left", padx=(0, 5), pady=10)
        
        # Botão de ajuda para cookies (referência ao card principal)
        cookies_help_frame = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        cookies_help_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        cookies_help_label = ctk.CTkLabel(
            cookies_help_frame,
            text="💡 Os cookies são gerenciados no card principal no topo da interface. Eles são salvos automaticamente para uso futuro.",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
            anchor="w",
            justify="left",
            wraplength=600
        )
        cookies_help_label.pack(side="left", fill="x", expand=True)

        self.cookies_help_btn = ctk.CTkButton(
            cookies_help_frame,
            text="Ver detalhes",
            width=110,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._show_cookies_help,
            fg_color=("#ef4444", "#dc2626"),
            hover_color=("#dc2626", "#b91c1c"),
            corner_radius=8
        )
        self.cookies_help_btn.pack(side="right", padx=(5, 0))
        
        # Botão de download melhorado com gradiente visual
        download_btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        download_btn_frame.pack(fill="x", padx=10, pady=(10, 10))
        self.download_btn_frame = download_btn_frame
        
        self.download_button = ctk.CTkButton(
            download_btn_frame,
            text="⬇️ Iniciar Download",
            command=self._start_download,
            font=ctk.CTkFont(size=17, weight="bold"),
            height=55,
            fg_color=("#ef4444", "#dc2626"),
            hover_color=("#dc2626", "#b91c1c"),
            corner_radius=12,
            border_width=0,
            text_color=("white", "white")
        )
        self.download_button.pack(fill="x")
        
        # Progress Bar com informações detalhadas - sempre visível quando ativo
        self.progress_frame = ctk.CTkFrame(
            main_frame,
            fg_color=("white", "gray16"),
            corner_radius=12,
            border_width=1,
            border_color=("#e5e7eb", "gray30")
        )
        # Não empacota inicialmente
        self.progress_frame.pack_forget()
        
        # Container interno para melhor organização
        progress_content = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        progress_content.pack(fill="x", padx=15, pady=15)
        
        # Header do progresso
        progress_header = ctk.CTkFrame(progress_content, fg_color="transparent")
        progress_header.pack(fill="x", pady=(0, 10))
        
        # Label principal de status
        self.progress_label = ctk.CTkLabel(
            progress_header,
            text="Aguardando...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#2c3e50", "#ecf0f1")
        )
        self.progress_label.pack(side="left", padx=(0, 10))
        
        # Label de porcentagem (ao lado do título) - melhorado
        self.progress_percent_label = ctk.CTkLabel(
            progress_header,
            text="0%",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#ef4444", "#dc2626"),
            corner_radius=8,
            width=70,
            height=30,
            text_color=("white", "white")
        )
        self.progress_percent_label.pack(side="right")

        # Resumo rápido do job atual (tipo, formato, pasta)
        self.progress_summary_label = ctk.CTkLabel(
            progress_content,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            anchor="w",
            justify="left",
            wraplength=600
        )
        self.progress_summary_label.pack(fill="x", pady=(0, 6), padx=2)
        
        # Label de detalhes (etapa atual)
        self.progress_detail_label = ctk.CTkLabel(
            progress_content,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70"),
            anchor="w",
            justify="left",
            wraplength=600
        )
        self.progress_detail_label.pack(fill="x", pady=(0, 12), padx=2)
        
        # Barra de progresso principal - melhorada
        progress_bar_frame = ctk.CTkFrame(progress_content, fg_color="transparent")
        progress_bar_frame.pack(fill="x", pady=(0, 12))
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_bar_frame,
            height=26,
            corner_radius=13,
            fg_color=("gray80", "gray30"),
            progress_color=("#ef4444", "#dc2626"),
            border_width=0
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        
        # Etapas do processo (em grid responsivo) - melhorado
        steps_label = ctk.CTkLabel(
            progress_content,
            text="📊 Etapas do Processo:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            text_color=("#2c3e50", "#ecf0f1")
        )
        steps_label.pack(anchor="w", padx=2, pady=(0, 8))
        
        self.steps_frame = ctk.CTkFrame(progress_content, fg_color=("gray85", "gray20"), corner_radius=8)
        self.steps_frame.pack(fill="x", padx=2, pady=(0, 5))
        
        # Etapas em colunas para telas pequenas - melhoradas
        self.steps = {
            'download': ctk.CTkLabel(
                self.steps_frame, 
                text="⬜ Download", 
                font=ctk.CTkFont(size=11, weight="bold"), 
                anchor="w",
                text_color=("#2c3e50", "#ecf0f1")
            ),
            'conversion': ctk.CTkLabel(
                self.steps_frame, 
                text="⬜ Conversão", 
                font=ctk.CTkFont(size=11, weight="bold"), 
                anchor="w",
                text_color=("#2c3e50", "#ecf0f1")
            ),
            'organization': ctk.CTkLabel(
                self.steps_frame, 
                text="⬜ Organização", 
                font=ctk.CTkFont(size=11, weight="bold"), 
                anchor="w",
                text_color=("#2c3e50", "#ecf0f1")
            ),
            'metadata': ctk.CTkLabel(
                self.steps_frame, 
                text="⬜ Metadados", 
                font=ctk.CTkFont(size=11, weight="bold"), 
                anchor="w",
                text_color=("#2c3e50", "#ecf0f1")
            )
        }
        
        # Grid responsivo (2 colunas em telas pequenas)
        for i, (key, step) in enumerate(self.steps.items()):
            row = i // 2
            col = i % 2
            step.grid(row=row, column=col, padx=15, pady=8, sticky="ew")
        
        # Configura colunas para expandir
        self.steps_frame.grid_columnconfigure(0, weight=1)
        self.steps_frame.grid_columnconfigure(1, weight=1)
        
        # Variáveis de estado
        self.current_step = None
        self.download_active = False
        self.main_frame_ref = main_frame  # Referência para o scrollable frame
        
        # Alternador entre Logs e Histórico dentro de Avançado (logo acima dos widgets)
        self.advanced_section_var = ctk.StringVar(value="Logs")
        self.advanced_section_switch = ctk.CTkSegmentedButton(
            self.advanced_frame,
            values=["Logs", "Histórico"],
            variable=self.advanced_section_var,
            command=self._on_advanced_section_change
        )
        self.advanced_section_switch.pack(fill="x", padx=15, pady=(0, 6))

        # Área de Logs melhorada (dentro de Opções Avançadas)
        self.logs_container = ctk.CTkFrame(self.advanced_frame, fg_color=("gray88", "gray17"), corner_radius=12)
        self.logs_container.pack(fill="both", expand=True, padx=10, pady=(5, 8))
        
        logs_header = ctk.CTkFrame(self.logs_container, fg_color=("gray85", "gray20"), corner_radius=8)
        logs_header.pack(fill="x", padx=8, pady=8)
        
        logs_title = ctk.CTkLabel(
            logs_header,
            text="📋 Logs de Atividade",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#2c3e50", "#ecf0f1")
        )
        logs_title.pack(side="left", padx=12, pady=10)

        # Filtro de logs (Todos / Avisos / Erros)
        filter_frame = ctk.CTkFrame(logs_header, fg_color="transparent")
        filter_frame.pack(side="right", padx=(0, 8), pady=8)

        filter_label = ctk.CTkLabel(
            filter_frame,
            text="Filtro:",
            font=ctk.CTkFont(size=11),
        )
        filter_label.pack(side="left", padx=(0, 4))

        self.log_filter_var = ctk.StringVar(value="Todos")
        self.log_filter_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.log_filter_var,
            values=["Todos", "Informações", "Avisos", "Erros"],
            width=120,
            command=lambda _: self._render_logs()
        )
        self.log_filter_menu.pack(side="left")
        
        # Botão para limpar logs - melhorado
        clear_logs_btn = ctk.CTkButton(
            logs_header,
            text="🗑️ Limpar",
            command=self._clear_logs,
            width=90,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            corner_radius=8
        )
        clear_logs_btn.pack(side="right", padx=8, pady=8)
        
        # Área de logs scrollable
        logs_frame = ctk.CTkFrame(self.logs_container, fg_color="transparent")
        logs_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        self.logs_text = ctk.CTkTextbox(
            logs_frame,
            height=180,
            font=ctk.CTkFont(size=11, family="Consolas"),
            fg_color=("gray95", "gray10"),
            text_color=("gray10", "gray90"),
            wrap="word",
            corner_radius=8,
            border_width=2,
            border_color=("gray80", "gray25")
        )
        self.logs_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configura scroll para o final
        self.logs_text.configure(state="disabled")

        # Card de Histórico de Downloads (simples, alternável com logs, também em avançado)
        self.history_container = ctk.CTkFrame(self.advanced_frame, fg_color=("gray90", "gray18"), corner_radius=12)
        self.history_container.pack(fill="x", padx=10, pady=(5, 10))
        
        history_header = ctk.CTkFrame(self.history_container, fg_color=("gray85", "gray22"), corner_radius=8)
        history_header.pack(fill="x", padx=8, pady=8)

        history_title = ctk.CTkLabel(
            history_header,
            text="📜 Histórico de Downloads (sessão atual)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#2c3e50", "#ecf0f1")
        )
        history_title.pack(side="left", padx=12, pady=8)

        self.history_frame = ctk.CTkFrame(self.history_container, fg_color="transparent")
        self.history_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.history_text = ctk.CTkTextbox(
            self.history_frame,
            height=110,
            font=ctk.CTkFont(size=11),
            fg_color=("gray95", "gray10"),
            text_color=("gray10", "gray90"),
            wrap="word",
            corner_radius=8,
            border_width=1,
            border_color=("gray80", "gray30")
        )
        self.history_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.history_text.configure(state="disabled")

        # Lista em memória para histórico
        self.history_items = []

        # Começa mostrando apenas Logs por padrão
        if hasattr(self, "history_container"):
            self.history_container.pack_forget()

        # === CARD: CONVERSOR DE MÍDIA ===
        converter_card = ctk.CTkFrame(self.main_frame, fg_color=("white", "gray19"), corner_radius=12,
                                      border_width=1, border_color=("#e5e7eb", "gray30"))
        converter_card.pack(fill="x", padx=10, pady=(0, 10))

        # Título
        ctk.CTkLabel(converter_card, text="🎬 Conversor de Mídia",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=("#2c3e50", "#ecf0f1"),
                     anchor="w", padx=18, pady=(18, 4)).pack(fill="x")

        # Linha 1: Arquivo de origem + botão Procurar
        src_row = ctk.CTkFrame(converter_card, fg_color="transparent")
        src_row.pack(fill="x", padx=18, pady=(4, 8))

        ctk.CTkLabel(src_row, text="Arquivo de origem:", width=140, anchor="w").pack(side="left", padx=(0, 8))
        self.converter_source_entry = ctk.CTkEntry(src_row, placeholder_text="Selecione um arquivo...", height=35)
        self.converter_source_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(src_row, text="📂 Procurar", command=self._browse_source_file,
                      width=120, height=35, corner_radius=8).pack(side="left")

        # Linha 2: Pasta/Arquivo de destino + botão Procurar
        out_row = ctk.CTkFrame(converter_card, fg_color="transparent")
        out_row.pack(fill="x", padx=18, pady=(4, 8))

        ctk.CTkLabel(out_row, text="Arquivo de destino:", width=140, anchor="w").pack(side="left", padx=(0, 8))
        self.converter_output_entry = ctk.CTkEntry(out_row, placeholder_text="Selecione o destino...", height=35)
        self.converter_output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(out_row, text="📂 Procurar", command=self._browse_output_file,
                      width=120, height=35, corner_radius=8).pack(side="left")

        # Linha 3: Formato de saída
        fmt_row = ctk.CTkFrame(converter_card, fg_color="transparent")
        fmt_row.pack(fill="x", padx=18, pady=(4, 8))

        ctk.CTkLabel(fmt_row, text="Formato de saída:", width=140, anchor="w").pack(side="left", padx=(0, 8))
        self.converter_format_var = ctk.StringVar(value="mp3")
        ctk.CTkOptionMenu(fmt_row, variable=self.converter_format_var,
                          values=["mp3", "m4a", "flac", "opus", "ogg", "wav", "mp4", "webm"],
                          width=150, height=35).pack(side="left")

        # Botão Converter
        self.convert_btn = ctk.CTkButton(converter_card, text="🎬 Converter", command=self._convert_file,
                                         height=42, size=15, font=ctk.CTkFont(size=15, weight="bold"),
                                         fg_color=("#ef4444", "#dc2626"),
                                         hover_color=("#dc2626", "#b91c1c"),
                                         corner_radius=10)
        self.convert_btn.pack(fill="x", padx=18, pady=(8, 4))

        # Status label
        self.converter_status_label = ctk.CTkLabel(converter_card, text="",
                                                   font=ctk.CTkFont(size=12),
                                                   text_color=("#4b5563", "#9ca3af"),
                                                   anchor="w", padx=18, pady=(0, 18))
        self.converter_status_label.pack(fill="x")

        # Footer com copyright
        self.footer_frame = ctk.CTkFrame(self.root, fg_color="transparent", height=30)
        self.footer_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
        
        footer_label = ctk.CTkLabel(
            self.footer_frame,
            text=config.APP_COPYRIGHT,
            font=ctk.CTkFont(size=10),
            text_color=("gray60", "gray40")
        )
        footer_label.pack(side="bottom")
    
    def _toggle_theme(self):
        """Alterna entre tema claro e escuro a partir do header"""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        ctk.set_appearance_mode(self.current_theme)

        # Atualiza texto do botão
        if hasattr(self, "theme_toggle_btn") and self.theme_toggle_btn:
            if self.current_theme == "dark":
                self.theme_toggle_btn.configure(text="🌙 Escuro")
            else:
                self.theme_toggle_btn.configure(text="☀️ Claro")

        # Reaplica paleta do site para ajustar cores em ambos os modos
        self._apply_site_theme()

    # ---------------------- Tema por site (YouTube / SoundCloud) ----------------------

    def _load_user_settings(self):
        """Carrega configurações persistentes do usuário"""
        try:
            if os.path.exists(config.USER_SETTINGS_FILE):
                import json
                with open(config.USER_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_user_settings(self):
        """Salva configurações persistentes do usuário"""
        try:
            import json
            data = {
                "site_theme": self.site_theme,
                "cookies": {
                    "file_path": self.cookies_file,
                    "provider": self.cookies_provider
                } if self.cookies_file else None
            }
            with open(config.USER_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _get_site_palette(self, site: str):
        """Retorna paleta de cores para o site especificado"""
        site = (site or "youtube").lower()
        if site == "soundcloud":
            return {
                "accent": ("#f97316", "#ea580c"),
                "accent_hover": ("#ea580c", "#c2410c"),
                "header_bg": ("#ffffff", "#161616"),
                "icon": ("#f97316", "#fed7aa"),
            }
        elif site == "indigo" or site == "indigo premium":
            return {
                "accent": ("#6366f1", "#4f46e5"),
                "accent_hover": ("#4f46e5", "#4338ca"),
                "header_bg": ("#ffffff", "#1e1b4b"),
                "icon": ("#6366f1", "#818cf8"),
            }
        elif site == "violet" or site == "violet night":
            return {
                "accent": ("#8b5cf6", "#7c3aed"),
                "accent_hover": ("#7c3aed", "#6d28d9"),
                "header_bg": ("#ffffff", "#2e1065"),
                "icon": ("#8b5cf6", "#a78bfa"),
            }
        # padrão: YouTube
        return {
            "accent": ("#ef4444", "#dc2626"),
            "accent_hover": ("#dc2626", "#b91c1c"),
            "header_bg": ("#ffffff", "#181818"),
            "icon": ("#dc2626", "#f97373"),
        }

    def _apply_site_theme(self):
        """Aplica as cores do tema atual (YouTube / SoundCloud) aos principais widgets"""
        palette = self._get_site_palette(self.site_theme)

        # Header
        if hasattr(self, "header_frame") and self.header_frame:
            self.header_frame.configure(fg_color=palette["header_bg"])
        if hasattr(self, "logo_icon") and self.logo_icon:
            self.logo_icon.configure(text_color=palette["icon"])

        # Botões principais
        accent = palette["accent"]
        accent_hover = palette["accent_hover"]
        if hasattr(self, "fetch_info_btn") and self.fetch_info_btn:
            self.fetch_info_btn.configure(fg_color=accent, hover_color=accent_hover)
        if hasattr(self, "browse_btn") and self.browse_btn:
            self.browse_btn.configure(fg_color=accent, hover_color=accent_hover)
        if hasattr(self, "cookies_browse_btn") and self.cookies_browse_btn:
            self.cookies_browse_btn.configure(fg_color=accent, hover_color=accent_hover)
        if hasattr(self, "cookies_help_btn") and self.cookies_help_btn:
            self.cookies_help_btn.configure(fg_color=accent, hover_color=accent_hover)
        if hasattr(self, "download_button") and self.download_button:
            self.download_button.configure(fg_color=accent, hover_color=accent_hover)

        # Barra de progresso
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.configure(progress_color=accent)
        if hasattr(self, "progress_percent_label") and self.progress_percent_label:
            self.progress_percent_label.configure(fg_color=accent)

        # Botão de mostrar/ocultar avançado – borda e texto no tom do tema
        if hasattr(self, "advanced_toggle_btn") and self.advanced_toggle_btn:
            self.advanced_toggle_btn.configure(
                border_color=accent,
                text_color=accent,
                fg_color=("gray96", "gray20"),
                hover_color=("gray92", "gray25")
            )

    def _set_site_theme(self, site: str, save_default: bool = False):
        """Define o tema do site atual e opcionalmente salva como padrão"""
        valid_sites = ["youtube", "soundcloud", "indigo", "violet"]
        if site not in valid_sites:
            site = "youtube"
        self.site_theme = site
        self._apply_site_theme()

        # Atualiza seletor manual, se existir
        if hasattr(self, "site_theme_var"):
            site_map_rev = {
                "youtube": "YouTube",
                "soundcloud": "SoundCloud",
                "indigo": "Indigo Premium",
                "violet": "Violet Night"
            }
            label = site_map_rev.get(site, "YouTube")
            self.site_theme_var.set(label)

        if save_default:
            self._save_user_settings()

    def _on_site_theme_manual_change(self, value: str):
        """Callback do seletor manual de tema em Avançado"""
        site_map = {
            "YouTube": "youtube",
            "SoundCloud": "soundcloud",
            "Indigo Premium": "indigo",
            "Violet Night": "violet"
        }
        site = site_map.get(value, "youtube")
        self._set_site_theme(site, save_default=True)

    def _auto_detect_site_theme_from_url(self, url: str):
        """Detecta tema com base no domínio da URL"""
        if not url:
            return
        ul = url.lower()
        if "soundcloud.com" in ul:
            self._set_site_theme("soundcloud", save_default=False)
        elif "youtube.com" in ul or "youtu.be" in ul or "music.youtube.com" in ul:
            self._set_site_theme("youtube", save_default=False)

    def _auto_detect_site_theme_from_cookies(self, file_path: str):
        """Heurística simples para detectar tema com base no arquivo de cookies"""
        if not file_path:
            return
        p = os.path.basename(file_path).lower()
        if "soundcloud" in p:
            self._set_site_theme("soundcloud", save_default=False)
        elif "youtube" in p or "yt" in p:
            self._set_site_theme("youtube", save_default=False)

    def _show_about(self):
        """Janela 'Sobre' com informações da versão 2.0"""
        win = ctk.CTkToplevel(self.root)
        win.title("Sobre - Nexus Downloader")
        win.geometry("520x380")
        win.transient(self.root)
        win.grab_set()

        title = ctk.CTkLabel(
            win,
            text=f"Nexus Downloader v{config.APP_VERSION}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(padx=20, pady=(20, 5))

        subtitle = ctk.CTkLabel(
            win,
            text="Versão 2.0 – Interface renovada, tema YouTube-like e fluxo mais seguro com cookies.",
            font=ctk.CTkFont(size=12),
            wraplength=460,
            justify="center"
        )
        subtitle.pack(padx=20, pady=(0, 15))

        changelog_title = ctk.CTkLabel(
            win,
            text="Principais novidades:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        changelog_title.pack(fill="x", padx=20, pady=(5, 5))

        changelog_text = (
            "• Tema escuro YouTube-like com acentos em vermelho.\n"
            "• Toggle Claro/Escuro direto no cabeçalho.\n"
            "• Cards organizando Download Rápido, Opções e Progresso.\n"
            "• Uso de cookies obrigatório e mais claro para evitar erros HTTP.\n"
            "• Popups de ajuda para cookies e organização automática.\n"
            "• Melhorias visuais em progresso, logs e mensagens."
        )

        changelog_label = ctk.CTkLabel(
            win,
            text=changelog_text,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            wraplength=460
        )
        changelog_label.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        palette = self._get_site_palette(self.site_theme)
        close_btn = ctk.CTkButton(
            win,
            text="Fechar",
            command=win.destroy,
            width=90,
            height=32,
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"]
        )
        close_btn.pack(pady=(0, 20))

    def _toggle_advanced_options(self):
        """Mostra ou esconde o bloco de opções avançadas"""
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.pack(fill="x", padx=15, pady=(0, 15))
            self.advanced_toggle_btn.configure(text="➖ Ocultar avançado")
        else:
            self.advanced_frame.pack_forget()
            self.advanced_toggle_btn.configure(text="➕ Mostrar avançado")

    def _show_cookies_help(self):
        """Mostra popup explicando como usar cookies"""
        help_win = ctk.CTkToplevel(self.root)
        help_win.title("Ajuda sobre cookies")
        help_win.geometry("520x360")
        help_win.transient(self.root)
        help_win.grab_set()

        title = ctk.CTkLabel(
            help_win,
            text="🔐 Como usar cookies para downloads privados",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(padx=20, pady=(20, 10))

        text = (
            "Alguns conteúdos (playlists privadas, curtidas, histórico, etc.) "
            "exigem que você esteja logado na sua conta.\n\n"
            "1. No seu navegador, instale uma extensão como 'Get cookies.txt LOCALLY'.\n"
            "2. Acesse o YouTube/YouTube Music ou Soundcloud, com a conta certa e certifique-se de estar logado.\n"
            "3. Use a extensão para exportar os cookies do domínio (youtube.com / music.youtube.com ; soundcloud.com).\n"
            "4. Salve o arquivo como cookies.txt ou se quiser organizar: youtube.txt, youtubemusic.txt ou soundcloud.txt, e selecione-o aqui no Nexus.\n\n"
            "Dica: mantenha o arquivo de cookies em local seguro, pois ele representa sua sessão logada no respectivo site para pesquisar, baixar e converter."
        )

        text_label = ctk.CTkLabel(
            help_win,
            text=text,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            wraplength=460
        )
        text_label.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        palette = self._get_site_palette(self.site_theme)
        close_btn = ctk.CTkButton(
            help_win,
            text="Entendi",
            command=help_win.destroy,
            width=100,
            height=32,
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"]
        )
        close_btn.pack(pady=(0, 20))

    def _show_organize_help(self):
        """Mostra popup explicando a organização automática"""
        help_win = ctk.CTkToplevel(self.root)
        help_win.title("Ajuda de organização")
        help_win.geometry("520x320")
        help_win.transient(self.root)
        help_win.grab_set()

        title = ctk.CTkLabel(
            help_win,
            text="📁 Organização automática por artista/álbum",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(padx=20, pady=(20, 10))

        text = (
            "Quando a opção de organizar está ligada, o Nexus cria uma estrutura de pastas "
            "baseada nos metadados da música.\n\n"
            "Exemplo de estrutura padrão:\n"
            "  Artista/Álbum/Música.mp3\n\n"
            "Você pode controlar quais campos entram na estrutura (artista, álbum, gênero, ano) "
            "nas configurações globais ou ajustando o dicionário FOLDER_STRUCTURE no arquivo config.py.\n\n"
            "Se preferir manter tudo em uma única pasta, basta desmarcar esta opção."
        )

        text_label = ctk.CTkLabel(
            help_win,
            text=text,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            wraplength=460
        )
        text_label.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        palette = self._get_site_palette(self.site_theme)
        close_btn = ctk.CTkButton(
            help_win,
            text="Entendi",
            command=help_win.destroy,
            width=100,
            height=32,
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"]
        )
        close_btn.pack(pady=(0, 20))

    def _update_status_directory(self):
        """Atualiza label de status com a pasta de download atual"""
        try:
            self.download_dir = self.dir_entry.get().strip() or self.download_dir
            if hasattr(self, "status_label") and self.status_label:
                self.status_label.configure(text=f"📂 Pasta atual: {self.download_dir}")
        except Exception:
            pass

    def _on_advanced_section_change(self, value=None):
        """Alterna visualmente entre Logs e Histórico dentro da aba Avançado"""
        section = self.advanced_section_var.get() if hasattr(self, "advanced_section_var") else "Logs"

        # Esconde ambos
        if hasattr(self, "logs_container") and self.logs_container:
            self.logs_container.pack_forget()
        if hasattr(self, "history_container") and self.history_container:
            self.history_container.pack_forget()

        # Mostra o selecionado
        if section == "Histórico":
            if hasattr(self, "history_container") and self.history_container:
                self.history_container.pack(fill="x", padx=10, pady=(5, 10))
        else:
            if hasattr(self, "logs_container") and self.logs_container:
                self.logs_container.pack(fill="both", expand=True, padx=10, pady=(5, 8))

    def _add_history_entry(self, success: bool, detail: str):
        """Adiciona uma linha ao histórico de downloads da sessão"""
        if not hasattr(self, "history_text"):
            return

        from datetime import datetime as _dt
        ts = _dt.now().strftime("%H:%M:%S")
        status_icon = "✅" if success else "❌"
        line = f"[{ts}] {status_icon} {detail}\n"

        self.history_items.append(line)
        # Mantém histórico relativamente curto
        if len(self.history_items) > 100:
            self.history_items = self.history_items[-100:]

        try:
            self.history_text.configure(state="normal")
            self.history_text.delete("1.0", "end")
            for entry in self.history_items:
                self.history_text.insert("end", entry)
            self.history_text.see("end")
            self.history_text.configure(state="disabled")
        except Exception:
            try:
                self.history_text.configure(state="disabled")
            except Exception:
                pass

    def _on_type_change(self):
        """Atualiza opções quando o tipo muda"""
        if self.download_type_var.get() == "video":
            self.format_menu.configure(values=config.VIDEO_FORMATS)
            self.format_var.set("mp4")
            self.quality_frame.pack(fill="x", padx=15, pady=5)
        else:
            self.format_menu.configure(values=config.AUDIO_FORMATS)
            self.format_var.set("mp3")
            self.quality_frame.pack_forget()
    
    def _on_format_change(self, value):
        """Atualiza quando formato muda"""
        pass
    
    def _setup_logging(self):
        """Configura o sistema de logging para capturar logs na interface"""
        # Cria handler customizado
        self.log_handler = LogHandler(self._add_log_message)
        self.log_handler.setLevel(logging.INFO)
        
        # Adiciona handler aos loggers principais
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger('downloader').addHandler(self.log_handler)
        logging.getLogger('converter').addHandler(self.log_handler)
        logging.getLogger('metadata').addHandler(self.log_handler)
        logging.getLogger('organizer').addHandler(self.log_handler)
        logging.getLogger('__main__').addHandler(self.log_handler)
    
    def _add_log_message(self, message: str, level: str = "INFO"):
        """Adiciona mensagem de log à interface"""
        def update_logs():
            try:
                # Adiciona timestamp e formata
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted_msg = f"[{timestamp}] {message}\n"

                # Guarda metadados para filtros futuros
                self.log_messages.append({"text": formatted_msg, "level": level})

                # Mantém apenas as últimas linhas
                if len(self.log_messages) > self.max_log_lines:
                    lines_to_remove = len(self.log_messages) - self.max_log_lines
                    self.log_messages = self.log_messages[lines_to_remove:]

                # Re-renderiza logs respeitando o filtro atual
                self._render_logs()
            except Exception as e:
                # Se der erro, apenas ignora (não quebra a aplicação)
                pass
        
        # Atualiza na thread principal
        if hasattr(self, 'root'):
            self.root.after(0, update_logs)
    
    def _clear_logs(self):
        """Limpa a área de logs"""
        self.logs_text.configure(state="normal")
        self.logs_text.delete("1.0", "end")
        self.logs_text.configure(state="disabled")
        self.log_messages = []

    def _render_logs(self):
        """Renderiza logs no TextBox aplicando o filtro selecionado"""
        try:
            self.logs_text.configure(state="normal")
            self.logs_text.delete("1.0", "end")

            # Filtro atual
            current_filter = None
            if hasattr(self, "log_filter_var"):
                val = self.log_filter_var.get()
                if val == "Avisos":
                    current_filter = "WARNING"
                elif val == "Erros":
                    current_filter = "ERROR"
                elif val == "Informações":
                    current_filter = "INFO"

            for idx, item in enumerate(self.log_messages):
                text = item.get("text", "")
                level = item.get("level", "INFO")

                # Aplica filtro
                if current_filter and level != current_filter:
                    # Também tenta filtrar por conteúdo se o nível não vier correto
                    if current_filter == "WARNING" and "⚠️" not in text and "Aviso" not in text:
                        continue
                    if current_filter == "ERROR" and "❌" not in text and "Erro" not in text:
                        continue

                # Define cor baseado no nível / conteúdo
                msg_lower = text.lower()
                if level == "ERROR" or "❌" in text or "erro" in msg_lower:
                    color = "#ef4444"
                elif level == "WARNING" or "⚠️" in text or "aviso" in msg_lower:
                    color = "#f59e0b"
                elif "✅" in text or "sucesso" in msg_lower or "concluído" in msg_lower:
                    color = "#10b981"
                elif "📥" in text or "📹" in text or "baixando" in msg_lower:
                    # Azul permanece como cor semântica para operações de download
                    color = "#3b82f6"
                elif "🏷️" in text or "metadados" in msg_lower:
                    color = "#8b5cf6"
                elif "📁" in text or "organizando" in msg_lower:
                    color = "#f97316"
                elif "🧹" in text or "limpando" in msg_lower:
                    color = "#22c55e"
                elif "🔍" in text or "buscando" in msg_lower:
                    color = "#06b6d4"
                else:
                    if ctk.get_appearance_mode() == "dark":
                        color = "#9ca3af"
                    else:
                        color = "#6b7280"

                tag_name = f"log_color_{idx}"
                self.logs_text.tag_config(tag_name, foreground=color)
                self.logs_text.insert("end", text, tag_name)

            self.logs_text.see("end")
            self.logs_text.configure(state="disabled")
        except Exception:
            try:
                self.logs_text.configure(state="disabled")
            except Exception:
                pass
    
    def _scroll_to_top(self):
        """Rola para o topo do scrollable frame"""
        try:
            if hasattr(self, 'main_frame_ref') and self.main_frame_ref:
                # CTkScrollableFrame tem um canvas interno
                if hasattr(self.main_frame_ref, '_parent_canvas'):
                    self.main_frame_ref._parent_canvas.yview_moveto(0)
                elif hasattr(self.main_frame_ref, '_scrollbar'):
                    # Tenta via scrollbar
                    self.main_frame_ref._scrollbar.set(0.0)
        except Exception as e:
            logger.debug(f"Erro ao scrollar para o topo: {e}")
    
    def _browse_directory(self):
        """Abre diálogo para escolher diretório"""
        directory = filedialog.askdirectory(initialdir=self.download_dir)
        if directory:
            self.download_dir = directory
            self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, directory)

    def _browse_source_file(self):
        """Seleciona um arquivo de origem para conversão"""
        file_path = filedialog.askopenfilename(
            title="Selecionar arquivo de origem",
            filetypes=[
                ("Mídia", "*.mp4 *.webm *.mkv *.avi *.mov *.flv *.wmv *.m4v *.mp3 *.m4a *.flac *.opus *.ogg *.wav"),
                ("Vídeo", "*.mp4 *.webm *.mkv *.avi *.mov *.flv *.wmv *.m4v"),
                ("Áudio", "*.mp3 *.m4a *.flac *.opus *.ogg *.wav"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return
        self.converter_source_path = file_path
        self.converter_source_entry.delete(0, tk.END)
        self.converter_source_entry.insert(0, file_path)
        self.converter_output_path = None
        self.converter_output_entry.delete(0, tk.END)
        self.converter_status_label.configure(text="Arquivo de origem selecionado. Escolha o destino e o formato.")

    def _browse_output_file(self):
        """Seleciona o arquivo de destino para a conversão"""
        fmt = self.converter_format_var.get()
        initial_file = ""
        if self.converter_source_path:
            base = os.path.splitext(os.path.basename(self.converter_source_path))[0]
            initial_file = f"{base}.{fmt}"
        file_path = filedialog.asksaveasfilename(
            title="Salvar como",
            defaultextension=f".{fmt}",
            initialfile=initial_file,
            filetypes=[
                (f"Arquivo {fmt.upper()}", f"*.{fmt}"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return
        self.converter_output_path = file_path
        self.converter_output_entry.delete(0, tk.END)
        self.converter_output_entry.insert(0, file_path)
        self.converter_status_label.configure(text="Arquivo de destino definido. Clique em Converter.")

    def _convert_file(self):
        """Inicia a conversão do arquivo selecionado"""
        if self.converter_running:
            self.converter_status_label.configure(text="⚠️ Uma conversão já está em andamento.")
            return

        source = self.converter_source_path or self.converter_source_entry.get().strip()
        if not source or not os.path.isfile(source):
            messagebox.showerror("Erro", "Selecione um arquivo de origem válido.")
            return

        fmt = self.converter_format_var.get()
        output = self.converter_output_path or self.converter_output_entry.get().strip()
        if not output:
            base = os.path.splitext(os.path.basename(source))[0]
            output = os.path.join(os.path.dirname(source), f"{base}.{fmt}")

        self.converter_running = True
        self.convert_btn.configure(state="disabled", text="Convertendo...")
        self.converter_status_label.configure(text="⏳ Convertendo, aguarde...")

        threading.Thread(
            target=self._run_conversion,
            args=(source, output, fmt),
            daemon=True,
        ).start()

    def _run_conversion(self, source: str, output: str, fmt: str):
        """Executa a conversão em thread separada"""
        success = False
        message = ""
        try:
            conv = self.converter
            src_ext = os.path.splitext(source)[1].lower()
            video_exts = (".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v")

            if src_ext in video_exts and fmt in config.AUDIO_FORMATS:
                success = conv.extract_audio_from_video(source, output, fmt)
            elif fmt in config.AUDIO_FORMATS:
                success = conv.convert_audio(source, output, fmt)
            else:
                success = conv.convert_video(source, output, fmt)

            message = f"Conversão concluída: {os.path.basename(output)}" if success else f"Falha na conversão de {os.path.basename(source)}"
        except Exception as e:
            message = f"Erro na conversão: {e}"

        self.root.after(0, self._conversion_finished, success, message)

    def _conversion_finished(self, success: bool, message: str):
        """Atualiza a UI após a conversão terminar"""
        self.converter_running = False
        self.convert_btn.configure(state="normal", text="🎬 Converter")
        if success:
            self.converter_status_label.configure(text=f"✅ {message}")
            self._add_log_message(message, level="INFO")
        else:
            self.converter_status_label.configure(text=f"❌ {message}")
            self._add_log_message(message, level="ERROR")
            messagebox.showerror("Erro de conversão", message)

    def _detect_cookie_provider(self, file_path: str) -> Optional[str]:
        """Detecta o provedor do cookie (youtube ou soundcloud)"""
        if not file_path or not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
            
            # Verifica domínios no conteúdo
            if 'youtube.com' in content or 'music.youtube.com' in content or 'youtu.be' in content:
                return "youtube"
            elif 'soundcloud.com' in content:
                return "soundcloud"
            
            # Verifica também no nome do arquivo
            filename = os.path.basename(file_path).lower()
            if 'youtube' in filename or 'yt' in filename:
                return "youtube"
            elif 'soundcloud' in filename or 'sc' in filename:
                return "soundcloud"
            
            return None
        except Exception as e:
            logger.warning(f"Erro ao detectar provedor do cookie: {e}")
            return None
    
    def _browse_cookies_file(self):
        """Abre diálogo para selecionar arquivo de cookies"""
        file_path = filedialog.askopenfilename(
            title="Selecionar arquivo de cookies",
            filetypes=[
                ("Arquivo de cookies", "*.txt"),
                ("Todos os arquivos", "*.*")
            ],
            initialdir=os.path.expanduser("~")
        )
        
        if file_path:
            # Valida o arquivo de cookies
            if CookieProcessor.validate_cookies_file(file_path):
                self.cookies_file = file_path
                
                # Detecta provedor
                detected_provider = self._detect_cookie_provider(file_path)
                if detected_provider:
                    self.cookies_provider = detected_provider
                    provider_name = "YouTube" if detected_provider == "youtube" else "SoundCloud"
                    
                    # Verifica se já existe cookie de outro provedor
                    if hasattr(self, 'cookies_provider') and self.cookies_provider and self.cookies_provider != detected_provider:
                        old_provider = "YouTube" if self.cookies_provider == "youtube" else "SoundCloud"
                        messagebox.showinfo(
                            "Novo provedor detectado",
                            f"Você está importando cookies de {provider_name}, mas já tinha cookies de {old_provider}.\n\n"
                            f"Os novos cookies de {provider_name} substituirão os anteriores e serão salvos automaticamente."
                        )
                else:
                    self.cookies_provider = None
                    messagebox.showwarning(
                        "Provedor não detectado",
                        "Não foi possível detectar automaticamente o provedor (YouTube/SoundCloud).\n\n"
                        "O cookie será salvo, mas você pode precisar importar um novo cookie específico para cada site."
                    )
                
                # Atualiza interface
                self.cookies_entry.delete(0, tk.END)
                self.cookies_entry.insert(0, os.path.basename(file_path))
                
                # Atualiza badge de status
                if detected_provider:
                    provider_name = "YouTube" if detected_provider == "youtube" else "SoundCloud"
                    self.cookies_status_badge.configure(
                        text=f"✅ {provider_name}",
                        fg_color=("#d1fae5", "#064e3b"),
                        text_color=("#065f46", "#6ee7b7")
                    )
                else:
                    self.cookies_status_badge.configure(
                        text="✅ Carregado",
                        fg_color=("#dbeafe", "#1e3a8a"),
                        text_color=("#1d4ed8", "#93c5fd")
                    )
                
                # Salva automaticamente
                self._save_user_settings()
                
                messagebox.showinfo(
                    "Sucesso",
                    f"Arquivo de cookies válido e carregado!\n\n"
                    f"Provedor: {provider_name if detected_provider else 'Não detectado'}\n"
                    f"Os cookies foram salvos e serão carregados automaticamente na próxima vez que você abrir o aplicativo.\n\n"
                    f"Agora você já pode usar o Nexus sem erros HTTP."
                )
                
                # Detecta tema pelo arquivo de cookies (YouTube / SoundCloud)
                self._auto_detect_site_theme_from_cookies(file_path)
            else:
                messagebox.showerror("Erro", "Arquivo de cookies inválido!\n\nCertifique-se de exportar os cookies no formato Netscape (cookies.txt).")
    
    def _clear_cookies_file(self):
        """Remove o arquivo de cookies selecionado"""
        self.cookies_file = None
        self.cookies_provider = None
        self.cookies_entry.delete(0, tk.END)
        
        # Atualiza badge de status
        if hasattr(self, "cookies_status_badge"):
            self.cookies_status_badge.configure(
                text="⚠️ Não configurado",
                fg_color=("#fee2e2", "#7f1d1d"),
                text_color=("#b91c1c", "#fca5a5")
            )
        
        # Salva alterações
        self._save_user_settings()
        
        messagebox.showinfo(
            "Cookies removidos",
            "Os cookies foram removidos.\n\n"
            "Você precisará importar novos cookies antes de fazer downloads."
        )
    
    def _fetch_info(self):
        """Busca informações do vídeo/música sem baixar
        Mostra título, artista, duração, gênero, etc. antes do download
        """
        logger.info("Botão 'Buscar Info' clicado")

        # Exige cookies carregados para evitar erros HTTP
        if not self.cookies_file:
            messagebox.showwarning(
                "Cookies obrigatórios",
                "Para usar o Nexus com segurança e sem erros HTTP, é obrigatório importar um arquivo de cookies válido.\n\n"
                "Use o card '🔐 Importar Cookies' no topo da interface para selecionar seu arquivo cookies.txt exportado do navegador."
            )
            return

        url = self.url_entry.get().strip()

        # Detecta tema pelo domínio da URL
        self._auto_detect_site_theme_from_url(url)

        if not url:
            messagebox.showwarning("Aviso", "Por favor, insira uma URL válida.")
            return
        
        # Validação básica de URL
        if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'soundcloud.com', 'youtube.com/watch', 'music.youtube.com']):
            messagebox.showwarning("Aviso", "URL inválida. Por favor, insira uma URL do YouTube, YouTube Music ou SoundCloud.")
            return
        
        self.current_url = url
        
        # Disable entry e button
        self.url_entry.configure(state="disabled")
        if hasattr(self, 'fetch_info_btn'):
            self.fetch_info_btn.configure(state="disabled")
        
        # Mostra loading temporário no info_frame (não usa progress_frame)
        # Garante que aparece logo após o url_frame
        # Remove temporariamente outros frames que podem estar na frente
        try:
            self.progress_frame.pack_forget()
        except:
            pass
        
        # Mostra info_frame logo após url_frame
        self.info_frame.pack(fill="x", padx=10, pady=(8, 10))
        
        # Limpa frame anterior
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        
        loading_label = ctk.CTkLabel(
            self.info_frame,
            text="🔍 Buscando informações do vídeo/música...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#2c3e50", "#ecf0f1")
        )
        loading_label.pack(padx=18, pady=18)
        
        loading_detail = ctk.CTkLabel(
            self.info_frame,
            text="Conectando ao servidor...",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        loading_detail.pack(padx=18, pady=(0, 18))
        
        # Scroll para mostrar o info_frame
        self.root.update_idletasks()
        try:
            # Tenta scrollar para mostrar o info_frame
            if hasattr(self, 'main_frame_ref') and self.main_frame_ref:
                self.main_frame_ref._parent_canvas.update_idletasks()
        except:
            pass
        
        def fetch_thread():
            try:
                logger.info(f"Iniciando busca de informações para: {url}")
                
                downloader = NexusDownloader(
                    self.download_dir, 
                    config.FFMPEG_PATH,
                    cookies_file=self.cookies_file
                )
                
                # Atualiza progresso
                def update_progress():
                    self.progress_bar.set(0.5)
                    self.progress_percent_label.configure(text="50%")
                    self.progress_label.configure(text="🔍 Conectando ao servidor...")
                    self.progress_detail_label.configure(text="Extraindo informações...")
                    self.root.update_idletasks()
                
                self.root.after(0, update_progress)
                
                info = downloader._get_video_info(url)
                
                logger.info(f"Informações obtidas: {info.get('title', 'N/A')}")
                
                if not info:
                    self.root.after(0, lambda: messagebox.showerror("Erro", "Não foi possível obter informações do vídeo/música.\n\nPossíveis causas:\n- URL inválida\n- Vídeo privado ou restrito (use cookies)\n- Problema de conexão\n- Vídeo não disponível"))
                    self.root.after(0, self._reset_fetch_ui)
                    return
                
                if not info.get('title') or info.get('title') == 'Unknown':
                    self.root.after(0, lambda: messagebox.showerror("Erro", "Não foi possível obter título do vídeo/música.\n\nVerifique a URL e tente novamente."))
                    self.root.after(0, self._reset_fetch_ui)
                    return
                
                # Sucesso - mostra informações
                def show_success():
                    self._display_info(info)
                    self._reset_fetch_ui()
                
                self.root.after(0, show_success)
                
            except Exception as e:
                import traceback
                error_msg = str(e)
                logger.error(f"Erro ao buscar info: {traceback.format_exc()}")
                
                # Mensagem de erro mais amigável
                detailed_msg = f"Erro ao buscar informações:\n\n{error_msg}"
                if "Private video" in error_msg or "Sign in" in error_msg:
                    detailed_msg += "\n\n💡 Dica: Este vídeo pode ser privado. Use cookies para acessar."
                elif "unavailable" in error_msg.lower():
                    detailed_msg += "\n\n💡 Dica: O vídeo pode não estar disponível ou foi removido."
                
                self.root.after(0, lambda: messagebox.showerror("Erro", detailed_msg))
                self.root.after(0, lambda: self.info_frame.pack_forget())
                self.root.after(0, self._reset_fetch_ui)
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def _reset_fetch_ui(self):
        """Reabilita campos após buscar informações"""
        self.url_entry.configure(state="normal")
        if hasattr(self, 'fetch_info_btn'):
            self.fetch_info_btn.configure(state="normal")
    
    def _display_info(self, info: dict):
        """Exibe informações do vídeo/música - melhorado (logo abaixo da seção Buscar Info)"""
        # Garante que está visível (já está na ordem correta por ter sido criado logo após url_frame)
        if not self.info_frame.winfo_viewable():
            self.info_frame.pack(fill="x", padx=10, pady=(8, 10))
        
        # Limpa frame anterior
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        
        # Título principal
        title_label = ctk.CTkLabel(
            self.info_frame,
            text=f"📋 {info.get('title', 'Título não disponível')}",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#111827", "#e5e7eb")
        )
        title_label.pack(anchor="w", padx=18, pady=(18, 6))

        # Linha de “badges” (duração, tipo, playlist)
        badges_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        badges_frame.pack(fill="x", padx=18, pady=(0, 8))

        duration_badge = ctk.CTkLabel(
            badges_frame,
            text=f"⏱ {self._format_duration(info.get('duration', 0))}",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#e5e7eb", "#374151"),
            text_color=("#111827", "#e5e7eb"),
            corner_radius=12,
            padx=8,
            pady=4
        )
        duration_badge.pack(side="left", padx=(0, 6))

        # Tipo atual (áudio/vídeo)
        current_type = self.download_type_var.get() if hasattr(self, "download_type_var") else "audio"
        type_text = "🎵 Áudio" if current_type == "audio" else "🎬 Vídeo"
        type_badge = ctk.CTkLabel(
            badges_frame,
            text=type_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#fee2e2", "#7f1d1d"),
            text_color=("#b91c1c", "#fecaca"),
            corner_radius=12,
            padx=8,
            pady=4
        )
        type_badge.pack(side="left", padx=6)

        # Badge de playlist (se aplicável)
        if info.get("is_playlist"):
            playlist_badge = ctk.CTkLabel(
                badges_frame,
                text="📂 Playlist",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("#e0f2fe", "#1e3a8a"),
                text_color=("#1d4ed8", "#bfdbfe"),
                corner_radius=12,
                padx=8,
                pady=4
            )
            playlist_badge.pack(side="left", padx=6)

        # Detalhes textuais
        details_text = f"🎤 Artista: {info.get('artist', 'N/A')}\n"
        details_text += f"💿 Álbum: {info.get('album', 'N/A')}\n"
        if info.get('year'):
            details_text += f"📅 Ano: {info.get('year')}\n"
        if info.get('genre'):
            details_text += f"🎵 Gênero: {info.get('genre')}"

        details_label = ctk.CTkLabel(
            self.info_frame,
            text=details_text,
            font=ctk.CTkFont(size=13),
            anchor="w",
            justify="left",
            text_color=("#374151", "#d1d5db")
        )
        details_label.pack(anchor="w", padx=18, pady=(0, 16))
    
    def _format_duration(self, seconds) -> str:
        """Formata duração em segundos"""
        if not seconds or seconds == 0:
            return "N/A"
        
        # Converte para int se for float
        total_seconds = int(float(seconds))
        
        mins, secs = divmod(total_seconds, 60)
        hours, mins = divmod(mins, 60)
        
        if hours:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
    
    def _start_download(self):
        """Inicia o processo de download"""
        # Exige cookies carregados para evitar erros HTTP
        if not self.cookies_file:
            messagebox.showwarning(
                "Cookies obrigatórios",
                "Antes de iniciar qualquer download, importe um arquivo de cookies válido.\n\n"
                "Use o card '🔐 Importar Cookies' no topo da interface para selecionar seu arquivo cookies.txt.\n\n"
                "Isso garante que o YouTube/YouTube Music/SoundCloud reconheça sua sessão e evita a maioria dos erros de HTTP/autenticação."
            )
            return
        
        # Verifica se o cookie é do provedor correto para a URL
        url = self.url_entry.get().strip()
        if url:
            url_provider = None
            if any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'music.youtube.com']):
                url_provider = "youtube"
            elif 'soundcloud.com' in url.lower():
                url_provider = "soundcloud"
            
            if url_provider and self.cookies_provider and url_provider != self.cookies_provider:
                current_provider = "YouTube" if self.cookies_provider == "youtube" else "SoundCloud"
                needed_provider = "YouTube" if url_provider == "youtube" else "SoundCloud"
                response = messagebox.askyesno(
                    "Provedor diferente detectado",
                    f"Você está tentando baixar de {needed_provider}, mas seus cookies salvos são de {current_provider}.\n\n"
                    f"Para evitar erros, é recomendado importar cookies específicos de {needed_provider}.\n\n"
                    f"Deseja continuar mesmo assim? (Pode ocorrer erros HTTP)"
                )
                if not response:
                    return

        url = self.url_entry.get().strip()

        # Detecta tema pelo domínio da URL
        self._auto_detect_site_theme_from_url(url)

        if not url:
            messagebox.showwarning("Aviso", "Por favor, insira uma URL válida.")
            return
        
        # Atualiza diretório
        self.download_dir = self.dir_entry.get().strip() or config.DEFAULT_DOWNLOAD_DIR
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)

        # Atualiza resumo do progresso
        download_type = self.download_type_var.get()
        output_format = self.format_var.get()
        tipo_texto = "Áudio" if download_type == "audio" else "Vídeo"
        resumo = f"{tipo_texto} • Formato: {output_format.upper()} • Pasta: {self.download_dir}"
        if hasattr(self, "progress_summary_label") and self.progress_summary_label:
            self.progress_summary_label.configure(text=resumo)
        
        # Atualiza arquivo de cookies
        cookies_path = self.cookies_file
        if not cookies_path:
            # Tenta obter do entry
            entry_text = self.cookies_entry.get().strip()
            if entry_text and os.path.exists(entry_text):
                cookies_path = entry_text
        
        # Inicializa componentes com cookies
        self.downloader = NexusDownloader(
            self.download_dir,
            config.FFMPEG_PATH,
            self._update_progress,
            cookies_file=cookies_path
        )
        self.organizer = NexusOrganizer(self.download_dir, config.FOLDER_STRUCTURE)
        
        # Mostra progress bar e reseta etapas (logo ACIMA do botão de download)
        # Usa parâmetro 'before' para aparecer antes do frame do botão
        if hasattr(self, "download_btn_frame") and self.download_btn_frame:
            self.progress_frame.pack(fill="x", padx=10, pady=(10, 10), before=self.download_btn_frame)
        else:
            self.progress_frame.pack(fill="x", padx=10, pady=(10, 10))
        self.progress_bar.set(0)
        self.progress_percent_label.configure(text="0%")
        self.progress_label.configure(text="⏳ Preparando download...")
        self.progress_detail_label.configure(text="Inicializando...")
        
        # Reseta todas as etapas
        for step_label in self.steps.values():
            step_label.configure(text=step_label.cget("text").replace("✅", "⬜").replace("⏳", "⬜"))
        
        # Disable download button mas mantém interface responsiva
        if hasattr(self, 'download_button') and self.download_button:
            self.download_button.configure(state="disabled")
        
        # Desabilita outros controles mas mantém interface responsiva
        self.url_entry.configure(state="disabled")
        if hasattr(self, 'fetch_info_btn'):
            self.fetch_info_btn.configure(state="disabled")
        
        # Garante que a interface atualize
        self.root.update_idletasks()
        self.download_active = True
        
        # Inicia download em thread separada
        thread = threading.Thread(target=self._download_thread, args=(url,), daemon=True)
        thread.start()
    
    def _download_thread(self, url: str):
        """Thread de download"""
        try:
            download_type = self.download_type_var.get()
            output_format = self.format_var.get()
            
            # Atualiza progresso inicial
            self.root.after(0, lambda: self._update_progress(5, "📥 Iniciando download...", "Preparando conexão..."))
            
            if download_type == "audio":
                # Callback para progresso de playlist
                def playlist_progress(item_num, total, title, status):
                    percent = int((item_num / total) * 30) + 10  # 10-40% para download da playlist
                    self.root.after(0, lambda: self._update_progress(
                        percent,
                        f"📥 Baixando playlist: {item_num}/{total}",
                        f"{title} - {status}"
                    ))
                
                self.root.after(0, lambda: self._update_progress(10, "📥 Verificando URL...", "Detectando se é playlist ou item único..."))
                audio_quality = self.audio_quality_var.get() if hasattr(self, 'audio_quality_var') else "192"
                result = self.downloader.download_audio(url, output_format, None, None, playlist_progress, audio_quality)
            else:
                quality = self.quality_var.get()
                self.root.after(0, lambda: self._update_progress(10, "📹 Baixando vídeo...", f"Formato: {output_format.upper()}, Qualidade: {quality}"))
                result = self.downloader.download_video(url, output_format, quality)
            
            # Verifica se é playlist
            if result.get('is_playlist'):
                # Processa resultados da playlist
                self._process_playlist_result(result, download_type)
                return
            
            if result.get('success'):
                # Download único concluído
                self.root.after(0, lambda: self._update_progress(60, "✅ Download concluído!", "Processando arquivo..."))
                
                file_path = result['file_path']
                metadata = result.get('metadata', {})
                cover_path = result.get('thumbnail_path')
                
                # Organiza arquivo se necessário (ANTES de aplicar metadados)
                if self.organize_var.get():
                    self.root.after(0, lambda: self._update_progress(70, "📁 Organizando arquivo...", "Criando estrutura de pastas..."))
                    org_result = self.organizer.organize_file(
                        file_path,
                        metadata,
                        cover_path
                    )
                    
                    if org_result.get('success'):
                        file_path = org_result['file_path']
                        # Atualiza cover_path se foi movida
                        if org_result.get('cover_path'):
                            cover_path = org_result['cover_path']
                        self.root.after(0, lambda: self._update_progress(75, "✅ Arquivo organizado!", "Aplicando metadados..."))
                else:
                    self.root.after(0, lambda: self._update_progress(70, "⏭️ Pulando organização...", "Aplicando metadados..."))
                
                # SEMPRE aplica metadados se disponíveis (para áudio e vídeo)
                if config.METADATA_ENABLED and metadata:
                    # Para áudio, sempre aplica com capa
                    if download_type == "audio":
                        self.root.after(0, lambda: self._update_progress(80, "🏷️ Aplicando metadados...", "Adicionando informações e capa..."))
                        
                        # Verifica se tem capa antes de aplicar
                        has_cover = cover_path and os.path.exists(cover_path)
                        if has_cover:
                            cover_size = os.path.getsize(cover_path)
                            logger.info(f"Aplicando metadados com capa: {cover_path} ({cover_size} bytes)")
                        else:
                            logger.warning("Nenhuma capa disponível para aplicar")
                        
                        # Aplica metadados COM capa
                        success = self.metadata_manager.set_metadata(
                            file_path,
                            metadata,
                            cover_path  # Aplica a capa nos metadados
                        )
                        
                        if success:
                            logger.info("✅ Metadados aplicados com sucesso")
                            self.root.after(0, lambda: self._update_progress(90, "✅ Metadados aplicados!", "Limpando arquivos temporários..."))
                            
                            # Se sucesso=True E tinha cover_path, a capa foi aplicada
                            # Deleta a thumbnail temporária (a capa já está no arquivo)
                            if has_cover and cover_path and os.path.exists(cover_path):
                                import time
                                time.sleep(0.3)  # Pequena espera para garantir salvamento
                                
                                try:
                                    # Tenta deletar a thumbnail temporária
                                    os.remove(cover_path)
                                    logger.info(f"🗑️ Thumbnail temporária removida: {cover_path}")
                                except Exception as e:
                                    logger.warning(f"⚠️ Erro ao remover thumbnail {cover_path}: {e}")
                        else:
                            logger.warning("❌ Falha ao aplicar metadados")
                    # Para vídeo, delegamos os metadados diretamente para o yt-dlp (FFmpeg)
                    # pois o Mutagen foca mais em arquivos de áudio puro e pode não ser lido bem pelo Windows Explorer
                    elif download_type == "video":
                        self.root.after(0, lambda: self._update_progress(80, "✅ Metadados aplicados nativamente!", "Limpando arquivos temporários..."))
                        # Remove thumbnail de vídeo
                        if cover_path and os.path.exists(cover_path):
                            try:
                                os.remove(cover_path)
                            except:
                                pass
                
                # Limpa arquivos temporários na pasta raiz
                self.root.after(0, lambda: self._update_progress(95, "🧹 Limpando arquivos temporários...", "Removendo thumbnails não utilizadas..."))
                self._clean_root_thumbnails()
                
                # Completa o processo
                self.root.after(0, lambda: self._update_progress(100, "✅ Processo concluído!", f"Arquivo salvo: {os.path.basename(file_path)}"))
                self.root.after(500, lambda: self._download_complete(True, file_path))
            else:
                error = result.get('error', 'Erro desconhecido')
                self.root.after(0, lambda err=error: self._download_complete(False, err))
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                error_msg = "Bloqueio Temporário do YouTube (Erro 429 - Muitas requisições).\nPor favor, aguarde alguns minutos ou horas antes de tentar novamente, pois seu IP foi limitado temporariamente pelo YouTube."
            self.root.after(0, lambda err=error_msg: self._download_complete(False, err))
    
    def _update_progress(self, percent: int, message: str, detail: str = ""):
        """Atualiza barra de progresso com informações detalhadas"""
        def update():
            if not self.download_active:
                return
                
            # Atualiza barra de progresso
            progress_value = max(0, min(100, percent)) / 100
            self.progress_bar.set(progress_value)
            self.progress_percent_label.configure(text=f"{percent}%")
            
            # Atualiza labels
            if message:
                self.progress_label.configure(text=message)
            if detail:
                self.progress_detail_label.configure(text=detail)
            
            # Atualiza etapas baseado na porcentagem
            if percent < 25:
                self._update_step('download', '⏳')
            elif percent < 50:
                self._update_step('download', '✅')
                self._update_step('conversion', '⏳')
            elif percent < 75:
                self._update_step('conversion', '✅')
                self._update_step('organization', '⏳')
            elif percent < 95:
                self._update_step('organization', '✅')
                self._update_step('metadata', '⏳')
            else:
                self._update_step('metadata', '✅')
            
            # Força atualização da interface
            try:
                self.root.update_idletasks()
            except:
                pass
        
        self.root.after(0, update)
    
    def _update_step(self, step_name: str, status: str):
        """Atualiza status de uma etapa com cores"""
        if step_name in self.steps:
            current_text = self.steps[step_name].cget("text")
            # Remove qualquer status anterior
            current_text = current_text.replace("✅", "").replace("⏳", "").replace("⬜", "").strip()
            
            # Define cor baseado no status
            if status == "✅":
                color = ("#10b981", "#10b981")  # Verde
            elif status == "⏳":
                color = ("#f59e0b", "#f59e0b")  # Laranja/Amarelo
            else:
                color = ("#6b7280", "#6b7280")  # Cinza
            
            self.steps[step_name].configure(
                text=f"{status} {current_text}",
                text_color=color
            )
    
    def _download_complete(self, success: bool, message: str):
        """Callback quando download completa"""
        self.download_active = False
        
        # Reabilita controles
        if self.download_button:
            self.download_button.configure(state="normal")
        self.url_entry.configure(state="normal")
        if hasattr(self, 'fetch_info_btn'):
            self.fetch_info_btn.configure(state="normal")
        
        if success:
            # Mantém progresso em 100% por um momento
            self.progress_label.configure(text="✅ Download concluído com sucesso!")
            self.progress_detail_label.configure(text=f"Arquivo: {os.path.basename(message)}")

            # Adiciona ao histórico da sessão
            try:
                self._add_history_entry(success=True, detail=message)
            except Exception:
                pass
            
            # Mostra notificação com opção de abrir pasta
            self.root.after(500, lambda: self._show_success_dialog(message))
            
            # Esconde progresso após notificação
            self.root.after(3000, lambda: self.progress_frame.pack_forget())
        else:
            self.progress_label.configure(text=f"❌ Erro no download")
            self.progress_detail_label.configure(text=f"{message}")
            self.progress_bar.set(0)
            self.progress_percent_label.configure(text="0%")
            
            messagebox.showerror("❌ Erro", f"Erro no download:\n\n{message}")

    def _show_success_dialog(self, file_path: str):
        """Mostra diálogo de sucesso com opção de abrir a pasta"""
        response = messagebox.askyesno(
            "✅ Sucesso",
            f"Download concluído!\n\n📁 Arquivo salvo em:\n{file_path}\n\n🎵 Metadados aplicados!\n\nDeseja abrir a pasta do arquivo?"
        )
        if response:
            try:
                import subprocess
                # O Windows Explorer abre a pasta e seleciona o arquivo
                file_path_win = os.path.normpath(file_path)
                subprocess.run(['explorer', '/select,', file_path_win])
            except Exception as e:
                logger.error(f"Erro ao abrir pasta: {e}")
        
        # Esconde progresso
        self.progress_frame.pack_forget()
    
    def _process_playlist_result(self, result: dict, download_type: str):
        """Processa resultados de download de playlist"""
        total = result.get('total_items', 0)
        downloaded = result.get('downloaded', 0)
        failed = result.get('failed', 0)
        results = result.get('results', [])
        playlist_title = result.get('playlist_title', 'Unknown Playlist')
        
        logger.info(f"Processando playlist: {downloaded}/{total} itens baixados, {failed} falhas")
        
        # Atualiza progresso
        self.root.after(0, lambda: self._update_progress(
            50,
            f"📁 Organizando playlist: {playlist_title}",
            f"{downloaded}/{total} itens - Colocando todos na mesma pasta..."
        ))
        
        # Prepara arquivos para organização
        files_to_organize = []
        for item_result in results:
            file_path = item_result.get('file_path')
            metadata = item_result.get('metadata', {})
            cover_path = None
            
            if not file_path or not os.path.exists(file_path):
                continue
            
            # Procura thumbnail próxima ao arquivo
            base_path = os.path.splitext(file_path)[0]
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                thumb_path = base_path + ext
                if os.path.exists(thumb_path):
                    cover_path = thumb_path
                    break
            
            files_to_organize.append({
                'file_path': file_path,
                'metadata': metadata,
                'cover_path': cover_path
            })
        
        # Organiza todos os arquivos na mesma pasta da playlist (se organização está habilitada)
        if self.organize_var.get() and files_to_organize:
            self.root.after(0, lambda: self._update_progress(
                60,
                f"📁 Organizando em: {playlist_title}",
                "Criando pasta única para toda a playlist..."
            ))
            
            org_result = self.organizer.organize_playlist(files_to_organize, playlist_title)
            
            if org_result.get('success'):
                # Atualiza os caminhos dos arquivos organizados
                organized_items = org_result.get('items', [])
                for i, org_item in enumerate(organized_items):
                    if org_item.get('success') and i < len(files_to_organize):
                        files_to_organize[i]['file_path'] = org_item.get('file_path')
        
        # Processa cada arquivo: aplica metadados
        self.root.after(0, lambda: self._update_progress(
            70,
            f"🏷️ Aplicando metadados...",
            f"{len(files_to_organize)} arquivos"
        ))
        
        for idx, file_item in enumerate(files_to_organize, 1):
            file_path = file_item.get('file_path')
            metadata = file_item.get('metadata', {})
            cover_path = file_item.get('cover_path')
            
            if not file_path or not os.path.exists(file_path):
                continue
            
            # Atualiza progresso
            self.root.after(0, lambda i=idx, total_items=len(files_to_organize), title=metadata.get('title', 'Unknown'): 
                self._update_progress(
                    70 + int((i / total_items) * 20),
                    f"🏷️ Aplicando metadados: {i}/{total_items}",
                    title
                ))
            
            # Aplica metadados
            if config.METADATA_ENABLED and download_type == "audio" and metadata:
                self.metadata_manager.set_metadata(file_path, metadata, cover_path)
                
                # Remove thumbnail após aplicar (se estiver na pasta da playlist)
                if cover_path and os.path.exists(cover_path):
                    try:
                        os.remove(cover_path)
                        logger.info(f"Thumbnail removida: {cover_path}")
                    except Exception as e:
                        logger.warning(f"Erro ao remover thumbnail: {e}")
        
        # Limpa thumbnails na pasta raiz
        self.root.after(0, lambda: self._update_progress(
            95,
            "🧹 Limpando arquivos temporários...",
            "Removendo thumbnails da raiz..."
        ))
        
        self._clean_root_thumbnails()
        
        # Conclui
        playlist_folder = ""
        if self.organize_var.get() and files_to_organize:
            playlist_folder = self.organizer._build_playlist_folder_path(playlist_title)
            success_msg = f"✅ Playlist organizada em:\n{playlist_folder}\n\n{downloaded}/{total} itens processados"
        else:
            success_msg = f"✅ {downloaded}/{total} itens processados"
        
        if failed > 0:
            success_msg += f" ({failed} falhas)"
        
        self.root.after(0, lambda: self._update_progress(100, "✅ Playlist processada!", success_msg))
        final_msg = playlist_folder if playlist_folder else f"Playlist: {playlist_title} - {downloaded}/{total} itens baixados" + (f" ({failed} falhas)" if failed > 0 else "")
        self.root.after(500, lambda: self._download_complete(
            downloaded > 0,
            final_msg
        ))
    
    def _clean_root_thumbnails(self):
        """Limpa todas as thumbnails na pasta raiz"""
        base_dir = self.download_dir
        cleaned_count = 0
        
        try:
            if os.path.exists(base_dir):
                for item in os.listdir(base_dir):
                    item_path = os.path.join(base_dir, item)
                    # Apenas arquivos, não pastas
                    if os.path.isfile(item_path):
                        item_lower = item.lower()
                        # Remove QUALQUER imagem/thumbnail na raiz
                        if item_lower.endswith(('.webp', '.jpg', '.jpeg', '.png')):
                            try:
                                os.remove(item_path)
                                cleaned_count += 1
                                logger.info(f"🗑️ Thumbnail da raiz removida: {item}")
                            except Exception as e:
                                logger.warning(f"⚠️ Erro ao remover {item}: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar thumbnails da raiz: {e}")
        
        if cleaned_count > 0:
            logger.info(f"✅ Limpeza concluída: {cleaned_count} thumbnail(s) removida(s) da raiz")
    
    def run(self):
        """Inicia o aplicativo"""
        self.root.mainloop()

