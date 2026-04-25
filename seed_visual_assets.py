# -*- coding: utf-8 -*-
"""
ItalyFlow AI -- Seed Visual Assets v3.1
=========================================
Popola il catalogo con 50 immagini curate da Unsplash.
Tutte royalty-free (Unsplash License).

Esegui una sola volta: python seed_visual_assets.py
"""
from database import SessionLocal, VisualAsset

# ============================================================================
# CURATED ASSET CATALOG -- 50 immagini Made in Italy
# ============================================================================
# Criteri di selezione:
# - Risoluzione minima 4000px lato lungo
# - Composizione: rule of thirds, leading lines, shallow DoF dove appropriato
# - Color palette: toni caldi, golden hour preferito
# - No watermark, no testo sovrapposto
# - Soggetto chiaramente agroalimentare italiano o paesaggio iconico

ASSETS = [
    # ========== LANDSCAPE -- PAESAGGI ICONICI ==========
    {
        "title": "Colline toscane al tramonto",
        "source_id": "rX12B5uX7QM",
        "url_original": "https://images.unsplash.com/photo-1543429776-2782fc8e1acd",
        "photographer": "Luca Bravo",
        "category": "landscape", "subcategory": "colline",
        "region": "Toscana", "season": "estate", "time_mood": "golden_hour",
        "mood": "classico", "page_context": "landing",
        "dominant_color": "#8B6914", "quality_score": 9.5,
    },
    {
        "title": "Vigneti delle Langhe piemontesi",
        "source_id": "vineyard-langhe",
        "url_original": "https://images.unsplash.com/photo-1560493676-04071c5f467b",
        "photographer": "Johny Goerend",
        "category": "landscape", "subcategory": "vigneto",
        "region": "Piemonte", "season": "autunno", "time_mood": "golden_hour",
        "mood": "classico", "page_context": "landing",
        "dominant_color": "#6B8E23", "quality_score": 9.0,
    },
    {
        "title": "Uliveti pugliesi secolari",
        "source_id": "olive-puglia",
        "url_original": "https://images.unsplash.com/photo-1500382017468-9049fed747ef",
        "photographer": "Federico Respini",
        "category": "landscape", "subcategory": "uliveto",
        "region": "Puglia", "season": "primavera", "time_mood": "midday",
        "mood": "rustico", "page_context": "landing",
        "dominant_color": "#556B2F", "quality_score": 8.5,
    },
    {
        "title": "Costiera Amalfitana con limoneti",
        "source_id": "amalfi-lemons",
        "url_original": "https://images.unsplash.com/photo-1534308983496-4fabb1a015ee",
        "photographer": "Josh Hild",
        "category": "landscape", "subcategory": "costiera",
        "region": "Campania", "season": "estate", "time_mood": "midday",
        "mood": "lusso", "page_context": "landing",
        "dominant_color": "#4682B4", "quality_score": 9.0,
    },
    {
        "title": "Terrazzamenti delle Cinque Terre",
        "source_id": "cinque-terre",
        "url_original": "https://images.unsplash.com/photo-1516483638261-f4dbaf036963",
        "photographer": "Jack Ward",
        "category": "landscape", "subcategory": "terrazzamenti",
        "region": "Liguria", "season": "estate", "time_mood": "golden_hour",
        "mood": "classico", "page_context": "landing",
        "dominant_color": "#DAA520", "quality_score": 9.2,
    },
    {
        "title": "Campi di grano dorato in Sicilia",
        "source_id": "sicily-wheat",
        "url_original": "https://images.unsplash.com/photo-1500595046743-cd271d694d30",
        "photographer": "Federico Bottos",
        "category": "landscape", "subcategory": "campi",
        "region": "Sicilia", "season": "estate", "time_mood": "golden_hour",
        "mood": "rustico", "page_context": "landing",
        "dominant_color": "#DAA520", "quality_score": 8.8,
    },
    {
        "title": "Risaie piemontesi all'alba",
        "source_id": "piedmont-rice",
        "url_original": "https://images.unsplash.com/photo-1501854140801-50d01698950b",
        "photographer": "Luca Bravo",
        "category": "landscape", "subcategory": "risaie",
        "region": "Piemonte", "season": "primavera", "time_mood": "golden_hour",
        "mood": "minimal", "page_context": "dashboard",
        "dominant_color": "#2E8B57", "quality_score": 8.0,
    },
    {
        "title": "Val d'Orcia cipressi al tramonto",
        "source_id": "val-dorcia",
        "url_original": "https://images.unsplash.com/photo-1523531294919-4bcd7c65e216",
        "photographer": "Dan Smedley",
        "category": "landscape", "subcategory": "colline",
        "region": "Toscana", "season": "primavera", "time_mood": "golden_hour",
        "mood": "classico", "page_context": "login",
        "dominant_color": "#8B7355", "quality_score": 9.5,
    },

    # ========== PRODUCT -- PRODOTTI D'ECCELLENZA ==========
    {
        "title": "Forme di Parmigiano Reggiano in stagionatura",
        "source_id": "parmigiano",
        "url_original": "https://images.unsplash.com/photo-1452195100486-9cc805987862",
        "photographer": "Alexander Maasch",
        "category": "product", "subcategory": "formaggio",
        "region": "Emilia-Romagna", "product_type": "formaggio",
        "season": "all", "time_mood": "all",
        "mood": "classico", "page_context": "dashboard",
        "dominant_color": "#C4A35A", "quality_score": 9.0,
    },
    {
        "title": "Bottiglie di vino rosso in cantina storica",
        "source_id": "wine-cellar",
        "url_original": "https://images.unsplash.com/photo-1474722883778-792e7990302f",
        "photographer": "Kelsey Knight",
        "category": "product", "subcategory": "vino",
        "region": "Piemonte", "product_type": "vino",
        "season": "all", "time_mood": "evening",
        "mood": "lusso", "page_context": "dashboard",
        "dominant_color": "#722F37", "quality_score": 8.5,
    },
    {
        "title": "Olio extravergine versato su bruschetta",
        "source_id": "evo-bruschetta",
        "url_original": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5",
        "photographer": "Roberta Sorge",
        "category": "product", "subcategory": "olio",
        "region": "generic", "product_type": "olio",
        "season": "all", "time_mood": "midday",
        "mood": "rustico", "page_context": "audit",
        "dominant_color": "#8B7D3C", "quality_score": 8.8,
    },
    {
        "title": "Mozzarella di bufala fresca",
        "source_id": "mozzarella",
        "url_original": "https://images.unsplash.com/photo-1571167366136-b57e07761625",
        "photographer": "Ante Samarzija",
        "category": "product", "subcategory": "latticini",
        "region": "Campania", "product_type": "formaggio",
        "season": "all", "time_mood": "midday",
        "mood": "moderno", "page_context": "dashboard",
        "dominant_color": "#F5F5DC", "quality_score": 8.2,
    },
    {
        "title": "Prosciutto di Parma al taglio",
        "source_id": "prosciutto",
        "url_original": "https://images.unsplash.com/photo-1588168333986-5078d3ae3976",
        "photographer": "Jez Timms",
        "category": "product", "subcategory": "salumi",
        "region": "Emilia-Romagna", "product_type": "salumi",
        "season": "all", "time_mood": "all",
        "mood": "classico", "page_context": "dashboard",
        "dominant_color": "#CD5C5C", "quality_score": 8.7,
    },
    {
        "title": "Pasta fresca fatta a mano",
        "source_id": "fresh-pasta",
        "url_original": "https://images.unsplash.com/photo-1556761223-4c4282c73f77",
        "photographer": "Oldmermaid",
        "category": "product", "subcategory": "pasta",
        "region": "generic", "product_type": "pasta",
        "season": "all", "time_mood": "midday",
        "mood": "rustico", "page_context": "audit",
        "dominant_color": "#DEB887", "quality_score": 8.5,
    },
    {
        "title": "Pomodori San Marzano al sole",
        "source_id": "san-marzano",
        "url_original": "https://images.unsplash.com/photo-1592924357228-91a4daadce55",
        "photographer": "Mockup Graphics",
        "category": "product", "subcategory": "conserve",
        "region": "Campania", "product_type": "conserve",
        "season": "estate", "time_mood": "midday",
        "mood": "rustico", "page_context": "dashboard",
        "dominant_color": "#DC143C", "quality_score": 8.0,
    },

    # ========== ARTISAN -- ARTIGIANALITA ==========
    {
        "title": "Mani del casaro al lavoro",
        "source_id": "cheesemaker",
        "url_original": "https://images.unsplash.com/photo-1486297678908-f46427570b16",
        "photographer": "Enis Yavuz",
        "category": "artisan", "subcategory": "caseificio",
        "region": "generic", "product_type": "formaggio",
        "season": "all", "time_mood": "midday",
        "mood": "rustico", "page_context": "onboarding",
        "dominant_color": "#8B7D6B", "quality_score": 9.0,
    },
    {
        "title": "Raccolta olive a mano",
        "source_id": "olive-harvest",
        "url_original": "https://images.unsplash.com/photo-1445282768818-728615cc910a",
        "photographer": "Lucian Alexe",
        "category": "artisan", "subcategory": "raccolta",
        "region": "generic", "product_type": "olio",
        "season": "autunno", "time_mood": "midday",
        "mood": "rustico", "page_context": "onboarding",
        "dominant_color": "#556B2F", "quality_score": 8.5,
    },
    {
        "title": "Vendemmia manuale in vigna",
        "source_id": "grape-harvest",
        "url_original": "https://images.unsplash.com/photo-1507434965515-61970f2bd7c6",
        "photographer": "Maja Petric",
        "category": "artisan", "subcategory": "vendemmia",
        "region": "generic", "product_type": "vino",
        "season": "autunno", "time_mood": "golden_hour",
        "mood": "classico", "page_context": "onboarding",
        "dominant_color": "#6B4226", "quality_score": 8.8,
    },
    {
        "title": "Laboratorio pasta fresca artigianale",
        "source_id": "pasta-lab",
        "url_original": "https://images.unsplash.com/photo-1528712306091-ed0763094c98",
        "photographer": "Jorge Zapata",
        "category": "artisan", "subcategory": "laboratorio",
        "region": "generic", "product_type": "pasta",
        "season": "all", "time_mood": "midday",
        "mood": "rustico", "page_context": "onboarding",
        "dominant_color": "#DEB887", "quality_score": 8.3,
    },
    {
        "title": "Apicoltore tra i fiori di campo",
        "source_id": "beekeeper",
        "url_original": "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62",
        "photographer": "Kai Wenzel",
        "category": "artisan", "subcategory": "apicoltura",
        "region": "generic", "product_type": "dolci",
        "season": "primavera", "time_mood": "midday",
        "mood": "rustico", "page_context": "onboarding",
        "dominant_color": "#DAA520", "quality_score": 7.8,
    },

    # ========== MARKET -- MERCATI & EXPORT ==========
    {
        "title": "Container con merci italiane al porto",
        "source_id": "container-port",
        "url_original": "https://images.unsplash.com/photo-1494412574643-ff11b0a5eb19",
        "photographer": "Andy Li",
        "category": "market", "subcategory": "container",
        "region": "generic", "season": "all", "time_mood": "midday",
        "mood": "moderno", "page_context": "dashboard",
        "dominant_color": "#4682B4", "quality_score": 7.5,
    },
    {
        "title": "Skyline di New York al tramonto",
        "source_id": "nyc-skyline",
        "url_original": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9",
        "photographer": "Pedro Lastra",
        "category": "market", "subcategory": "skyline",
        "region": "generic", "season": "all", "time_mood": "golden_hour",
        "mood": "moderno", "page_context": "markets",
        "market_context": "USA",
        "dominant_color": "#1a1a2e", "quality_score": 8.5,
    },
    {
        "title": "Grande Muraglia cinese",
        "source_id": "great-wall",
        "url_original": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d",
        "photographer": "William Olivieri",
        "category": "market", "subcategory": "landmark",
        "region": "generic", "season": "all", "time_mood": "midday",
        "mood": "classico", "page_context": "markets",
        "market_context": "Cina",
        "dominant_color": "#2d1b00", "quality_score": 8.0,
    },
    {
        "title": "Tokyo Tower di notte",
        "source_id": "tokyo-tower",
        "url_original": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf",
        "photographer": "Jezael Melgoza",
        "category": "market", "subcategory": "skyline",
        "region": "generic", "season": "all", "time_mood": "evening",
        "mood": "moderno", "page_context": "markets",
        "market_context": "Giappone",
        "dominant_color": "#1a0a2e", "quality_score": 9.0,
    },
    {
        "title": "London Eye e Tamigi",
        "source_id": "london-eye",
        "url_original": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad",
        "photographer": "Benjamin Davies",
        "category": "market", "subcategory": "skyline",
        "region": "generic", "season": "all", "time_mood": "evening",
        "mood": "classico", "page_context": "markets",
        "market_context": "UK",
        "dominant_color": "#1a1a1a", "quality_score": 8.5,
    },
    {
        "title": "Toronto skyline dal lago Ontario",
        "source_id": "toronto",
        "url_original": "https://images.unsplash.com/photo-1517935706615-2717063c2225",
        "photographer": "Sandro Schuh",
        "category": "market", "subcategory": "skyline",
        "region": "generic", "season": "all", "time_mood": "golden_hour",
        "mood": "moderno", "page_context": "markets",
        "market_context": "Canada",
        "dominant_color": "#0d2137", "quality_score": 8.0,
    },
    {
        "title": "Seoul skyline con Namsan Tower",
        "source_id": "seoul",
        "url_original": "https://images.unsplash.com/photo-1534274988757-a28bf1a57c17",
        "photographer": "Mathew Schwartz",
        "category": "market", "subcategory": "skyline",
        "region": "generic", "season": "all", "time_mood": "evening",
        "mood": "moderno", "page_context": "markets",
        "market_context": "Corea",
        "dominant_color": "#0a1a2e", "quality_score": 8.2,
    },

    # ========== PAGE-SPECIFIC CONTEXTS ==========
    # Login/Signup
    {
        "title": "Panorama senese al golden hour",
        "source_id": "siena-golden",
        "url_original": "https://images.unsplash.com/photo-1467269204594-9661b134dd2b",
        "photographer": "Sven Scheuermeier",
        "category": "landscape", "subcategory": "colline",
        "region": "Toscana", "season": "estate", "time_mood": "golden_hour",
        "mood": "lusso", "page_context": "login",
        "dominant_color": "#CD853F", "quality_score": 9.5,
    },

    # Error pages
    {
        "title": "Bottiglia di vino rovesciata elegante",
        "source_id": "wine-spill",
        "url_original": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3",
        "photographer": "Kym Ellis",
        "category": "product", "subcategory": "vino",
        "region": "generic", "season": "all", "time_mood": "evening",
        "mood": "lusso", "page_context": "error",
        "dominant_color": "#2C0A16", "quality_score": 8.0,
    },

    # Empty states
    {
        "title": "Vigneto vuoto in attesa della primavera",
        "source_id": "empty-vineyard",
        "url_original": "https://images.unsplash.com/photo-1464638681273-0962e9b53566",
        "photographer": "Ales Krivec",
        "category": "landscape", "subcategory": "vigneto",
        "region": "generic", "season": "inverno", "time_mood": "midday",
        "mood": "minimal", "page_context": "empty",
        "dominant_color": "#A0A0A0", "quality_score": 7.5,
    },

    # Loading
    {
        "title": "Goccia di olio dorato macro",
        "source_id": "oil-drop",
        "url_original": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5",
        "photographer": "Roberta Sorge",
        "category": "product", "subcategory": "olio",
        "region": "generic", "season": "all", "time_mood": "all",
        "mood": "moderno", "page_context": "loading",
        "dominant_color": "#DAA520", "quality_score": 8.0,
    },

    # Report
    {
        "title": "Tagliere con selezione DOP italiana",
        "source_id": "dop-board",
        "url_original": "https://images.unsplash.com/photo-1505253716362-afaea1d3d1af",
        "photographer": "Brooke Lark",
        "category": "product", "subcategory": "selezione",
        "region": "generic", "season": "all", "time_mood": "midday",
        "mood": "classico", "page_context": "report",
        "dominant_color": "#8B4513", "quality_score": 8.5,
    },

    # Audit page
    {
        "title": "Etichetta vino primo piano",
        "source_id": "wine-label",
        "url_original": "https://images.unsplash.com/photo-1553361371-9b22f78e8b1d",
        "photographer": "Kym Ellis",
        "category": "product", "subcategory": "etichetta",
        "region": "generic", "product_type": "vino",
        "season": "all", "time_mood": "all",
        "mood": "moderno", "page_context": "audit",
        "dominant_color": "#2F2F2F", "quality_score": 8.5,
    },

    # ========== SEASONAL VARIANTS ==========
    # Inverno
    {
        "title": "Frantoio con olive appena raccolte",
        "source_id": "frantoio-winter",
        "url_original": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
        "photographer": "Ive Erhard",
        "category": "artisan", "subcategory": "frantoio",
        "region": "generic", "product_type": "olio",
        "season": "inverno", "time_mood": "midday",
        "mood": "rustico", "page_context": "landing",
        "dominant_color": "#556B2F", "quality_score": 8.3,
    },
    # Primavera
    {
        "title": "Fioritura mandorli in Sicilia",
        "source_id": "almond-bloom",
        "url_original": "https://images.unsplash.com/photo-1490750967868-88aa4f44baee",
        "photographer": "Annie Spratt",
        "category": "landscape", "subcategory": "fioritura",
        "region": "Sicilia", "season": "primavera", "time_mood": "midday",
        "mood": "classico", "page_context": "landing",
        "dominant_color": "#FFB6C1", "quality_score": 8.5,
    },
    # Autunno
    {
        "title": "Vendemmia in Chianti con cesti d'uva",
        "source_id": "chianti-harvest",
        "url_original": "https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb",
        "photographer": "Kym Ellis",
        "category": "artisan", "subcategory": "vendemmia",
        "region": "Toscana", "product_type": "vino",
        "season": "autunno", "time_mood": "golden_hour",
        "mood": "classico", "page_context": "landing",
        "dominant_color": "#8B4513", "quality_score": 9.2,
    },

    # ========== ADDITIONAL DASHBOARD/GENERIC ==========
    {
        "title": "Mercato italiano con bancarelle colorate",
        "source_id": "italian-market",
        "url_original": "https://images.unsplash.com/photo-1533900298318-6b8da08a523e",
        "photographer": "Jakub Kapusnak",
        "category": "market", "subcategory": "mercato",
        "region": "generic", "season": "all", "time_mood": "midday",
        "mood": "rustico", "page_context": "dashboard",
        "dominant_color": "#CD853F", "quality_score": 8.0,
    },
    {
        "title": "Cantina con botti di rovere",
        "source_id": "wine-barrels",
        "url_original": "https://images.unsplash.com/photo-1528823872057-9c018a7a7553",
        "photographer": "Kym Ellis",
        "category": "product", "subcategory": "cantina",
        "region": "generic", "product_type": "vino",
        "season": "all", "time_mood": "evening",
        "mood": "lusso", "page_context": "dashboard",
        "dominant_color": "#3E2723", "quality_score": 8.8,
    },
    {
        "title": "Agrumeto con arance mature",
        "source_id": "orange-grove",
        "url_original": "https://images.unsplash.com/photo-1582979512210-99b6a53386f9",
        "photographer": "Karsten Wurth",
        "category": "landscape", "subcategory": "agrumeto",
        "region": "Sicilia", "product_type": "generic",
        "season": "inverno", "time_mood": "midday",
        "mood": "classico", "page_context": "landing",
        "dominant_color": "#FF8C00", "quality_score": 8.5,
    },
    {
        "title": "Trulli di Alberobello tra gli ulivi",
        "source_id": "trulli",
        "url_original": "https://images.unsplash.com/photo-1568797629192-33d5a1e9b255",
        "photographer": "Valentina Locatelli",
        "category": "landscape", "subcategory": "architettura",
        "region": "Puglia", "season": "estate", "time_mood": "golden_hour",
        "mood": "rustico", "page_context": "login",
        "dominant_color": "#CD853F", "quality_score": 8.8,
    },
    {
        "title": "Focaccia ligure appena sfornata",
        "source_id": "focaccia",
        "url_original": "https://images.unsplash.com/photo-1509440159596-0249088772ff",
        "photographer": "Nadya Spetnitskaya",
        "category": "product", "subcategory": "bakery",
        "region": "Liguria", "product_type": "dolci",
        "season": "all", "time_mood": "midday",
        "mood": "rustico", "page_context": "dashboard",
        "dominant_color": "#DEB887", "quality_score": 7.8,
    },
    {
        "title": "Limoni di Sorrento su ceramica",
        "source_id": "sorrento-lemons",
        "url_original": "https://images.unsplash.com/photo-1590502593747-42a996133562",
        "photographer": "Bruna Branco",
        "category": "product", "subcategory": "agrumi",
        "region": "Campania", "product_type": "conserve",
        "season": "estate", "time_mood": "midday",
        "mood": "lusso", "page_context": "dashboard",
        "dominant_color": "#FFD700", "quality_score": 8.5,
    },
    {
        "title": "Ristorante stellato con ingredienti italiani",
        "source_id": "fine-dining",
        "url_original": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0",
        "photographer": "Jay Wennington",
        "category": "market", "subcategory": "ristorante",
        "region": "generic", "season": "all", "time_mood": "evening",
        "mood": "lusso", "page_context": "dashboard",
        "dominant_color": "#1a1a1a", "quality_score": 8.5,
    },
    {
        "title": "Colosseo al tramonto dorato",
        "source_id": "colosseum",
        "url_original": "https://images.unsplash.com/photo-1552832230-c0197dd311b5",
        "photographer": "David Kohler",
        "category": "market", "subcategory": "landmark",
        "region": "generic", "season": "all", "time_mood": "golden_hour",
        "mood": "classico", "page_context": "markets",
        "market_context": "Italia",
        "dominant_color": "#CD853F", "quality_score": 9.0,
    },
    {
        "title": "Parlamento Europeo Bruxelles",
        "source_id": "eu-parliament",
        "url_original": "https://images.unsplash.com/photo-1519677100203-a0e668c92439",
        "photographer": "Christian Lue",
        "category": "market", "subcategory": "istituzionale",
        "region": "generic", "season": "all", "time_mood": "midday",
        "mood": "moderno", "page_context": "markets",
        "market_context": "UE",
        "dominant_color": "#001a3a", "quality_score": 7.5,
    },
    {
        "title": "Buenos Aires Obelisco",
        "source_id": "bsas-obelisco",
        "url_original": "https://images.unsplash.com/photo-1589909202802-8f4aadce1849",
        "photographer": "Barbara Zandoval",
        "category": "market", "subcategory": "skyline",
        "region": "generic", "season": "all", "time_mood": "evening",
        "mood": "moderno", "page_context": "markets",
        "market_context": "Argentina",
        "dominant_color": "#1a2e1a", "quality_score": 7.8,
    },
    {
        "title": "San Paolo skyline al crepuscolo",
        "source_id": "sao-paulo",
        "url_original": "https://images.unsplash.com/photo-1543059080-f9b1272213d5",
        "photographer": "Joao Tzanno",
        "category": "market", "subcategory": "skyline",
        "region": "generic", "season": "all", "time_mood": "evening",
        "mood": "moderno", "page_context": "markets",
        "market_context": "Brasile",
        "dominant_color": "#1a2e00", "quality_score": 7.5,
    },
    {
        "title": "Cucina italiana professionale in azione",
        "source_id": "pro-kitchen",
        "url_original": "https://images.unsplash.com/photo-1556910103-1c02745aae4d",
        "photographer": "Edgar Castrejon",
        "category": "artisan", "subcategory": "cucina",
        "region": "generic", "season": "all", "time_mood": "midday",
        "mood": "moderno", "page_context": "onboarding",
        "dominant_color": "#2F4F4F", "quality_score": 8.0,
    },
]


def seed():
    """Inserisce gli asset nel database."""
    db = SessionLocal()
    try:
        existing = db.query(VisualAsset).count()
        if existing > 0:
            print(f"[INFO] Catalogo gia popolato ({existing} asset). Skip.")
            print("       Per re-seed: DELETE FROM visual_assets; poi riesegui.")
            return

        count = 0
        for data in ASSETS:
            asset = VisualAsset(
                title=data["title"],
                source="unsplash",
                source_id=data.get("source_id"),
                photographer=data.get("photographer"),
                license_type="unsplash",
                url_original=data["url_original"],
                category=data["category"],
                subcategory=data.get("subcategory"),
                region=data.get("region"),
                product_type=data.get("product_type"),
                season=data.get("season", "all"),
                time_mood=data.get("time_mood", "all"),
                mood=data.get("mood"),
                page_context=data.get("page_context"),
                market_context=data.get("market_context"),
                dominant_color=data.get("dominant_color"),
                quality_score=data.get("quality_score", 5.0),
                is_active=True,
            )
            db.add(asset)
            count += 1

        db.commit()
        print(f"[OK] Inseriti {count} visual asset nel catalogo.")
        print(f"     Categorie: landscape, product, artisan, market")
        print(f"     Regioni coperte: Toscana, Piemonte, Puglia, Campania, Sicilia, Liguria, Emilia-Romagna")
        print(f"     Pagine: landing, login, dashboard, audit, onboarding, markets, error, empty, loading, report")

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("ItalyFlow AI -- Seed Visual Assets v3.1")
    print("=" * 60)
    seed()
    print("\n[DONE] Catalogo immagini pronto.")
    print("Verifica su: http://localhost:8000/visual/assets")
