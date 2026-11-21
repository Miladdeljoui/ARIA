from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
BOT = ROOT / "bot.py"
DOCKERFILE = ROOT / "Dockerfile"

for required in ("billing.py", "billing_handlers.py", "clip_service.py"):
    if not (ROOT / required).is_file():
        raise SystemExit(f"REQUIRED_FILE_MISSING: {required}")

bot = BOT.read_text()
docker = DOCKERFILE.read_text()

billing_import = "from billing_handlers import register_billing_handlers"
clip_import = "from clip_service import generate_clip_for_user"
app_anchor = "    app = Application.builder().token(BOT_TOKEN).build()\n"
docker_line = "COPY billing.py billing_handlers.py clip_service.py ./"

if "import httpx\n" not in bot:
    raise SystemExit("BOT_IMPORT_ANCHOR_NOT_FOUND")
if "async def handle_text(" not in bot or "    mode = chat_mode.get(uid)\n" not in bot:
    raise SystemExit("HANDLE_TEXT_ANCHOR_NOT_FOUND")
if app_anchor not in bot and "    register_billing_handlers(app)" not in bot:
    raise SystemExit("BOT_APPLICATION_ANCHOR_NOT_FOUND")
if docker_line not in docker and "COPY billing.py billing_handlers.py ./" not in docker and "COPY bot.py ." not in docker:
    raise SystemExit("DOCKERFILE_COPY_ANCHOR_NOT_FOUND")

new_bot = bot
if billing_import not in new_bot:
    new_bot = new_bot.replace("import httpx\n", "import httpx\n" + billing_import + "\n", 1)
if clip_import not in new_bot:
    new_bot = new_bot.replace(
        billing_import + "\n",
        billing_import + "\n" + clip_import + "\n",
        1,
    )
if "    register_billing_handlers(app)" not in new_bot:
    new_bot = new_bot.replace(app_anchor, app_anchor + "    register_billing_handlers(app)\n", 1)

# Add a clip button to the existing main menu without changing other menu rows.
clip_button = '        [InlineKeyboardButton("🎬 ساخت کلیپ", callback_data="clip_start")],\n'
if clip_button not in new_bot:
    plan_button = '        [InlineKeyboardButton("💎 خرید اشتراک", callback_data="plans")],\n'
    if plan_button not in new_bot:
        raise SystemExit("MAIN_MENU_PLAN_BUTTON_NOT_FOUND")
    new_bot = new_bot.replace(plan_button, clip_button + plan_button, 1)

# Route the next private text message to the quota-protected clip service.
handle_start = new_bot.index("async def handle_text(")
help_start = new_bot.index("async def help_command(", handle_start)
handle_part = new_bot[handle_start:help_start]
clip_route = (
    '    if context.user_data.pop("clip_waiting", False):\n'
    '        await generate_clip_for_user(update, context, update.message.text)\n'
    '        return\n\n'
)
mode_anchor = "    mode = chat_mode.get(uid)\n"
if clip_route.strip() not in handle_part:
    if mode_anchor not in handle_part:
        raise SystemExit("HANDLE_TEXT_MODE_ANCHOR_NOT_FOUND")
    handle_part = handle_part.replace(mode_anchor, clip_route + mode_anchor, 1)
    new_bot = new_bot[:handle_start] + handle_part + new_bot[help_start:]

new_docker = docker
if docker_line not in new_docker:
    old_line = "COPY billing.py billing_handlers.py ./"
    if old_line in new_docker:
        new_docker = new_docker.replace(old_line, docker_line, 1)
    elif "COPY bot.py ." in new_docker:
        new_docker = new_docker.replace("COPY bot.py .", "COPY bot.py .\n" + docker_line, 1)
    else:
        raise SystemExit("DOCKERFILE_COPY_ANCHOR_NOT_FOUND")

compile(new_bot, str(BOT), "exec")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(BOT, ROOT / f"bot.py.before-billing-{stamp}")
shutil.copy2(DOCKERFILE, ROOT / f"Dockerfile.before-billing-{stamp}")
BOT.write_text(new_bot)
DOCKERFILE.write_text(new_docker)

print("BILLING_AND_CLIP_INTEGRATION_PATCHED")
print("Syntax check: OK")
print("Backups created; no container was restarted.")
