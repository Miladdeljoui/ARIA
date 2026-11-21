from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
BOT = ROOT / "bot.py"
DOCKERFILE = ROOT / "Dockerfile"

bot = BOT.read_text()
docker = DOCKERFILE.read_text()

import_line = "from billing_handlers import register_billing_handlers"
if import_line not in bot and "import httpx\n" not in bot:
    raise SystemExit("BOT_IMPORT_ANCHOR_NOT_FOUND")

register_line = "    register_billing_handlers(app)"
if register_line not in bot and "    app = Application.builder().token(BOT_TOKEN).build()\n" not in bot:
    raise SystemExit("BOT_APPLICATION_ANCHOR_NOT_FOUND")

docker_line = "COPY billing.py billing_handlers.py ./"
if docker_line not in docker and "COPY bot.py ." not in docker:
    raise SystemExit("DOCKERFILE_COPY_ANCHOR_NOT_FOUND")

new_bot = bot
if import_line not in new_bot:
    new_bot = new_bot.replace("import httpx\n", "import httpx\n" + import_line + "\n", 1)
if register_line not in new_bot:
    anchor = "    app = Application.builder().token(BOT_TOKEN).build()\n"
    new_bot = new_bot.replace(anchor, anchor + register_line + "\n", 1)

new_docker = docker
if docker_line not in new_docker:
    new_docker = new_docker.replace(
        "COPY bot.py .",
        "COPY bot.py .\n" + docker_line,
        1,
    )

compile(new_bot, str(BOT), "exec")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(BOT, ROOT / f"bot.py.before-billing-{stamp}")
shutil.copy2(DOCKERFILE, ROOT / f"Dockerfile.before-billing-{stamp}")
BOT.write_text(new_bot)
DOCKERFILE.write_text(new_docker)

print("BILLING_INTEGRATION_PATCHED")
print("Syntax check: OK")
print("Backup files created.")
print("No container was restarted.")
