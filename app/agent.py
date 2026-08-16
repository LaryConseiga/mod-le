"""Turn one inbound WhatsApp message into one reply.

Pipeline per message (Feuilles A-02 / A-03 de l'architecture) :
  1. load conversation state + recent history from Supabase
  2. RAG top-k over menu_items + restaurant_info (Feuille A-02) for the
     free-form question ; the full compact menu is *also* given inline so
     order function-calling (add_item) always has accurate ids/prices,
     independent of what retrieval happens to surface this turn.
  3. one Groq call with function-calling tools for cart mutations
  4. cart/order side effects are applied deterministically in Python —
     never let the LLM phrase prices or totals itself.

Confirming an order clears the cart, but the *last confirmed order* stays
on the conversation (conv["last_order"]) so a customer who corrects a
detail right after confirming ("ah, en fait je veux être livré") can be
handled via update_last_order instead of the bot claiming the cart is
empty and having no idea what they're talking about.
"""
from __future__ import annotations

import json
import time
import uuid

from ingestion.retrieval import search as rag_search

from app import db
from app.groq_client import chat
from app.orders import push_to_partner

WELCOME = "Bonjour ! Bienvenue chez Issouf Fast Food 👋"

SYSTEM_PROMPT_TEMPLATE = """Tu es l'assistant WhatsApp du restaurant Issouf Fast Food (Burkina Faso).
Réponds en français, de façon brève et chaleureuse, adaptée à une conversation WhatsApp (pas de longues listes formatées, pas de markdown).
Sois toujours extrêmement courtois et poli : vouvoie systématiquement le client (jamais de "tu"), utilise des formules de politesse naturelles ("avec plaisir", "je vous en prie", "merci beaucoup", "n'hésitez pas"), et reste respectueux et aimable même si le client est bref, familier ou impatient.
Ne invente jamais un plat, un prix ou une information : base-toi uniquement sur le menu et le contexte ci-dessous.
Pour ajouter, retirer ou confirmer des articles du panier, corriger une commande déjà confirmée, ou transférer la conversation à un humain, utilise impérativement les outils fournis — ne fais jamais semblant en texte libre.

Distingue bien une QUESTION d'une COMMANDE :
- Si le client demande un prix, la composition d'un plat, les horaires, ou ce qui est disponible dans une catégorie ("c'est combien le kebab ?", "il y a quoi dedans ?", "vous avez quoi comme sucrerie ?", "qu'est-ce que vous avez en jus ?", "vous avez du coca ?") : réponds simplement en texte à partir du menu/contexte. N'appelle AUCUN outil, et n'ajoute rien au panier — même si un seul plat correspond à la catégorie demandée.
- N'appelle add_item QUE si le client exprime clairement l'intention de commander ce plat précis ("je veux", "donne-moi", "ajoute", "je prends"). Une question sur une catégorie ou une marque n'est jamais une commande.
- Quand le client demande ce qui est disponible dans une catégorie précise (sucreries, jus, hamburgers...), cherche TOUTES les entrées correspondantes dans le MENU COMPLET ci-dessous (pas seulement le contexte) et énumère-les avec leur prix. Ne réponds jamais "nous avons plusieurs options" sans donner la liste.
- Quand le client demande le menu en général ("c'est quoi le menu ?", "qu'est-ce que vous avez ?", "montrez-moi la carte") sans préciser de catégorie : ne liste PAS les 30+ plats un par un. Cite quelques exemples représentatifs de 3-4 catégories différentes (nom + prix), et invite-le à demander une catégorie précise ou un plat en particulier pour plus de détails.

Avant de confirmer une commande (confirm_order), le client doit avoir dit explicitement "livraison" ou "sur place"/"je viens chercher" (ou équivalent) DANS la conversation. Si tu ne trouves pas cette information dans les messages précédents, n'appelle PAS confirm_order même si le client dit "confirme" ou "c'est bon" — réponds en texte "Récupération sur place ou livraison ?" et attends sa réponse avant de confirmer. Ne devine jamais, même "pickup" par défaut.

Si le client veut corriger un détail (mode de récupération/livraison) de la commande qu'il vient tout juste de confirmer, utilise update_last_order — ne dis jamais que le panier est vide dans ce cas, la commande existe déjà, seul le panier a été vidé après confirmation.

{greeting_instruction}

PANIER ACTUEL DU CLIENT :
{cart_summary}

DERNIÈRE COMMANDE CONFIRMÉE (si le client veut la corriger) :
{last_order_summary}

MENU COMPLET (id | nom | catégorie | prix) :
{menu_table}

CONTEXTE PERTINENT POUR CETTE QUESTION :
{rag_context}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_item",
            "description": "Ajoute un ou plusieurs plats au panier du client. UNIQUEMENT si le client demande explicitement de commander/ajouter ce plat — jamais en réponse à une simple question sur le prix, la composition ou le menu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "menu_item_id": {
                                    "type": "string",
                                    "description": "id exact du plat, tiré du menu fourni ci-dessus",
                                },
                                "quantity": {"type": "integer", "minimum": 1},
                            },
                            "required": ["menu_item_id", "quantity"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_item",
            "description": "Retire un plat du panier du client.",
            "parameters": {
                "type": "object",
                "properties": {"menu_item_id": {"type": "string"}},
                "required": ["menu_item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_order",
            "description": "Confirme la commande actuelle et déclenche son envoi au restaurant. Uniquement quand le client a explicitement validé ET précisé retrait sur place ou livraison. Ne DEVINE jamais ce champ : si le client n'a pas dit lequel, n'appelle pas cette fonction et demande-le en texte à la place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fulfillment": {
                        "type": "string",
                        "enum": ["pickup", "delivery"],
                        "description": "Le client récupère sur place (pickup) ou se fait livrer (delivery). Ne renseigne ce champ QUE si le client l'a dit explicitement dans la conversation — sinon laisse cet appel de côté.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_last_order",
            "description": "Corrige un détail de la commande que le client vient de confirmer (mode de récupération/livraison), quand il veut rectifier juste après confirmation plutôt que passer une nouvelle commande.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fulfillment": {
                        "type": "string",
                        "enum": ["pickup", "delivery"],
                        "description": "Nouveau mode : retrait sur place (pickup) ou livraison (delivery)",
                    }
                },
                "required": ["fulfillment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_human",
            "description": "Marque la conversation pour qu'un employé humain prenne le relais (demande explicite du client, ou question hors du cadre de l'agent).",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": [],
            },
        },
    },
]


def _format_menu_table(items: list[dict]) -> str:
    return "\n".join(f"- {i['id']} | {i['name']} | {i['category']} | {i['price_text']}" for i in items)


def _format_rag_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(aucun contexte pertinent trouvé)"
    return "\n".join(f"- {c['content']}" for c in chunks)


def _format_cart(cart: list[dict]) -> str:
    if not cart:
        return "(vide)"
    return "\n".join(f"- {item['quantity']} x {item['name']} ({item['price_text']})" for item in cart)


def _format_last_order(last_order: dict | None) -> str:
    if not last_order:
        return "(aucune)"
    payload = last_order.get("payload", {})
    items = payload.get("items", [])
    mode = "Livraison" if payload.get("fulfillment") == "delivery" else "Retrait sur place"
    items_text = ", ".join(f"{it['qty']} x {it['name']}" for it in items) or "(détail indisponible)"
    return f"n°{last_order.get('order_id', '')[:8]} — {items_text} — {mode}"


def handle_incoming_message(phone_number: str, text: str) -> str | None:
    t0 = time.perf_counter()
    with db.get_connection() as conn:
        conv = db.get_or_create_conversation(conn, phone_number)

        if conv["human_takeover"]:
            db.save_message(conn, phone_number, "user", text)
            return None  # un humain gère déjà cette conversation, l'agent se tait

        history = db.get_recent_messages(conn, phone_number, limit=10)
        db.save_message(conn, phone_number, "user", text)
        menu_items = db.get_menu_items(conn)
        t1 = time.perf_counter()

        rag_chunks = rag_search(text, k=4, conn=conn)
        t2 = time.perf_counter()

        greeting_instruction = (
            "C'est le tout premier message de cette conversation : un message de bienvenue "
            '("Bonjour ! Bienvenue chez Issouf Fast Food") a DÉJÀ été ajouté automatiquement '
            "avant ta réponse. Ne dis pas \"bonjour\" ni \"bienvenue\" toi-même — réponds "
            "directement à la question ou à la demande du client."
            if conv["is_new"]
            else ""
        )
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            menu_table=_format_menu_table(menu_items),
            rag_context=_format_rag_context(rag_chunks),
            cart_summary=_format_cart(conv["cart"]),
            last_order_summary=_format_last_order(conv["last_order"]),
            greeting_instruction=greeting_instruction,
        )
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": text}]

        response = chat(messages, tools=TOOLS)
        t3 = time.perf_counter()
        choice = response.choices[0].message

        if choice.tool_calls:
            reply = _execute_tool_calls(conn, phone_number, conv, choice.tool_calls, menu_items)
        else:
            reply = choice.content or "Désolé, je n'ai pas compris — pouvez-vous reformuler ?"
        t4 = time.perf_counter()

        if conv["is_new"]:
            reply = f"{WELCOME}\n{reply}"

        db.save_message(conn, phone_number, "assistant", reply)

        print(
            f"[latence] db_init={t1 - t0:.2f}s rag={t2 - t1:.2f}s groq={t3 - t2:.2f}s "
            f"tool_exec={t4 - t3:.2f}s total={t4 - t0:.2f}s",
            flush=True,
        )
        return reply


def _execute_tool_calls(conn, phone_number: str, conv: dict, tool_calls, menu_items: list[dict]) -> str:
    menu_by_id = {item["id"]: item for item in menu_items}
    cart = [dict(item) for item in conv["cart"]]
    order_confirmed = False
    fulfillment: str | None = None
    needs_fulfillment = False
    last_order_fulfillment: str | None = None
    human_requested = False

    for call in tool_calls:
        name = call.function.name
        try:
            args = json.loads(call.function.arguments)
        except (TypeError, ValueError):
            args = {}

        if name == "add_item":
            for entry in args.get("items", []):
                item = menu_by_id.get(entry.get("menu_item_id"))
                if item is None:
                    continue
                quantity = max(1, int(entry.get("quantity", 1)))
                existing = next((c for c in cart if c["id"] == item["id"]), None)
                if existing:
                    existing["quantity"] += quantity
                else:
                    cart.append(
                        {"id": item["id"], "name": item["name"], "price_text": item["price_text"], "quantity": quantity}
                    )

        elif name == "remove_item":
            cart = [c for c in cart if c["id"] != args.get("menu_item_id")]

        elif name == "confirm_order":
            if cart:
                candidate = args.get("fulfillment")
                if candidate in ("pickup", "delivery"):
                    order_confirmed = True
                    fulfillment = candidate
                else:
                    needs_fulfillment = True

        elif name == "update_last_order":
            candidate = args.get("fulfillment")
            if candidate in ("pickup", "delivery"):
                last_order_fulfillment = candidate

        elif name == "request_human":
            human_requested = True

    if human_requested:
        db.update_cart(conn, phone_number, cart)
        db.set_human_takeover(conn, phone_number, True)
        return "Je transmets votre demande à un membre de l'équipe, qui prend le relais dans un instant. 🙏"

    if order_confirmed and fulfillment:
        return _confirm_order(conn, phone_number, cart, fulfillment)

    if needs_fulfillment:
        db.update_cart(conn, phone_number, cart)
        return "Récupération sur place ou livraison ? 🙂"

    if last_order_fulfillment:
        last_order = conv.get("last_order")
        if not last_order:
            return "Je ne retrouve pas de commande récente à modifier — voulez-vous en passer une nouvelle ?"
        return _update_last_order(conn, phone_number, last_order, last_order_fulfillment)

    db.update_cart(conn, phone_number, cart)
    if not cart:
        return "Votre panier est vide pour l'instant. Que souhaitez-vous commander ?"
    return f"C'est noté !\n{_format_cart(cart)}\nSouhaitez-vous autre chose, ou je confirme la commande ?"


def _confirm_order(conn, phone_number: str, cart: list[dict], fulfillment: str) -> str:
    order_id = str(uuid.uuid4())
    idempotency_key = str(uuid.uuid4())
    payload = {
        "idempotency_key": idempotency_key,
        "source": "whatsapp_agent",
        "customer": {"phone": phone_number},
        "items": [
            {"menu_item_id": c["id"], "name": c["name"], "qty": c["quantity"], "price_text": c["price_text"]}
            for c in cart
        ],
        "fulfillment": fulfillment,
    }

    status, partner_order_id = push_to_partner(payload)
    db.insert_order_outbox(conn, order_id, phone_number, payload, idempotency_key, status, partner_order_id)
    db.update_cart(conn, phone_number, [])
    db.update_last_order(conn, phone_number, {"order_id": order_id, "payload": payload})

    ref = partner_order_id or order_id[:8]
    mode = "Livraison" if fulfillment == "delivery" else "Retrait sur place"
    return (
        f"Commande confirmée ✅ (n°{ref})\n"
        f"{_format_cart(cart)}\n"
        f"{mode} — préparation environ 20 min.\n"
        f"Paiement Orange Money ou cash au +226 67 33 69 74."
    )


def _update_last_order(conn, phone_number: str, last_order: dict, new_fulfillment: str) -> str:
    payload = dict(last_order.get("payload", {}))
    payload["fulfillment"] = new_fulfillment
    order_id = last_order["order_id"]

    db.update_order_outbox_payload(conn, order_id, payload)
    db.update_last_order(conn, phone_number, {"order_id": order_id, "payload": payload})

    mode = "Livraison" if new_fulfillment == "delivery" else "Retrait sur place"
    return f"C'est corrigé ✅ — commande n°{order_id[:8]} : {mode}."
