"""
GitHub Actions — Posta no Instagram no horario agendado
Roda nos servidores do GitHub. PC pode estar desligado.
"""
import os, json, requests, time, sys
from datetime import datetime, timezone, timedelta

IG_TOKEN = os.environ["META_INSTAGRAM_TOKEN"]
IG_ID    = os.environ["META_INSTAGRAM_ACCOUNT_ID"]
REPO     = "merkkavaapp-source/marketing-assets"

# Carrega agenda e legendas direto do repo
def fetch(filename):
    r = requests.get(f"https://raw.githubusercontent.com/{REPO}/main/{filename}")
    r.raise_for_status()
    return r.json()

schedule = fetch("instagram_schedule.json")  # {"11": "2026-04-14T22:00", ...}
legendas = fetch("legendas.json")             # {"11": "caption...", ...}

# Descobre qual post postar agora (tolerancia de 10 minutos)
now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
print(f"Hora atual UTC: {now_utc.strftime('%Y-%m-%dT%H:%M')}")

post_num = None
for num_str, dt_str in schedule.items():
    scheduled = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
    diff = abs((now_utc - scheduled).total_seconds())
    if diff <= 600:  # 10 minutos de tolerancia
        post_num = int(num_str)
        print(f"Post encontrado: Post {post_num} agendado para {dt_str} UTC")
        break

if post_num is None:
    print(f"Nenhum post encontrado para o horario atual ({now_utc.strftime('%Y-%m-%dT%H:%M')} UTC)")
    print("Posts disponíveis:", list(schedule.keys()))
    sys.exit(0)

image_url = f"https://raw.githubusercontent.com/{REPO}/main/post{post_num}_slide_01_capa.png"
caption   = legendas.get(str(post_num), "")

print(f"\nPostando Post {post_num} no Instagram...")
print(f"Imagem: {image_url}")

# Aguarda CDN GitHub
time.sleep(5)

# Cria container
r = requests.post(f"https://graph.instagram.com/v25.0/{IG_ID}/media", data={
    "image_url": image_url,
    "caption": caption,
    "access_token": IG_TOKEN
})
data = r.json()
if "id" not in data:
    print(f"ERRO container: {data}")
    sys.exit(1)

container_id = data["id"]
print(f"Container criado: {container_id}")

# Aguarda processamento (max 90s)
for i in range(18):
    time.sleep(5)
    r2 = requests.get(f"https://graph.instagram.com/v25.0/{container_id}",
                      params={"fields": "status_code", "access_token": IG_TOKEN})
    status = r2.json().get("status_code", "")
    print(f"  Status ({i+1}/18): {status}")
    if status == "FINISHED":
        break
    if status == "ERROR":
        print(f"ERRO processamento: {r2.json()}")
        sys.exit(1)

# Publica
r3 = requests.post(f"https://graph.instagram.com/v25.0/{IG_ID}/media_publish", data={
    "creation_id": container_id,
    "access_token": IG_TOKEN
})
result = r3.json()
if "id" in result:
    print(f"\n✅ Post {post_num} publicado no Instagram! ID: {result['id']}")
else:
    print(f"ERRO publish: {result}")
    sys.exit(1)
