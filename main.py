import os
import sys
import re
import time
import getpass
import asyncio
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from telethon import TelegramClient, events, utils
from telethon.errors import ChatForwardsRestrictedError
from telethon.tl.types import Message, MessageEntityTextUrl, MessageEntityUrl
import colorama
from colorama import Fore, Style

from config_manager import ConfigManager
from filter_engine import FilterEngine

# Inicializa colorama para suporte a cores no terminal Windows
colorama.init(autoreset=True)

# Carrega variáveis de ambiente do .env
load_dotenv()

API_ID_RAW = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")
ENV_TARGET_CHAT = os.getenv("TARGET_CHAT")
SESSION_NAME = "filtro_promocoes"

if not API_ID_RAW or not API_HASH:
    print(Fore.RED + "[ERRO FATAL] TELEGRAM_API_ID e TELEGRAM_API_HASH devem estar configurados no arquivo .env!")
    sys.exit(1)

try:
    API_ID = int(API_ID_RAW)
except ValueError:
    print(Fore.RED + f"[ERRO FATAL] TELEGRAM_API_ID deve ser numérico! Valor atual: {API_ID_RAW}")
    sys.exit(1)

# Inicializa gerenciador de configuração e motor de filtros
config = ConfigManager()
if config.target_chat == "me" and ENV_TARGET_CHAT and ENV_TARGET_CHAT.strip().lower() != "me":
    config.set_target_chat(ENV_TARGET_CHAT.strip())

engine = FilterEngine(
    keywords=config.keywords,
    negative_keywords=config.negative_keywords,
    cooldown_minutes=config.cooldown_minutes
)

# Inicializa o cliente Telethon
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Estatísticas em tempo de execução
stats = {
    "start_time": time.time(),
    "promos_found": 0,
    "messages_scanned": 0,
    "last_promo_time": None
}


def extract_urls(message: Message) -> List[str]:
    """Extrai todas as URLs do texto e das entidades da mensagem."""
    urls = []
    if not message:
        return urls

    # Entidades de formatação do Telegram (links embutidos)
    if message.entities:
        for ent in message.entities:
            if isinstance(ent, MessageEntityTextUrl) and ent.url:
                urls.append(ent.url)
            elif isinstance(ent, MessageEntityUrl) and message.message:
                raw_url = message.message[ent.offset:ent.offset + ent.length]
                if raw_url:
                    urls.append(raw_url)

    # Regex para pegar links no texto puro
    if message.message:
        matches = re.findall(r'https?://[^\s<>"]+', message.message)
        for m in matches:
            if m not in urls:
                urls.append(m)

    return urls


def format_uptime() -> str:
    elapsed = int(time.time() - stats["start_time"])
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"


def sync_config_if_changed():
    """Recarrega config.json e atualiza o motor de filtros caso o arquivo tenha mudado."""
    if config.reload_if_changed():
        engine.update_rules(
            config.keywords,
            config.negative_keywords,
            config.cooldown_minutes
        )
        time_str = datetime.now().strftime("%H:%M:%S")
        print(Fore.CYAN + f"[{time_str}] [RELOAD] config.json alterado no disco. Regras atualizadas ({len(config.keywords)} termos ativos)!")


async def handle_saved_command(event: events.NewMessage.Event, my_id: int):
    """Processa comandos de gerenciamento enviados em Mensagens Salvas."""
    sync_config_if_changed()
    text = (event.raw_text or "").strip()
    if not text.startswith("/"):
        return

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/ajuda", "/help", "/start"):
        help_msg = (
            "🤖 **Filtro de Promoções - Central de Comandos**\n\n"
            "🔍 **Palavras-chave (O que buscar):**\n"
            "• `/add <termo>` - Adiciona palavra (ex: `/add rtx 4060` ou com teto de preço `/add rtx 4060 < 2000`)\n"
            "• `/del <termo>` - Remove palavra (ex: `/del rtx 4060`)\n"
            "• `/listar` - Exibe termos de busca e bloqueados\n\n"
            "🚫 **Palavras Bloqueadas (Negativas / Ignorar):**\n"
            "• `/bloquear <termo>` - Ignora promos com o termo (ex: `/bloquear capa`)\n"
            "• `/desbloquear <termo>` - Remove termo bloqueado\n\n"
            "📢 **Canais:**\n"
            "• `/canais` - Lista seus canais de promoções\n"
            "• `/modo` - Alterna entre monitorar TODOS ou apenas canais da lista\n"
            "• `/addcanal <id/@user>` - Adiciona canal à lista restrita\n"
            "• `/delcanal <id/@user>` - Remove canal da lista restrita\n\n"
            "⚙️ **Status & Sistema:**\n"
            "• `/destino <me/@canal/id>` - Define para onde enviar os alertas\n"
            "• `/aqui` - Envie dentro de um grupo/canal privado para torná-lo o destino\n"
            "• `/status` - Resumo do bot e total de promoções capturadas\n"
            "• `/limparhistorico` - Reseta o histórico de duplicatas imediatas"
        )
        await event.reply(help_msg)

    elif cmd in ("/listar", "/list"):
        kw_list = "\n".join(f"• `{k}`" for k in config.keywords) if config.keywords else "_Nenhuma cadastrada_"
        neg_list = "\n".join(f"• `{k}`" for k in config.negative_keywords) if config.negative_keywords else "_Nenhuma cadastrada_"
        mode_str = "🌐 Monitorando **TODOS** os canais" if config.monitor_all else f"🎯 Monitorando apenas **{len(config.channels)}** canais específicos"

        msg = (
            "📋 **Configuração Atual do Filtro**\n\n"
            f"🔍 **Palavras-chave Ativas ({len(config.keywords)}):**\n{kw_list}\n\n"
            f"🚫 **Palavras Bloqueadas / Negativas ({len(config.negative_keywords)}):**\n{neg_list}\n\n"
            f"📡 **Modo de Operação:** {mode_str}\n"
            f"⏳ **Cooldown de Duplicatas:** {config.cooldown_minutes} minutos"
        )
        await event.reply(msg)

    elif cmd == "/add":
        if not arg:
            await event.reply("⚠️ Uso correto: `/add termo` ou `/add termo1, termo2`\nExemplo: `/add rtx 4060`")
            return

        terms = [t.strip() for t in arg.split(",") if t.strip()]
        added = []
        for t in terms:
            if config.add_keyword(t):
                added.append(t)

        if added:
            engine.update_rules(config.keywords, config.negative_keywords)
            await event.reply(f"✅ Adicionado(s) às buscas:\n" + "\n".join(f"• `{x}`" for x in added))
        else:
            await event.reply("⚠️ O(s) termo(s) já estavam na lista ou são inválidos.")

    elif cmd in ("/del", "/remover", "/rm"):
        if not arg:
            await event.reply("⚠️ Uso correto: `/del termo`\nExemplo: `/del rtx 4060`")
            return

        if config.remove_keyword(arg):
            engine.update_rules(config.keywords, config.negative_keywords)
            await event.reply(f"🗑️ Termo `{arg}` removido com sucesso!")
        else:
            await event.reply(f"⚠️ Termo `{arg}` não foi encontrado na lista ativa.")

    elif cmd in ("/bloquear", "/block"):
        if not arg:
            await event.reply("⚠️ Uso correto: `/bloquear termo`\nExemplo: `/bloquear capa, pelicula`")
            return

        terms = [t.strip() for t in arg.split(",") if t.strip()]
        added = []
        for t in terms:
            if config.add_negative_keyword(t):
                added.append(t)

        if added:
            engine.update_rules(config.keywords, config.negative_keywords)
            await event.reply(f"🚫 Adicionado(s) às palavras BLOQUEADAS:\n" + "\n".join(f"• `{x}`" for x in added))
        else:
            await event.reply("⚠️ O(s) termo(s) já estavam bloqueados ou são inválidos.")

    elif cmd in ("/desbloquear", "/unblock"):
        if not arg:
            await event.reply("⚠️ Uso correto: `/desbloquear termo`\nExemplo: `/desbloquear capa`")
            return

        if config.remove_negative_keyword(arg):
            engine.update_rules(config.keywords, config.negative_keywords)
            await event.reply(f"✅ Termo `{arg}` desbloqueado com sucesso!")
        else:
            await event.reply(f"⚠️ Termo `{arg}` não constava na lista de bloqueados.")

    elif cmd == "/modo":
        new_val = not config.monitor_all
        config.set_monitor_all(new_val)
        mode_str = "🌐 **TODOS** os canais" if new_val else f"🎯 **APENAS** canais da lista ({len(config.channels)} canais)"
        await event.reply(f"🔄 Modo alterado com sucesso!\nAgora monitorando: {mode_str}")

    elif cmd == "/canais":
        status_msg = await event.reply("⏳ Escaneando canais e grupos da sua conta...")
        channels_found = []
        try:
            async for dialog in client.iter_dialogs(limit=100):
                if dialog.is_channel or dialog.is_group:
                    username_str = f"@{dialog.entity.username} | " if getattr(dialog.entity, "username", None) else ""
                    channels_found.append(f"• **{dialog.name}** ({username_str}ID: `{dialog.id}`)")
        except Exception as e:
            await status_msg.edit(f"❌ Erro ao listar canais/grupos: {e}")
            return

        if not channels_found:
            await status_msg.edit("ℹ️ Nenhum canal ou grupo encontrado na sua conta.")
            return

        header = f"📢 **Seus Canais e Grupos ({len(channels_found)}):**\n\n"
        # Limita para não estourar 4096 caracteres do Telegram
        body = "\n".join(channels_found[:35])
        if len(channels_found) > 35:
            body += f"\n\n_... e mais {len(channels_found) - 35} canais._"

        await status_msg.edit(header + body)

    elif cmd == "/addcanal":
        if not arg:
            await event.reply("⚠️ Uso correto: `/addcanal @nomedocanal` ou `/addcanal -100123456789`")
            return
        if config.add_channel(arg):
            await event.reply(f"✅ Canal `{arg}` adicionado à lista monitorada!")
        else:
            await event.reply(f"⚠️ Canal `{arg}` já estava na lista.")

    elif cmd == "/delcanal":
        if not arg:
            await event.reply("⚠️ Uso correto: `/delcanal @nomedocanal`")
            return
        if config.remove_channel(arg):
            await event.reply(f"🗑️ Canal `{arg}` removido da lista monitorada!")
        else:
            await event.reply(f"⚠️ Canal `{arg}` não foi encontrado na lista.")

    elif cmd == "/limparhistorico":
        engine.history.clear()
        await event.reply("🧹 Histórico de duplicatas limpo com sucesso!")

    elif cmd == "/destino":
        if not arg:
            await event.reply(
                f"🎯 **Destino atual:** `{config.target_chat}`\n"
                "Para alterar, envie: `/destino me` (Mensagens Salvas) ou `/destino @seucanal` ou `/destino -100123456789`"
            )
            return
        config.set_target_chat(arg)
        await event.reply(f"✅ Destino dos alertas atualizado para: `{config.target_chat}`")

    elif cmd == "/status":
        last_promo = stats["last_promo_time"]
        last_str = datetime.fromtimestamp(last_promo).strftime("%H:%M:%S - %d/%m") if last_promo else "Nenhuma ainda"
        status_text = (
            "📊 **Status do Filtro de Promoções**\n\n"
            f"⏱️ **Tempo online:** `{format_uptime()}`\n"
            f"📥 **Mensagens analisadas:** `{stats['messages_scanned']}`\n"
            f"🎯 **Promoções capturadas:** `{stats['promos_found']}`\n"
            f"🕒 **Última captura:** `{last_str}`\n"
            f"🔍 **Palavras-chave ativas:** `{len(config.keywords)}`\n"
            f"🚫 **Palavras bloqueadas:** `{len(config.negative_keywords)}`\n"
            f"📡 **Modo:** `{'Todos os canais' if config.monitor_all else 'Canais específicos'}`\n"
            f"🎯 **Destino:** `{config.target_chat}`"
        )
        await event.reply(status_text)

    else:
        await event.reply("❓ Comando desconhecido. Digite `/ajuda` para ver os comandos disponíveis.")


@client.on(events.NewMessage)
async def on_new_message(event: events.NewMessage.Event):
    me = await client.get_me()

    # 1. Comandos em Mensagens Salvas (Saved Messages)
    if event.is_private and event.chat_id == me.id:
        await handle_saved_command(event, me.id)
        return

    # 2. Ignora se não for canal ou grupo
    if not (event.is_channel or event.is_group):
        return

    # Atalho rápido: enviar /aqui dentro de qualquer grupo ou canal privado define ele como destino
    raw_cmd = (event.raw_text or "").strip().lower()
    if event.out and raw_cmd in ("/aqui", "/definiraqui"):
        chat = await event.get_chat()
        chat_title = utils.get_display_name(chat) if chat else "este chat"
        config.set_target_chat(str(event.chat_id))
        await event.reply(
            f"✅ **Destino atualizado!**\n"
            f"As promoções filtradas agora aparecerão aqui em **{chat_title}** (`{event.chat_id}`)."
        )
        print(Fore.CYAN + f"[DESTINO] Alterado via /aqui para '{chat_title}' ({event.chat_id})")
        return

    # 3. Ignora mensagens enviadas pelo próprio usuário em outros grupos
    if event.out:
        return

    # Sincroniza eventuais edições manuais em config.json sem precisar reiniciar
    sync_config_if_changed()

    chat = await event.get_chat()

    # Nunca monitora o próprio chat/grupo de destino para evitar loops
    target_str_cfg = str(config.target_chat).strip()
    chat_username = getattr(chat, "username", "") or ""
    if str(event.chat_id) == target_str_cfg or (chat_username and target_str_cfg.lstrip("@").lower() == chat_username.lower()):
        return

    # 4. Verifica filtro de canais específicos se monitor_all estiver desativado
    if not config.monitor_all:
        chat_id = str(event.chat_id)
        username = getattr(chat, "username", "") or ""
        matched_channel = False

        for target in config.channels:
            target_str = str(target).strip()
            if target_str == chat_id or (username and target_str.lstrip("@").lower() == username.lower()):
                matched_channel = True
                break

        if not matched_channel:
            return

    stats["messages_scanned"] += 1
    raw_text = event.raw_text or event.message.message or ""
    if not raw_text.strip():
        return

    # Extrai links para checagem de duplicatas
    urls = extract_urls(event.message)

    # Processa pelo motor de filtro
    approved, matched_term, reason = engine.check_message(raw_text, urls)

    chat_title = utils.get_display_name(chat) if chat else "Canal"

    if approved and matched_term:
        stats["promos_found"] += 1
        stats["last_promo_time"] = time.time()
        time_str = datetime.now().strftime("%H:%M:%S")

        print(
            Fore.GREEN + f"[{time_str}] " +
            Fore.YELLOW + f"[MATCH: '{matched_term}'] " +
            Fore.CYAN + f"Canal: '{chat_title}'" +
            Fore.WHITE + " -> Encaminhando..."
        )

        target_dest = config.target_chat
        if str(target_dest).lower() in ("me", "self", "saved"):
            target_dest = "me"
        elif str(target_dest).lstrip("-").isdigit():
            target_dest = int(target_dest)

        try:
            # Encaminha mensagem original completa mantendo mídia, links e botões
            forwarded = await client.forward_messages(target_dest, event.message)

            if config.add_tag_reply:
                tag_text = (
                    f"🎯 **Promoção Encontrada!**\n"
                    f"🏷️ **Termo correspondente:** `{matched_term}`\n"
                    f"📢 **Canal de origem:** {chat_title}"
                )
                try:
                    target_id = forwarded.id if hasattr(forwarded, "id") else (forwarded[0].id if isinstance(forwarded, list) and len(forwarded) > 0 else None)
                    await client.send_message(target_dest, tag_text, reply_to=target_id)
                except Exception:
                    await client.send_message(target_dest, tag_text)

        except ChatForwardsRestrictedError:
            # Fallback para canais que bloqueiam encaminhamento nativo
            fallback_msg = (
                f"🎯 **Promoção Encontrada!**\n"
                f"🏷️ **Termo:** `{matched_term}`\n"
                f"📢 **Canal:** {chat_title} _(encaminhamento restrito)_\n\n"
                f"{raw_text}"
            )
            if urls:
                fallback_msg += "\n\n🔗 **Links:**\n" + "\n".join(urls)
            try:
                await client.send_message(target_dest, fallback_msg)
            except Exception as send_err:
                print(Fore.RED + f"[ERRO AO ENVIAR FALLBACK] {send_err}")

        except Exception as e:
            print(Fore.RED + f"[ERRO AO ENCAMINHAR] {e}")


def print_banner(me):
    print(Fore.CYAN + "=" * 60)
    print(Fore.GREEN + Style.BRIGHT + "   ⚡ BOT DE FILTRO DE PROMOÇÕES TELEGRAM ATIVO ⚡   ")
    print(Fore.CYAN + "=" * 60)
    print(Fore.YELLOW + f"👤 Conectado como: " + Fore.WHITE + f"{me.first_name} (@{me.username or 'sem username'}) [ID: {me.id}]")
    dest_label = "me (Mensagens Salvas)" if str(config.target_chat).lower() == "me" else str(config.target_chat)
    print(Fore.YELLOW + f"🎯 Destino dos alertas: " + Fore.WHITE + dest_label)
    print(Fore.YELLOW + f"🔍 Palavras-chave ({len(config.keywords)}): " + Fore.WHITE + f"{', '.join(config.keywords[:6])}{'...' if len(config.keywords) > 6 else ''}")
    print(Fore.YELLOW + f"🚫 Bloqueadas ({len(config.negative_keywords)}): " + Fore.WHITE + f"{', '.join(config.negative_keywords[:5])}{'...' if len(config.negative_keywords) > 5 else ''}")
    print(Fore.YELLOW + f"📡 Modo: " + Fore.WHITE + ("TODOS os canais da conta" if config.monitor_all else f"{len(config.channels)} canais específicos"))
    print(Fore.YELLOW + f"⏳ Cooldown de duplicatas: " + Fore.WHITE + f"{config.cooldown_minutes} minutos")
    print(Fore.CYAN + "-" * 60)
    print(Fore.MAGENTA + "💡 DICA: Envie /ajuda nas suas 'Mensagens Salvas' no Telegram")
    print(Fore.MAGENTA + "   para adicionar palavras, listar ou alterar canais em tempo real!")
    print(Fore.CYAN + "=" * 60)
    print(Fore.GREEN + "Aguardando novas promoções nos canais...\n")


async def main():
    await client.connect()
    if not await client.is_user_authorized():
        print(Fore.CYAN + "=" * 60)
        print(Fore.GREEN + Style.BRIGHT + "       PRIMEIRO ACESSO - CONEXÃO COM TELEGRAM")
        print(Fore.CYAN + "=" * 60)
        print(Fore.YELLOW + "Para que o bot possa ler os canais da sua conta,")
        print(Fore.YELLOW + "informe o número do seu celular com o código do país.")
        print(Fore.WHITE + "Exemplo no Brasil: +5511999999999\n")

    phone_cb = PHONE.strip() if (PHONE and PHONE.strip()) else lambda: input(Fore.YELLOW + "Digite seu telefone com DDD (ex: +5511999999999): " + Fore.WHITE).strip()
    code_cb = lambda: input(Fore.YELLOW + "Digite o código de verificação recebido no seu Telegram: " + Fore.WHITE).strip()
    pwd_cb = lambda: getpass.getpass(Fore.YELLOW + "Digite sua senha de duas etapas (2FA se houver): " + Fore.WHITE)

    await client.start(
        phone=phone_cb,
        code_callback=code_cb,
        password=pwd_cb
    )

    me = await client.get_me()
    # Carrega diálogos recentes no cache da sessão para garantir resolução de IDs de grupos/canais privados
    await client.get_dialogs(limit=50)
    print_banner(me)
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n[INFO] Bot encerrado pelo usuário.")
    except Exception as e:
        print(Fore.RED + f"\n[ERRO INESPERADO] {e}")

