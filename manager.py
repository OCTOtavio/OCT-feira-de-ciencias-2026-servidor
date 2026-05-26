import json
import shutil
import unicodedata
from datetime import date
from pathlib import Path

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog

BASE_DIR = Path("noticias")
LISTA_JSON = Path("noticias.json")
CONFIG_JSON = Path("config.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DEFAULT_CONFIG = {
    "Nome": "OCT News",
    "Icone": "favicon.ico",
    "Escola": "Escola Estadual Orlando da Costa Telles",
    "Descricao": (
        "Portal de noticias com cobertura do entorno escolar, clima, seguranca, "
        "educacao e acontecimentos que impactam a rotina da comunidade."
    ),
    "HeroTitulo": "As editorias que movem a rotina da Orlando da Costa Telles.",
    "HeroResumo": (
        "Um portal local para acompanhar clima, ocorrencias, educacao, comunidade "
        "e assuntos globais com impacto no cotidiano da escola e do bairro."
    ),
    "Rodape": "Cobertura local, escolar e regional da Editora OCT.",
    "Categorias": [
        {"Categoria": "Clima em Foco", "Subcategorias": []},
        {"Categoria": "Casos Policiais", "Subcategorias": []},
        {
            "Categoria": "Globalizacao",
            "Subcategorias": [
                "Brasil",
                "America Latina",
                "America do Sul",
                "Europa",
                "Asia",
                "America do Norte",
                "America Central",
                "Africa",
                "Oceania",
            ],
        },
    ],
}


def slugify(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    texto = texto.replace("/", " ").replace("\\", " ")
    partes = [parte for parte in texto.lower().strip().split() if parte]
    return "_".join(partes) or "noticia"


def caminho_relativo(caminho):
    return Path(caminho).as_posix()


def hoje_iso():
    return date.today().isoformat()


def carregar_json(caminho, fallback):
    if not caminho.exists():
        return fallback
    try:
        with caminho.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return fallback


def salvar_json(caminho, data):
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalizar_config(config):
    base = DEFAULT_CONFIG.copy()
    base.update({key: value for key, value in config.items() if key != "Categorias"})

    categorias = config.get("Categorias", DEFAULT_CONFIG["Categorias"])
    categorias_limpas = []
    for item in categorias:
        nome = str(item.get("Categoria", "")).strip()
        if not nome:
            continue
        subcategorias = [
            str(sub).strip()
            for sub in item.get("Subcategorias", [])
            if str(sub).strip()
        ]
        categorias_limpas.append(
            {"Categoria": nome, "Subcategorias": subcategorias}
        )

    if not categorias_limpas:
        categorias_limpas = DEFAULT_CONFIG["Categorias"]

    base["Categorias"] = categorias_limpas
    return base


def carregar_config():
    return normalizar_config(carregar_json(CONFIG_JSON, DEFAULT_CONFIG))


def salvar_config(config):
    salvar_json(CONFIG_JSON, normalizar_config(config))


def carregar_estrutura(caminho):
    try:
        with Path(caminho).open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def salvar_estrutura_em_disco(noticia_path, estrutura):
    caminho = Path(noticia_path) / "estrutura.json"
    salvar_json(caminho, estrutura)


def criar_estrutura_padrao(titulo):
    return {
        "titulo": titulo,
        "resumo": "",
        "data": hoje_iso(),
        "categoria": "",
        "subcategoria": "",
        "imagemCapa": "",
        "conteudo": [],
    }


def preparar_pasta_noticia(pasta):
    (pasta / "paragrafos").mkdir(parents=True, exist_ok=True)
    (pasta / "imagens").mkdir(exist_ok=True)
    (pasta / "midia").mkdir(exist_ok=True)
    (pasta / "documentos").mkdir(exist_ok=True)


def listar_noticias_publicadas():
    noticias = []
    if not BASE_DIR.exists():
        return noticias

    for estrutura_path in BASE_DIR.glob("*/estrutura.json"):
        estrutura = carregar_estrutura(estrutura_path)
        if not estrutura:
            continue

        pasta = estrutura_path.parent
        noticias.append(
            {
                "slug": slugify(pasta.name),
                "pasta": caminho_relativo(pasta),
                "estrutura": caminho_relativo(estrutura_path),
                "titulo": estrutura.get("titulo", pasta.name),
                "resumo": estrutura.get("resumo", ""),
                "data": estrutura.get("data", ""),
                "categoria": estrutura.get("categoria", ""),
                "subcategoria": estrutura.get("subcategoria", ""),
                "imagemCapa": estrutura.get("imagemCapa", ""),
            }
        )

    noticias.sort(key=lambda item: item.get("data", ""), reverse=True)
    return noticias


def sincronizar_noticias():
    noticias = listar_noticias_publicadas()
    salvar_json(LISTA_JSON, noticias)
    return noticias


def carregar_noticia_existente(item):
    noticia_path = Path(item["pasta"])
    estrutura = carregar_estrutura(item["estrutura"])
    if not estrutura:
        return None, None
    return noticia_path, estrutura


def subcategorias_da_categoria(config, categoria):
    for item in config.get("Categorias", []):
        if item.get("Categoria") == categoria:
            return item.get("Subcategorias", [])
    return []


def descricao_bloco(item, indice):
    tipo = item.get("tipo", "bloco").upper()
    detalhe = item.get("arquivo", "") if item.get("tipo") != "titulo" else item.get("texto", "")
    detalhe = detalhe.replace("\n", " ").strip()
    if len(detalhe) > 58:
        detalhe = detalhe[:55] + "..."
    return f"{indice + 1:02d}. {tipo} - {detalhe or 'sem conteudo'}"


def ler_conteudo_item(noticia_path, item):
    tipo = item.get("tipo")
    if tipo == "texto":
        caminho = Path(noticia_path) / item["arquivo"]
        if caminho.exists():
            return caminho.read_text(encoding="utf-8")
        return ""
    if tipo == "titulo":
        return item.get("texto", "")
    return item.get("arquivo", "")


def salvar_conteudo_item(noticia_path, item, novo_valor):
    tipo = item.get("tipo")
    if tipo == "texto":
        caminho = Path(noticia_path) / item["arquivo"]
        caminho.write_text(novo_valor, encoding="utf-8")
    elif tipo == "titulo":
        item["texto"] = novo_valor
    else:
        item["arquivo"] = novo_valor


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config_data = carregar_config()
        self.current_news_path = None
        self.current_news = None
        self.current_block_index = None
        self.selected_news_slug = None
        self.selected_site_category_index = None

        self.title(f"{self.config_data['Nome']} - Manager")
        self.geometry("1560x920")
        self.minsize(1320, 820)

        self.criar_layout()
        self.preencher_site_form()
        self.atualizar_listas_noticias()
        self.preparar_nova_noticia()

    def criar_layout(self):
        self.header = ctk.CTkFrame(self, corner_radius=0)
        self.header.pack(fill="x")

        self.header_title = ctk.CTkLabel(
            self.header,
            text=f"{self.config_data['Nome']} - painel de administracao",
            font=("Arial", 26, "bold"),
        )
        self.header_title.pack(anchor="w", padx=24, pady=(18, 4))

        self.header_subtitle = ctk.CTkLabel(
            self.header,
            text="Gerencie a configuracao do portal, as editorias e as noticias publicadas.",
            text_color="gray",
        )
        self.header_subtitle.pack(anchor="w", padx=24, pady=(0, 16))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=14)

        self.site_tab = self.tabs.add("Site")
        self.news_tab = self.tabs.add("Noticias")

        self.criar_aba_site()
        self.criar_aba_noticias()

    def criar_aba_site(self):
        self.site_tab.grid_columnconfigure(0, weight=1)
        self.site_tab.grid_columnconfigure(1, weight=2)
        self.site_tab.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self.site_tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        right = ctk.CTkScrollableFrame(self.site_tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Editorias", font=("Arial", 22, "bold")).pack(
            anchor="w", padx=16, pady=(18, 10)
        )
        self.site_categories_frame = ctk.CTkScrollableFrame(left)
        self.site_categories_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        ctk.CTkButton(
            left,
            text="Nova categoria",
            command=self.nova_categoria_site,
            height=38,
        ).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(
            left,
            text="Remover categoria",
            command=self.remover_categoria_site,
            fg_color="#a81d1d",
            hover_color="#8a1212",
            height=38,
        ).pack(fill="x", padx=12, pady=(0, 12))

        self.site_status_var = ctk.StringVar(value="Edite os dados gerais do portal e as categorias.")
        ctk.CTkLabel(
            right,
            text="Configuracao do portal",
            font=("Arial", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))
        ctk.CTkLabel(
            right,
            textvariable=self.site_status_var,
            text_color="gray",
            wraplength=620,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))

        self.site_name_entry = ctk.CTkEntry(right, placeholder_text="Nome do portal", height=38)
        self.site_name_entry.grid(row=2, column=0, sticky="ew", padx=18, pady=6)

        self.site_icon_entry = ctk.CTkEntry(right, placeholder_text="Icone", height=38)
        self.site_icon_entry.grid(row=3, column=0, sticky="ew", padx=18, pady=6)

        self.site_school_entry = ctk.CTkEntry(right, placeholder_text="Escola", height=38)
        self.site_school_entry.grid(row=4, column=0, sticky="ew", padx=18, pady=6)

        ctk.CTkLabel(right, text="Descricao do portal", font=("Arial", 14, "bold")).grid(
            row=5, column=0, sticky="w", padx=18, pady=(12, 6)
        )
        self.site_description_box = ctk.CTkTextbox(right, height=90)
        self.site_description_box.grid(row=6, column=0, sticky="ew", padx=18, pady=6)

        self.site_hero_title_entry = ctk.CTkEntry(right, placeholder_text="Titulo do hero", height=38)
        self.site_hero_title_entry.grid(row=7, column=0, sticky="ew", padx=18, pady=6)

        ctk.CTkLabel(right, text="Resumo do hero", font=("Arial", 14, "bold")).grid(
            row=8, column=0, sticky="w", padx=18, pady=(12, 6)
        )
        self.site_hero_summary_box = ctk.CTkTextbox(right, height=88)
        self.site_hero_summary_box.grid(row=9, column=0, sticky="ew", padx=18, pady=6)

        self.site_footer_entry = ctk.CTkEntry(right, placeholder_text="Texto do rodape", height=38)
        self.site_footer_entry.grid(row=10, column=0, sticky="ew", padx=18, pady=6)

        ctk.CTkLabel(right, text="Categoria selecionada", font=("Arial", 18, "bold")).grid(
            row=11, column=0, sticky="w", padx=18, pady=(18, 6)
        )
        self.site_category_name_entry = ctk.CTkEntry(
            right, placeholder_text="Nome da categoria", height=38
        )
        self.site_category_name_entry.grid(row=12, column=0, sticky="ew", padx=18, pady=6)

        ctk.CTkLabel(right, text="Subcategorias (uma por linha)", font=("Arial", 14, "bold")).grid(
            row=13, column=0, sticky="w", padx=18, pady=(12, 6)
        )
        self.site_subcategories_box = ctk.CTkTextbox(right, height=110)
        self.site_subcategories_box.grid(row=14, column=0, sticky="ew", padx=18, pady=6)

        buttons_row = ctk.CTkFrame(right, fg_color="transparent")
        buttons_row.grid(row=15, column=0, sticky="ew", padx=18, pady=(12, 18))
        buttons_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            buttons_row,
            text="Nova categoria",
            command=self.nova_categoria_site,
            height=38,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            buttons_row,
            text="Salvar categoria",
            command=self.salvar_categoria_site,
            height=38,
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ctk.CTkButton(
            buttons_row,
            text="Salvar config.json",
            command=self.salvar_config_site,
            height=38,
            fg_color="#0b7d2d",
            hover_color="#086123",
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

    def criar_aba_noticias(self):
        self.news_tab.grid_columnconfigure(0, weight=1)
        self.news_tab.grid_columnconfigure(1, weight=2)
        self.news_tab.grid_columnconfigure(2, weight=3)
        self.news_tab.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self.news_tab)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        editor = ctk.CTkScrollableFrame(self.news_tab)
        editor.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        editor.grid_columnconfigure(0, weight=1)

        preview = ctk.CTkFrame(self.news_tab)
        preview.grid(row=0, column=2, sticky="nsew", padx=(8, 0), pady=8)

        ctk.CTkLabel(sidebar, text="Noticias", font=("Arial", 22, "bold")).pack(
            anchor="w", padx=16, pady=(18, 10)
        )
        self.news_list_frame = ctk.CTkScrollableFrame(sidebar)
        self.news_list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        ctk.CTkButton(
            sidebar,
            text="Nova noticia",
            command=self.preparar_nova_noticia,
            height=38,
        ).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(
            sidebar,
            text="Sincronizar noticias.json",
            command=self.atualizar_listas_noticias,
            height=38,
        ).pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(
            sidebar,
            text="Excluir noticia",
            command=self.excluir_noticia_atual,
            fg_color="#a81d1d",
            hover_color="#8a1212",
            height=38,
        ).pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(editor, text="Editor da noticia", font=("Arial", 24, "bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 6)
        )
        self.news_status_var = ctk.StringVar(value="Crie uma nova noticia ou carregue uma materia existente.")
        ctk.CTkLabel(
            editor,
            textvariable=self.news_status_var,
            text_color="gray",
            wraplength=540,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))

        self.news_title_entry = ctk.CTkEntry(editor, placeholder_text="Titulo da noticia", height=38)
        self.news_title_entry.grid(row=2, column=0, sticky="ew", padx=18, pady=6)

        ctk.CTkLabel(editor, text="Resumo", font=("Arial", 14, "bold")).grid(
            row=3, column=0, sticky="w", padx=18, pady=(12, 6)
        )
        self.news_summary_box = ctk.CTkTextbox(editor, height=90)
        self.news_summary_box.grid(row=4, column=0, sticky="ew", padx=18, pady=6)

        self.news_date_entry = ctk.CTkEntry(editor, placeholder_text="Data (AAAA-MM-DD)", height=38)
        self.news_date_entry.grid(row=5, column=0, sticky="ew", padx=18, pady=6)

        self.news_category_var = ctk.StringVar(value="")
        self.news_category_menu = ctk.CTkOptionMenu(
            editor,
            values=self.categorias_disponiveis_para_menu(),
            variable=self.news_category_var,
            command=self.on_categoria_change,
            height=36,
        )
        self.news_category_menu.grid(row=6, column=0, sticky="ew", padx=18, pady=6)

        self.news_subcategory_var = ctk.StringVar(value="Sem subcategoria")
        self.news_subcategory_menu = ctk.CTkOptionMenu(
            editor,
            values=["Sem subcategoria"],
            variable=self.news_subcategory_var,
            height=36,
        )
        self.news_subcategory_menu.grid(row=7, column=0, sticky="ew", padx=18, pady=6)

        self.news_cover_entry = ctk.CTkEntry(editor, placeholder_text="Caminho relativo da capa", height=38)
        self.news_cover_entry.grid(row=8, column=0, sticky="ew", padx=18, pady=6)

        cover_row = ctk.CTkFrame(editor, fg_color="transparent")
        cover_row.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 10))
        cover_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            cover_row,
            text="Selecionar capa",
            command=self.selecionar_capa_noticia,
            height=36,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            cover_row,
            text="Salvar metadados",
            command=self.salvar_metadados_noticia,
            height=36,
            fg_color="#0b7d2d",
            hover_color="#086123",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ctk.CTkLabel(editor, text="Blocos da noticia", font=("Arial", 18, "bold")).grid(
            row=10, column=0, sticky="w", padx=18, pady=(12, 8)
        )
        self.block_list_frame = ctk.CTkScrollableFrame(editor, height=180)
        self.block_list_frame.grid(row=11, column=0, sticky="ew", padx=18, pady=(0, 12))

        self.block_status_var = ctk.StringVar(
            value="Selecione um bloco para editar ou escreva um novo conteudo abaixo."
        )
        ctk.CTkLabel(
            editor,
            textvariable=self.block_status_var,
            text_color="gray",
            wraplength=540,
            justify="left",
        ).grid(row=12, column=0, sticky="w", padx=18, pady=(0, 10))

        self.block_type_var = ctk.StringVar(value="texto")
        self.block_type_menu = ctk.CTkOptionMenu(
            editor,
            values=["texto", "titulo", "imagem", "video", "audio", "documento"],
            variable=self.block_type_var,
            height=36,
        )
        self.block_type_menu.grid(row=13, column=0, sticky="ew", padx=18, pady=6)

        ctk.CTkLabel(editor, text="Conteudo do bloco ou caminho do arquivo", font=("Arial", 14, "bold")).grid(
            row=14, column=0, sticky="w", padx=18, pady=(12, 6)
        )
        self.block_editor = ctk.CTkTextbox(editor, height=180)
        self.block_editor.grid(row=15, column=0, sticky="ew", padx=18, pady=6)

        block_buttons = ctk.CTkFrame(editor, fg_color="transparent")
        block_buttons.grid(row=16, column=0, sticky="ew", padx=18, pady=(10, 20))
        block_buttons.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(
            block_buttons,
            text="Selecionar arquivo",
            command=self.selecionar_arquivo_bloco,
            height=36,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            block_buttons,
            text="Adicionar bloco",
            command=self.adicionar_bloco,
            height=36,
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ctk.CTkButton(
            block_buttons,
            text="Salvar bloco",
            command=self.salvar_bloco_atual,
            height=36,
        ).grid(row=0, column=2, sticky="ew", padx=6)
        ctk.CTkButton(
            block_buttons,
            text="Remover bloco",
            command=self.remover_bloco_atual,
            fg_color="#a81d1d",
            hover_color="#8a1212",
            height=36,
        ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        ctk.CTkLabel(preview, text="Pre-visualizacao", font=("Arial", 24, "bold")).pack(
            anchor="w", padx=16, pady=(18, 10)
        )
        self.preview_box = ctk.CTkScrollableFrame(preview)
        self.preview_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def categorias_disponiveis_para_menu(self):
        categorias = [item["Categoria"] for item in self.config_data.get("Categorias", [])]
        return categorias or ["Sem categoria"]

    def preencher_site_form(self):
        self.site_name_entry.delete(0, "end")
        self.site_name_entry.insert(0, self.config_data.get("Nome", ""))

        self.site_icon_entry.delete(0, "end")
        self.site_icon_entry.insert(0, self.config_data.get("Icone", ""))

        self.site_school_entry.delete(0, "end")
        self.site_school_entry.insert(0, self.config_data.get("Escola", ""))

        self.site_description_box.delete("1.0", "end")
        self.site_description_box.insert("1.0", self.config_data.get("Descricao", ""))

        self.site_hero_title_entry.delete(0, "end")
        self.site_hero_title_entry.insert(0, self.config_data.get("HeroTitulo", ""))

        self.site_hero_summary_box.delete("1.0", "end")
        self.site_hero_summary_box.insert("1.0", self.config_data.get("HeroResumo", ""))

        self.site_footer_entry.delete(0, "end")
        self.site_footer_entry.insert(0, self.config_data.get("Rodape", ""))

        self.refresh_site_categories()
        if self.config_data.get("Categorias"):
            self.selecionar_categoria_site(0)

    def refresh_site_categories(self):
        for widget in self.site_categories_frame.winfo_children():
            widget.destroy()

        for indice, item in enumerate(self.config_data.get("Categorias", [])):
            ativo = indice == self.selected_site_category_index
            button = ctk.CTkButton(
                self.site_categories_frame,
                text=f"{item['Categoria']} ({len(item.get('Subcategorias', []))} sub)",
                anchor="w",
                command=lambda idx=indice: self.selecionar_categoria_site(idx),
                fg_color="#1f6aa5" if ativo else "#2b2b2b",
                hover_color="#1a517b" if ativo else "#3a3a3a",
                height=34,
            )
            button.pack(fill="x", padx=6, pady=4)

    def selecionar_categoria_site(self, indice):
        self.selected_site_category_index = indice
        categoria = self.config_data["Categorias"][indice]
        self.site_category_name_entry.delete(0, "end")
        self.site_category_name_entry.insert(0, categoria.get("Categoria", ""))
        self.site_subcategories_box.delete("1.0", "end")
        self.site_subcategories_box.insert(
            "1.0", "\n".join(categoria.get("Subcategorias", []))
        )
        self.site_status_var.set(f"Editando categoria: {categoria.get('Categoria', '')}")
        self.refresh_site_categories()

    def nova_categoria_site(self):
        self.selected_site_category_index = None
        self.site_category_name_entry.delete(0, "end")
        self.site_subcategories_box.delete("1.0", "end")
        self.site_status_var.set("Criando uma nova categoria.")
        self.refresh_site_categories()

    def salvar_categoria_site(self):
        nome = self.site_category_name_entry.get().strip()
        if not nome:
            self.site_status_var.set("Informe um nome para a categoria antes de salvar.")
            return

        subcategorias = []
        for linha in self.site_subcategories_box.get("1.0", "end").splitlines():
            linha = linha.strip()
            if not linha:
                continue
            partes = [parte.strip() for parte in linha.split(",") if parte.strip()]
            subcategorias.extend(partes if partes else [linha])

        item = {"Categoria": nome, "Subcategorias": subcategorias}
        if self.selected_site_category_index is None:
            self.config_data["Categorias"].append(item)
            self.selected_site_category_index = len(self.config_data["Categorias"]) - 1
        else:
            self.config_data["Categorias"][self.selected_site_category_index] = item

        self.refresh_site_categories()
        self.site_status_var.set(f"Categoria salva: {nome}")
        self.refresh_category_menus()

    def remover_categoria_site(self):
        if self.selected_site_category_index is None:
            self.site_status_var.set("Selecione uma categoria para remover.")
            return

        removida = self.config_data["Categorias"].pop(self.selected_site_category_index)
        self.selected_site_category_index = None
        self.site_category_name_entry.delete(0, "end")
        self.site_subcategories_box.delete("1.0", "end")
        self.refresh_site_categories()
        self.site_status_var.set(f"Categoria removida: {removida['Categoria']}")
        self.refresh_category_menus()

    def salvar_config_site(self):
        self.config_data["Nome"] = self.site_name_entry.get().strip() or DEFAULT_CONFIG["Nome"]
        self.config_data["Icone"] = self.site_icon_entry.get().strip() or DEFAULT_CONFIG["Icone"]
        self.config_data["Escola"] = self.site_school_entry.get().strip() or DEFAULT_CONFIG["Escola"]
        self.config_data["Descricao"] = self.site_description_box.get("1.0", "end").strip()
        self.config_data["HeroTitulo"] = self.site_hero_title_entry.get().strip()
        self.config_data["HeroResumo"] = self.site_hero_summary_box.get("1.0", "end").strip()
        self.config_data["Rodape"] = self.site_footer_entry.get().strip()
        self.config_data = normalizar_config(self.config_data)
        salvar_config(self.config_data)
        self.header_title.configure(text=f"{self.config_data['Nome']} - painel de administracao")
        self.title(f"{self.config_data['Nome']} - Manager")
        self.refresh_site_categories()
        self.refresh_category_menus()
        self.site_status_var.set("config.json salvo com sucesso.")

    def refresh_category_menus(self):
        categorias = self.categorias_disponiveis_para_menu()
        self.news_category_menu.configure(values=categorias)
        categoria_atual = self.news_category_var.get()
        if categoria_atual not in categorias:
            self.news_category_var.set(categorias[0] if categorias else "")
        self.atualizar_menu_subcategoria(self.news_category_var.get(), preserve=False)

    def atualizar_menu_subcategoria(self, categoria, preserve=True):
        atual = self.news_subcategory_var.get()
        subcategorias = ["Sem subcategoria"] + subcategorias_da_categoria(self.config_data, categoria)
        self.news_subcategory_menu.configure(values=subcategorias)
        if preserve and atual in subcategorias:
            self.news_subcategory_var.set(atual)
        else:
            self.news_subcategory_var.set("Sem subcategoria")

    def on_categoria_change(self, categoria):
        self.atualizar_menu_subcategoria(categoria, preserve=False)

    def atualizar_listas_noticias(self):
        noticias = sincronizar_noticias()
        for widget in self.news_list_frame.winfo_children():
            widget.destroy()

        for item in noticias:
            ativo = item["slug"] == self.selected_news_slug
            texto = f"{item['titulo']}\n{item['categoria'] or 'Sem categoria'}"
            button = ctk.CTkButton(
                self.news_list_frame,
                text=texto,
                anchor="w",
                command=lambda meta=item: self.carregar_noticia_na_interface(meta),
                fg_color="#1f6aa5" if ativo else "#2b2b2b",
                hover_color="#1a517b" if ativo else "#3a3a3a",
                height=52,
            )
            button.pack(fill="x", padx=6, pady=4)

    def preparar_nova_noticia(self):
        self.current_news_path = None
        self.current_news = None
        self.current_block_index = None
        self.selected_news_slug = None

        self.news_title_entry.delete(0, "end")
        self.news_summary_box.delete("1.0", "end")
        self.news_date_entry.delete(0, "end")
        self.news_date_entry.insert(0, hoje_iso())
        categorias = self.categorias_disponiveis_para_menu()
        self.news_category_var.set(categorias[0] if categorias else "")
        self.atualizar_menu_subcategoria(self.news_category_var.get(), preserve=False)
        self.news_cover_entry.delete(0, "end")
        self.block_type_var.set("texto")
        self.block_editor.delete("1.0", "end")
        self.news_status_var.set("Pronto para criar uma nova noticia.")
        self.block_status_var.set("Escreva um bloco novo ou selecione uma materia existente.")
        self.refresh_block_list()
        self.atualizar_preview()
        self.atualizar_listas_noticias()

    def garantir_noticia_corrente(self):
        if self.current_news and self.current_news_path:
            return True

        titulo = self.news_title_entry.get().strip()
        if not titulo:
            self.news_status_var.set("Informe um titulo antes de criar a noticia.")
            return False

        pasta = BASE_DIR / slugify(titulo)
        preparar_pasta_noticia(pasta)
        self.current_news_path = pasta
        self.current_news = criar_estrutura_padrao(titulo)
        self.current_news["resumo"] = self.news_summary_box.get("1.0", "end").strip()
        self.current_news["data"] = self.news_date_entry.get().strip() or hoje_iso()
        self.current_news["categoria"] = self.news_category_var.get().strip()
        self.current_news["subcategoria"] = self.subcategoria_atual_limpa()
        self.current_news["imagemCapa"] = self.news_cover_entry.get().strip()
        self.salvar_noticia_corrente()
        return True

    def subcategoria_atual_limpa(self):
        valor = self.news_subcategory_var.get().strip()
        return "" if valor == "Sem subcategoria" else valor

    def carregar_noticia_na_interface(self, item):
        noticia_path, estrutura = carregar_noticia_existente(item)
        if not noticia_path or not estrutura:
            self.news_status_var.set("Nao foi possivel carregar esta noticia.")
            return

        self.current_news_path = noticia_path
        self.current_news = estrutura
        self.current_block_index = None
        self.selected_news_slug = item["slug"]

        self.news_title_entry.delete(0, "end")
        self.news_title_entry.insert(0, estrutura.get("titulo", ""))

        self.news_summary_box.delete("1.0", "end")
        self.news_summary_box.insert("1.0", estrutura.get("resumo", ""))

        self.news_date_entry.delete(0, "end")
        self.news_date_entry.insert(0, estrutura.get("data", hoje_iso()))

        categoria = estrutura.get("categoria", "")
        categorias = self.categorias_disponiveis_para_menu()
        if categoria and categoria not in categorias:
            categorias = categorias + [categoria]
            self.news_category_menu.configure(values=categorias)
        self.news_category_var.set(categoria or (categorias[0] if categorias else ""))
        self.atualizar_menu_subcategoria(self.news_category_var.get(), preserve=False)

        subcategoria = estrutura.get("subcategoria", "")
        if subcategoria and subcategoria not in self.news_subcategory_menu.cget("values"):
            novos = list(self.news_subcategory_menu.cget("values")) + [subcategoria]
            self.news_subcategory_menu.configure(values=novos)
        self.news_subcategory_var.set(subcategoria or "Sem subcategoria")

        self.news_cover_entry.delete(0, "end")
        self.news_cover_entry.insert(0, estrutura.get("imagemCapa", ""))

        self.block_type_var.set("texto")
        self.block_editor.delete("1.0", "end")

        self.news_status_var.set(
            f"Editando: {estrutura.get('titulo', '')} ({caminho_relativo(noticia_path)})"
        )
        self.block_status_var.set("Selecione um bloco para editar ou adicione um novo.")
        self.refresh_block_list()
        self.atualizar_preview()
        self.atualizar_listas_noticias()

    def salvar_noticia_corrente(self):
        if not self.current_news or not self.current_news_path:
            return
        salvar_estrutura_em_disco(self.current_news_path, self.current_news)
        self.selected_news_slug = slugify(self.current_news_path.name)
        sincronizar_noticias()
        self.atualizar_listas_noticias()

    def salvar_metadados_noticia(self):
        if not self.garantir_noticia_corrente():
            return

        self.current_news["titulo"] = self.news_title_entry.get().strip()
        self.current_news["resumo"] = self.news_summary_box.get("1.0", "end").strip()
        self.current_news["data"] = self.news_date_entry.get().strip() or hoje_iso()
        self.current_news["categoria"] = self.news_category_var.get().strip()
        self.current_news["subcategoria"] = self.subcategoria_atual_limpa()
        self.current_news["imagemCapa"] = self.news_cover_entry.get().strip()
        self.salvar_noticia_corrente()
        self.news_status_var.set(
            f"Metadados salvos para: {self.current_news.get('titulo', '')}"
        )
        self.atualizar_preview()

    def selecionar_capa_noticia(self):
        if not self.garantir_noticia_corrente():
            return

        caminho = filedialog.askopenfilename()
        if not caminho:
            return

        origem = Path(caminho)
        destino = self.current_news_path / "imagens" / origem.name
        shutil.copy(origem, destino)
        relativo = f"imagens/{origem.name}"
        self.news_cover_entry.delete(0, "end")
        self.news_cover_entry.insert(0, relativo)
        self.current_news["imagemCapa"] = relativo
        self.salvar_noticia_corrente()
        self.atualizar_preview()

    def refresh_block_list(self):
        for widget in self.block_list_frame.winfo_children():
            widget.destroy()

        if not self.current_news:
            ctk.CTkLabel(
                self.block_list_frame,
                text="Nenhuma noticia carregada.",
                text_color="gray",
            ).pack(anchor="w", padx=10, pady=10)
            return

        conteudo = self.current_news.get("conteudo", [])
        if not conteudo:
            ctk.CTkLabel(
                self.block_list_frame,
                text="Ainda nao ha blocos nesta noticia.",
                text_color="gray",
            ).pack(anchor="w", padx=10, pady=10)
            return

        for indice, item in enumerate(conteudo):
            ativo = indice == self.current_block_index
            button = ctk.CTkButton(
                self.block_list_frame,
                text=descricao_bloco(item, indice),
                anchor="w",
                command=lambda idx=indice: self.selecionar_bloco(idx),
                fg_color="#1f6aa5" if ativo else "#2b2b2b",
                hover_color="#1a517b" if ativo else "#3a3a3a",
                height=34,
            )
            button.pack(fill="x", padx=6, pady=4)

    def selecionar_bloco(self, indice):
        if not self.current_news:
            return
        item = self.current_news["conteudo"][indice]
        self.current_block_index = indice
        self.block_type_var.set(item.get("tipo", "texto"))
        self.block_editor.delete("1.0", "end")
        self.block_editor.insert("1.0", ler_conteudo_item(self.current_news_path, item))
        self.block_status_var.set(
            f"Editando o bloco {indice + 1}: {item.get('tipo', 'desconhecido')}."
        )
        self.refresh_block_list()

    def selecionar_arquivo_bloco(self):
        if not self.garantir_noticia_corrente():
            return

        caminho = filedialog.askopenfilename()
        if not caminho:
            return

        tipo = self.block_type_var.get()
        origem = Path(caminho)
        nome = origem.name

        if tipo == "imagem":
            destino = self.current_news_path / "imagens" / nome
            relativo = f"imagens/{nome}"
        elif tipo in {"video", "audio"}:
            destino = self.current_news_path / "midia" / nome
            relativo = f"midia/{nome}"
        else:
            destino = self.current_news_path / "documentos" / nome
            relativo = f"documentos/{nome}"

        shutil.copy(origem, destino)
        self.block_editor.delete("1.0", "end")
        self.block_editor.insert("1.0", relativo)

    def adicionar_bloco(self):
        if not self.garantir_noticia_corrente():
            return

        tipo = self.block_type_var.get()
        valor = self.block_editor.get("1.0", "end").strip()
        if not valor:
            self.block_status_var.set("Informe o conteudo do bloco antes de adicionar.")
            return

        if tipo == "texto":
            numero = sum(1 for item in self.current_news["conteudo"] if item["tipo"] == "texto") + 1
            arquivo = f"paragrafos/p{numero}.txt"
            (self.current_news_path / arquivo).write_text(valor, encoding="utf-8")
            self.current_news["conteudo"].append({"tipo": "texto", "arquivo": arquivo})
        elif tipo == "titulo":
            self.current_news["conteudo"].append({"tipo": "titulo", "texto": valor})
        elif tipo == "imagem":
            self.current_news["conteudo"].append(
                {"tipo": "imagem", "arquivo": valor, "legenda": "Imagem"}
            )
            if not self.current_news.get("imagemCapa"):
                self.current_news["imagemCapa"] = valor
                self.news_cover_entry.delete(0, "end")
                self.news_cover_entry.insert(0, valor)
        elif tipo == "video":
            self.current_news["conteudo"].append({"tipo": "video", "arquivo": valor})
        elif tipo == "audio":
            self.current_news["conteudo"].append({"tipo": "audio", "arquivo": valor})
        elif tipo == "documento":
            self.current_news["conteudo"].append(
                {"tipo": "documento", "arquivo": valor, "legenda": "Abrir documento"}
            )

        self.current_block_index = None
        self.block_editor.delete("1.0", "end")
        self.block_type_var.set("texto")
        self.salvar_noticia_corrente()
        self.block_status_var.set("Novo bloco adicionado com sucesso.")
        self.refresh_block_list()
        self.atualizar_preview()

    def salvar_bloco_atual(self):
        if self.current_block_index is None or not self.current_news:
            self.block_status_var.set("Selecione um bloco antes de salvar.")
            return

        valor = self.block_editor.get("1.0", "end").strip()
        if not valor:
            self.block_status_var.set("O bloco nao pode ficar vazio.")
            return

        item = self.current_news["conteudo"][self.current_block_index]
        salvar_conteudo_item(self.current_news_path, item, valor)
        self.salvar_noticia_corrente()
        self.block_status_var.set(
            f"Bloco {self.current_block_index + 1} salvo com sucesso."
        )
        self.refresh_block_list()
        self.atualizar_preview()

    def remover_bloco_atual(self):
        if self.current_block_index is None or not self.current_news:
            self.block_status_var.set("Selecione um bloco antes de remover.")
            return

        item = self.current_news["conteudo"].pop(self.current_block_index)
        if item.get("tipo") == "texto":
            caminho = self.current_news_path / item.get("arquivo", "")
            if caminho.exists():
                caminho.unlink()

        if item.get("tipo") == "imagem" and self.current_news.get("imagemCapa") == item.get("arquivo"):
            self.current_news["imagemCapa"] = ""
            self.news_cover_entry.delete(0, "end")

        self.current_block_index = None
        self.block_editor.delete("1.0", "end")
        self.block_type_var.set("texto")
        self.salvar_noticia_corrente()
        self.block_status_var.set("Bloco removido com sucesso.")
        self.refresh_block_list()
        self.atualizar_preview()

    def excluir_noticia_atual(self):
        if not self.current_news_path:
            self.news_status_var.set("Nenhuma noticia carregada para exclusao.")
            return

        alvo = self.current_news_path
        if alvo.exists():
            shutil.rmtree(alvo)

        self.news_status_var.set(f"Noticia excluida: {alvo.name}")
        self.preparar_nova_noticia()
        sincronizar_noticias()
        self.atualizar_listas_noticias()

    def atualizar_preview(self):
        for widget in self.preview_box.winfo_children():
            widget.destroy()

        if not self.current_news:
            ctk.CTkLabel(
                self.preview_box,
                text="Nenhuma noticia carregada para pre-visualizacao.",
                text_color="gray",
            ).pack(anchor="w", padx=12, pady=12)
            return

        ctk.CTkLabel(
            self.preview_box,
            text=self.current_news.get("titulo", "Sem titulo"),
            font=("Arial", 30, "bold"),
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(10, 5))

        meta = (
            f"{self.current_news.get('categoria', 'Sem categoria')}"
            + (
                f" ({self.current_news.get('subcategoria')})"
                if self.current_news.get("subcategoria")
                else ""
            )
            + f" - {self.current_news.get('data', '')}"
        )
        ctk.CTkLabel(
            self.preview_box,
            text=meta,
            font=("Arial", 14),
            text_color="gray",
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            self.preview_box,
            text=self.current_news.get("resumo", ""),
            font=("Arial", 16),
            text_color="gray",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        capa = self.current_news.get("imagemCapa", "")
        if capa:
            path = self.current_news_path / capa
            if path.exists():
                try:
                    img = Image.open(path)
                    img.thumbnail((760, 420))
                    ctk_img = ctk.CTkImage(
                        light_image=img,
                        dark_image=img,
                        size=img.size,
                    )
                    label = ctk.CTkLabel(self.preview_box, image=ctk_img, text="")
                    label.image = ctk_img
                    label.pack(pady=(0, 14))
                except OSError:
                    pass

        for item in self.current_news.get("conteudo", []):
            tipo = item.get("tipo")
            if tipo == "titulo":
                ctk.CTkLabel(
                    self.preview_box,
                    text=item.get("texto", ""),
                    font=("Arial", 24, "bold"),
                ).pack(anchor="w", pady=(16, 8))
            elif tipo == "texto":
                texto = ler_conteudo_item(self.current_news_path, item)
                ctk.CTkLabel(
                    self.preview_box,
                    text=texto,
                    wraplength=780,
                    justify="left",
                    font=("Arial", 17),
                ).pack(anchor="w", pady=8)
            else:
                ctk.CTkLabel(
                    self.preview_box,
                    text=f"{tipo.upper()}: {item.get('arquivo', '')}",
                    font=("Arial", 15),
                    text_color="gray",
                ).pack(anchor="w", pady=8)


if __name__ == "__main__":
    BASE_DIR.mkdir(exist_ok=True)
    salvar_config(carregar_config())
    sincronizar_noticias()
    App().mainloop()
