"""
Datos de shopify_fix_translations.py: traducciones EN/FR de los productos "Loncheado a Mano / a Máquina",
colecciones, menú, banda de confianza, FAQ y textos de ficha que no tienen equivalente reutilizable.

NO se traducen aquí los nombres/valores de opciones que el tema usa para decidir lógica
("Formato", "Pieza entera", "Deshuesado", "Corte a mano y envasado"…): el tema los muestra traducidos sin cambiarlos.
"""

# ── Productos por handle: {handle: {campo: {locale: texto}}} ──
def _hand_machine():
    # (handle sufijo, nombre EN, nombre FR, sello EN/FR, curación EN/FR meses, kind, frase de crianza EN/FR)
    marcas = {
        "jamon-bellota-100-iberico": dict(
            en_name="100% Ibérico Bellota Ham", fr_name="Jambon Bellota 100 % ibérique", pct="100",
            en_intro="100% Iberian acorn-fed ham with a black label", fr_intro="Jambon 100 % ibérique de bellota avec sceau noir",
            en_fat="Each slice shows the marbling of infiltrated fat characteristic of pure acorn-fed Iberian ham.",
            fr_fat="Chaque tranche présente le persillage de gras infiltré caractéristique de l'ibérique pur de bellota.",
            en_cur="more than <strong>36 months of curing</strong>", fr_cur="plus de <strong>36 mois d'affinage</strong>",
            en_extra="<li>100% Iberian acorn-fed pork</li>\n", fr_extra="<li>Porc 100 % ibérique de bellota</li>\n",
            en_meta="100% Ibérico Bellota", fr_meta="Bellota 100 % ibérique", months_en="36+", months_fr="+36",
        ),
        "jamon-bellota-50-iberico": dict(
            en_name="50% Ibérico Bellota Ham", fr_name="Jambon Bellota 50 % ibérique", pct="50",
            en_intro="50% Iberian acorn-fed ham with a red label", fr_intro="Jambon ibérique de bellota 50 % avec sceau rouge",
            en_fat="Each slice shows the marbling of infiltrated fat characteristic of acorn-fed Iberian ham.",
            fr_fat="Chaque tranche présente le persillage de gras infiltré caractéristique de l'ibérique de bellota.",
            en_cur="more than <strong>36 months of curing</strong>", fr_cur="plus de <strong>36 mois d'affinage</strong>",
            en_extra="", fr_extra="",
            en_meta="50% Bellota", fr_meta="Bellota 50 %", months_en="36+", months_fr="+36",
        ),
        "jamon-cebo-de-campo-50-iberico": dict(
            en_name="50% Ibérico Cebo de Campo Ham", fr_name="Jambon Cebo de Campo 50 % ibérique", pct="50",
            en_intro="50% Ibérico Cebo de Campo ham with a green label", fr_intro="Jambon de Cebo de Campo 50 % ibérique avec sceau vert",
            en_fat="Raised free-range and fed with natural feed and pastures, this ham offers a clean, balanced flavor with an Iberian character.",
            fr_fat="Élevé en liberté et nourri de céréales naturelles et de pâturages, ce jambon offre un goût pur, équilibré et de caractère ibérique.",
            en_cur="a minimum curing of <strong>30 months</strong>", fr_cur="un affinage minimal de <strong>30 mois</strong>",
            en_extra="", fr_extra="",
            en_meta="50% Cebo de Campo", fr_meta="Cebo de Campo 50 %", months_en="30+", months_fr="+30",
        ),
    }
    out = {}
    for base, m in marcas.items():
        for kind in ("a-mano", "a-maquina"):
            hand = kind == "a-mano"
            handle = f"{base}-loncheado-{kind}"
            other = f"{base}-loncheado-{'a-maquina' if hand else 'a-mano'}"
            g = "80" if hand else "100"
            t = {}
            t["title"] = {
                "en": f"{m['en_name']} — {'Hand-Sliced' if hand else 'Machine-Sliced'}",
                "fr": f"{m['fr_name']} — {'Tranché à la main' if hand else 'Tranché à la machine'}",
            }
            if hand:
                en_p2 = (f"<p>Each pack is sliced by hand by master carvers. Hand slicing keeps the original flavors of the ham: each slice "
                         f"lets you enjoy its full texture, fat and aroma. With {m['en_cur']}.</p><ul>\n{m['en_extra']}"
                         f"<li>Hand-sliced · {g} g pack</li>\n<li>Keeps the original flavors of the ham</li>\n"
                         f"<li>Irregular slice that releases all its texture, fat and aroma</li>\n<li>Vacuum-packed, ready to serve or give as a gift</li>\n</ul>"
                         f"<p>Prefer a uniform, practical slice for everyday? Discover the <a href=\"/en/products/{other}\">{m['en_name']}, machine-sliced</a>.</p>")
                fr_p2 = (f"<p>Chaque boîte est tranchée à la main par des maîtres trancheurs. La coupe à la main préserve les saveurs d'origine du jambon : "
                         f"chaque tranche révèle toute sa texture, son gras et son arôme. Avec {m['fr_cur']}.</p><ul>\n{m['fr_extra']}"
                         f"<li>Tranché à la main · boîte de {g} g</li>\n<li>Préserve les saveurs d'origine du jambon</li>\n"
                         f"<li>Tranche irrégulière qui libère toute sa texture, son gras et son arôme</li>\n<li>Emballé sous vide, prêt à servir ou à offrir</li>\n</ul>"
                         f"<p>Vous préférez une tranche uniforme et pratique au quotidien ? Découvrez le <a href=\"/fr/products/{other}\">{m['fr_name']}, tranché à la machine</a>.</p>")
            else:
                en_p2 = (f"<p>Each pack is sliced by machine: a uniform, regular slice, practical for toasts, sandwiches and boards and for everyday. "
                         f"With {m['en_cur']}.</p><ul>\n{m['en_extra']}"
                         f"<li>Machine-sliced · {g} g pack</li>\n<li>Uniform slice, ideal for everyday</li>\n<li>Vacuum-packed, ready to serve or give as a gift</li>\n</ul>"
                         f"<p>Looking for the most artisanal cut? Discover the <a href=\"/en/products/{other}\">{m['en_name']}, hand-sliced</a>.</p>")
                fr_p2 = (f"<p>Chaque boîte est tranchée à la machine : tranche uniforme et régulière, pratique pour les tartines, les sandwichs, les planches et le quotidien. "
                         f"Avec {m['fr_cur']}.</p><ul>\n{m['fr_extra']}"
                         f"<li>Tranché à la machine · boîte de {g} g</li>\n<li>Tranche uniforme, idéale au quotidien</li>\n<li>Emballé sous vide, prêt à servir ou à offrir</li>\n</ul>"
                         f"<p>Vous cherchez la coupe la plus artisanale ? Découvrez le <a href=\"/fr/products/{other}\">{m['fr_name']}, tranché à la main</a>.</p>")
            t["body_html"] = {
                "en": f"<p>{m['en_intro']}, <strong>{'hand-sliced' if hand else 'machine-sliced'}</strong> and vacuum-packed in <strong>{g} g</strong> packs. {m['en_fat']}</p>" + en_p2,
                "fr": f"<p>{m['fr_intro']}, <strong>{'tranché à la main' if hand else 'tranché à la machine'}</strong> et emballé sous vide en boîtes de <strong>{g} g</strong>. {m['fr_fat']}</p>" + fr_p2,
            }
            t["meta_title"] = {
                "en": f"{m['en_meta']} Ham, {'Hand-Sliced' if hand else 'Machine-Sliced'} | Casa Maravillas",
                "fr": f"Jambon {m['fr_meta']} {'tranché à la main' if hand else 'tranché à la machine'} | Casa Maravillas",
            }
            t["meta_description"] = {
                "en": (f"{m['en_name'].replace(' Ham', '')} ham, {'hand-sliced' if hand else 'machine-sliced'}, {g} g pack. "
                       + ("Keeps the original flavor: all the texture, fat and aroma. " if hand else "Uniform slice, ideal for everyday. ")
                       + f"{m['months_en']} months of curing. Shipping to Europe."),
                "fr": (f"Jambon {m['fr_meta']} {'tranché à la main' if hand else 'tranché à la machine'}, boîte de {g} g. "
                       + ("Préserve la saveur d'origine : toute la texture, le gras et l'arôme. " if hand else "Tranche uniforme, idéale au quotidien. ")
                       + f"{m['months_fr']} mois d'affinage. Livraison en Europe."),
            }
            t["product_type"] = {"en": "Iberian Ham", "fr": "Jambon ibérique"}
            out[handle] = t
    out["servicio-de-preparacion-del-jamon"] = {"title": {"en": "Ham preparation service", "fr": "Service de préparation du jambon"}}
    return out


PRODUCT_RULES = _hand_machine()

# ── Colecciones por handle ──
COLLECTION_RULES = {
    "regalos-ibericos": {
        "title": {"en": "Iberian Gifts", "fr": "Cadeaux ibériques"},
        "body_html": {
            "en": "<p>A curated selection of the best Iberian packs to give as gifts. Ham and cured meats from the finest dehesas of Salamanca, gathered in gourmet baskets for those who appreciate the authentic.</p><p>Perfect for any occasion: birthdays, Christmas, corporate celebrations or simply to surprise someone special.</p>",
            "fr": "<p>Une sélection soignée des meilleurs coffrets ibériques à offrir. Jambon et charcuteries des meilleures dehesas de Salamanque, réunis dans des paniers gourmets pour ceux qui apprécient l'authentique.</p><p>Parfaits pour toutes les occasions : anniversaires, Noël, fêtes d'entreprise ou simplement pour surprendre quelqu'un de spécial.</p>",
        },
        "meta_title": {"en": "Gourmet Iberian Gifts — Acorn-fed Ham and Cured Meat Baskets — Casa Maravillas",
                       "fr": "Cadeaux ibériques gourmets — Paniers de jambon et charcuteries de bellota — Casa Maravillas"},
        "meta_description": {"en": "Gourmet baskets with acorn-fed Iberian ham and cured meats. The perfect gift for any occasion.",
                             "fr": "Paniers gourmets avec jambon ibérique de bellota et charcuteries. Le cadeau parfait pour toutes les occasions."},
    },
    "loncheados": {"title": {"en": "Sliced Meats", "fr": "Produits tranchés"}},
    "jamones": {
        "meta_title": {"en": "Acorn-fed and Cebo de Campo Iberian Hams - Casa Maravillas",
                       "fr": "Jambons ibériques de bellota et de Cebo de Campo - Casa Maravillas"},
        "meta_description": {"en": "Discover our selection of acorn-fed and cebo de campo Iberian hams. Whole pieces and sliced, shipped across Europe. Casa Maravillas.",
                             "fr": "Découvrez notre sélection de jambons ibériques de bellota et de cebo de campo. Pièces entières et tranchées, livrées dans toute l'Europe. Casa Maravillas."},
    },
    "embutidos": {
        "meta_title": {"en": "Acorn-fed Iberian Cured Meats | Gourmet Selection – Casa Maravillas",
                       "fr": "Charcuteries ibériques de bellota | Sélection gourmet – Casa Maravillas"},
        "meta_description": {"en": "Discover our selection of acorn-fed Iberian cured meats. Authentic, artisan flavor. Shipping to Spain and Europe.",
                             "fr": "Découvrez notre sélection de charcuteries ibériques de bellota. Saveur authentique et artisanale. Livraison en Espagne et en Europe."},
    },
}

# ── Reglas por texto original exacto: (tipo, trozo de la clave, texto es o None=cualquiera, {locale: texto}) ──
# Con None solo se rellenan huecos/outdated de esa clave.
RULES2 = [
    ("LINK", "title", "Loncheados", {"en": "Sliced Meats", "fr": "Produits tranchés"}),
    ("LINK", "title", "Packs y Regalos", {"en": "Packs & Gifts", "fr": "Coffrets & Cadeaux"}),
    # Banda de confianza (producto)
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "trust_item_pGzHrd.title:", "Garantía 100%", {"en": "100% Guarantee", "fr": "Garantie 100 %"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "trust_item_pGzHrd.description:", "Si no te convence, puedes devolverlo.",
     {"en": "If you're not convinced, you can return it.", "fr": "Si vous n'êtes pas convaincu, vous pouvez le retourner."}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", ".trust.trust-3.title:", "Garantía 100%", {"en": "100% Guarantee", "fr": "Garantie 100 %"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", ".trust.trust-3.description:", "Si no te convence, puedes devolverlo.",
     {"en": "If you're not convinced, you can return it.", "fr": "Si vous n'êtes pas convaincu, vous pouvez le retourner."}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "title", "Tres niveles de selección", {"en": "Three selection levels", "fr": "Trois niveaux de sélection"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "description", "Oro, plata y bronce", {"en": "Gold, silver and bronze", "fr": "Or, argent et bronze"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "trust_item_formato.description:", "Loncheado, deshuesado o pieza entera",
     {"en": "Sliced, boneless or whole piece", "fr": "Tranché, désossé ou pièce entière"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "title_exterior:", "Envío a toda Europa", {"en": "Shipping across Europe", "fr": "Livraison dans toute l'Europe"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "description_exterior:", "Con seguimiento", {"en": "With tracking", "fr": "Avec suivi"}),
    # Raza → Breed
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "kv_1_label:", "Raza", {"en": "Breed", "fr": "Race"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "detail_card_edJprB.label:", "Raza", {"en": "Breed", "fr": "Race"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "accordion_z7nhkT.title:", "Raza y Alimentación", {"en": "Breed and Feeding", "fr": "Race et alimentation"}),
    # Colección Loncheados
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "hero.eyebrow:", "Listo para disfrutar", {"en": "Ready to enjoy", "fr": "Prêt à déguster"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "hero.heading:", "Loncheados Ibéricos", {"en": "Sliced Iberian Meats", "fr": "Produits ibériques tranchés"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.eyebrow:", "Nuestra gama", {"en": "Our range", "fr": "Notre gamme"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.heading:", "Elige tu loncheado", {"en": "Choose your sliced meat", "fr": "Choisissez votre produit tranché"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.cat1_name:", "Jamón", {"en": "Ham", "fr": "Jambon"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.cat2_name:", "Lomo", {"en": "Loin", "fr": "Longe"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.cat3_name:", "Chorizo y salchichón", {"en": "Chorizo and salchichón", "fr": "Chorizo et salchichón"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.cat1_label:", "6 referencias", {"en": "6 products", "fr": "6 références"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.cat2_label:", "3 referencias", {"en": "3 products", "fr": "3 références"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "tiers.cat3_label:", "2 referencias", {"en": "2 products", "fr": "2 références"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "collection.eyebrow:", "Nuestra selección", {"en": "Our selection", "fr": "Notre sélection"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "collection.empty_label:", "No hay loncheados disponibles en este momento.",
     {"en": "No sliced products available at the moment.", "fr": "Aucun produit tranché disponible pour le moment."}),
    # Constructor de packs
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "builder.eyebrow:", "Packs de regalo · Casa Maravillas", {"en": "Gift packs · Casa Maravillas", "fr": "Coffrets cadeaux · Casa Maravillas"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "builder.heading:", "Crea tu pack a tu medida de forma sencilla",
     {"en": "Create your custom pack, simply", "fr": "Créez simplement votre coffret sur mesure"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "builder.intro:", "El arte de regalar empieza por elegir bien. Crea tu pack ibérico.",
     {"en": "The art of gifting starts with choosing well. Create your Iberian pack.", "fr": "L'art d'offrir commence par bien choisir. Créez votre coffret ibérique."}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "newsletter.incentive_text:", "Código de bienvenida", {"en": "Welcome code", "fr": "Code de bienvenue"}),
    # Metacampos sin equivalente reutilizable
    ("METAFIELD", "value", "'+30 meses", {"en": "'+30 months", "fr": "'+30 mois"}),
    ("METAFIELD", "value", "'+36 meses", {"en": "'+36 months", "fr": "'+36 mois"}),
    ("METAFIELD", "value", "Ibérico 50%", {"en": "50% Ibérico", "fr": "50% Ibérique"}),
    ("METAFIELD", "value", "Estuche de 100 g · packs de 1 o 10 estuches", {"en": "100 g pack · packs of 1 or 10", "fr": "Boîte de 100 g · lots de 1 ou 10 boîtes"}),
    ("METAFIELD", "value", "Estuche de 80 g · packs de 1 o 10 estuches", {"en": "80 g pack · packs of 1 or 10", "fr": "Boîte de 80 g · lots de 1 ou 10 boîtes"}),
]

# Consejos de corte (metacampo custom.cutting_tips): se emparejan por el principio del texto
CUTTING_TIPS = {
    "machine": {
        "es_has": "al ser uniformes, se manejan",
        "en": "Take the pack out of the refrigerator and let it come to room temperature for 10-15 minutes before opening. Serve the slices directly on the plate or use them in toasts, sandwiches and boards: being uniform, they are easy to handle and combine. Don't use a fork or tongs — the warmth of your hands helps the fat shine. Once opened, consume on the same day to enjoy its full freshness.",
        "fr": "Sortez la boîte du réfrigérateur et laissez-la tempérer 10 à 15 minutes avant de l'ouvrir. Servez les tranches directement dans l'assiette ou utilisez-les sur des tartines, des sandwichs et des planches : étant uniformes, elles se manipulent et s'associent facilement. N'utilisez ni fourchette ni pince — la chaleur des mains aide le gras à briller. Une fois ouverte, consommez dans la journée pour profiter de toute sa fraîcheur.",
    },
    "hand": {
        "es_has": "al ser irregulares, se aprecia mejor",
        "en": "Take the pack out of the refrigerator and let it come to room temperature for 10-15 minutes before opening. Serve the slices directly on the plate, without piling them up too much: as they are irregular, their aroma is better appreciated when they are spread out. Don't use a fork or tongs — the warmth of your hands helps the fat shine. Once opened, consume on the same day to enjoy its full freshness.",
        "fr": "Sortez la boîte du réfrigérateur et laissez-la tempérer 10 à 15 minutes avant de l'ouvrir. Servez les tranches directement dans l'assiette, sans les empiler trop : étant irrégulières, leur arôme s'apprécie mieux lorsqu'elles sont bien séparées. N'utilisez ni fourchette ni pince — la chaleur des mains aide le gras à briller. Une fois ouverte, consommez dans la journée pour profiter de toute sa fraîcheur.",
    },
}

# Textos de la ficha nutricional en rich text (JSON): trozo ES → {locale: texto}
JSON_TEXT = {
    "Valor energético: 1448 kJ / 348 kcal · Grasas: 24 g (saturadas: 9 g) · Hidratos: 0 g · Proteína: 31 g · Sal: 4 g":
        {"en": "Energy value: 1448 kJ / 348 kcal · Fat: 24 g (saturates: 9 g) · Carbohydrates: 0 g · Protein: 31 g · Salt: 4 g",
         "fr": "Valeur énergétique : 1448 kJ / 348 kcal · Matières grasses : 24 g (dont saturées : 9 g) · Glucides : 0 g · Protéines : 31 g · Sel : 4 g"},
    "Información nutricional por 100 g de producto:": {"en": "Nutritional information per 100 g of product:", "fr": "Informations nutritionnelles pour 100 g de produit :"},
    "Valor energético: 1448 kJ / 348 kcal": {"en": "Energy value: 1448 kJ / 348 kcal", "fr": "Valeur énergétique : 1448 kJ / 348 kcal"},
    "Grasas: 24 g | de las cuales saturadas: 9 g": {"en": "Fat: 24 g | of which saturates: 9 g", "fr": "Matières grasses : 24 g | dont saturées : 9 g"},
    "Hidratos de carbono: 0 g | de los cuales azúcares: 0 g": {"en": "Carbohydrates: 0 g | of which sugars: 0 g", "fr": "Glucides : 0 g | dont sucres : 0 g"},
    "Proteína: 31 g": {"en": "Protein: 31 g", "fr": "Protéines : 31 g"},
    "Sal: 4 g": {"en": "Salt: 4 g", "fr": "Sel : 4 g"},
}

# FAQ de la portada (por clave, solo huecos/outdated). {locale: texto}
FAQ = {
    "faq_item_69jJEf.question:": {"en": "How do we select the hams in the shop?", "fr": "Comment sélectionnons-nous les jambons de la boutique ?"},
    "faq_item_69jJEf.answer:": {
        "en": "<p>Every ham in the shop goes through a rigorous selection process: it has to pass four filters to be part of Casa Maravillas. We look at the <strong>origin</strong>, the <strong>rearing</strong>, the <strong>time</strong> and the <strong>piece</strong>. If you want to understand what we look for in each one, we explain it on the <a href=\"/en/pages/nosotros\">About us</a> page.</p>",
        "fr": "<p>Chaque jambon de la boutique passe par un processus de sélection rigoureux : il doit réussir quatre filtres pour faire partie de Casa Maravillas. Nous examinons l'<strong>origine</strong>, l'<strong>élevage</strong>, le <strong>temps</strong> et la <strong>pièce</strong>. Pour comprendre ce que nous recherchons dans chacun, rendez-vous sur la page <a href=\"/fr/pages/nosotros\">Qui sommes-nous</a>.</p>"},
    "faq_item_gLmL3f.answer:": {
        "en": "<p>Orders placed before 12:00 are prepared and shipped the same day, with delivery in 24-48 hours on the Peninsula. For the rest of Europe, delivery takes 3-5 business days depending on the destination. During periods of high demand (Christmas, Easter) the delivery time may be slightly longer.</p>",
        "fr": "<p>Les commandes passées avant 12h00 sont préparées et expédiées le jour même, avec une livraison en 24-48 heures en Espagne péninsulaire. Pour le reste de l'Europe, le délai est de 3 à 5 jours ouvrables selon la destination. En période de forte demande (Noël, Semaine sainte), le délai peut être légèrement allongé.</p>"},
    "faq_item_WxYXfM.question:": {"en": "What if I don't know how to slice my ham?", "fr": "Et si je ne sais pas trancher mon jambon ?"},
    "faq_item_WxYXfM.answer:": {
        "en": "<p>If you have chosen a whole piece, you can order it boneless so it is easier to carve and to store. And if you prefer to enjoy the whole ham already sliced, we also offer that format within the whole piece, machine-sliced or hand-sliced and vacuum-packed. Just choose the format on the product page.</p>",
        "fr": "<p>Si vous avez choisi une pièce entière, vous pouvez la commander désossée pour qu'elle soit plus facile à couper et à conserver. Et si vous préférez profiter de tout le jambon déjà tranché, nous proposons aussi ce format pour la pièce entière, tranché à la machine ou à la main et emballé sous vide. Il suffit de choisir le format sur la fiche produit.</p>"},
    "faq_item_Ath4dk.question:": {"en": "What guarantee do I have if I'm not convinced by the ham?", "fr": "Quelle garantie ai-je si le jambon ne me convainc pas ?"},
    "faq_item_Ath4dk.answer:": {
        "en": "<p>We want you to be satisfied with your purchase. If your order arrives in poor condition or the ham is not what you expected, write to us at <a href=\"mailto:info@casamaravillas.com\">info@casamaravillas.com</a> or call us on <a href=\"tel:966113446\">966 11 34 46</a> and we'll sort it out with you. You can also check our <a href=\"/en/pages/devoluciones\">returns policy</a>.</p>",
        "fr": "<p>Nous voulons que vous soyez satisfait de votre achat. Si votre commande arrive en mauvais état ou si le jambon n'est pas ce que vous attendiez, écrivez-nous à <a href=\"mailto:info@casamaravillas.com\">info@casamaravillas.com</a> ou appelez-nous au <a href=\"tel:966113446\">966 11 34 46</a> et nous trouverons une solution avec vous. Vous pouvez aussi consulter notre <a href=\"/fr/pages/devoluciones\">politique de retours</a>.</p>"},
}
