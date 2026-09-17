#!/usr/bin/env python3
"""
NovaMart - Pipeline Orchestrator
===================================
Roda em sequência, disparado pelo cron:
  1. Ingestão de dados sintéticos (continuous_ingestion.py)
  2. dbt build (staging -> intermediate -> marts), parando na primeira
     camada que falhar (não faz sentido construir marts em cima de
     staging quebrado)
  3. dbt docs generate (só roda se tudo acima passou)
E manda um alerta no Discord ao final com duração total, status de
cada etapa e, se algo falhou, o log de debug (com o arquivo completo
anexado).

Uso (chamado pelo cron, sem argumentos):
    /home/ubuntu/novamart/venv/bin/python3 run_pipeline.py

Uso manual com full refresh (roda os dbt build com --full-refresh):
    /home/ubuntu/novamart/venv/bin/python3 run_pipeline.py --full-refresh
"""

import argparse
import json
import os
import subprocess
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (mesma pasta do script, por padrão).
# O .env NUNCA vai para o repositório — veja a nota de setup abaixo.
load_dotenv()

# ---------------------------------------------------------------------------
# Configuração — ajuste os caminhos abaixo se algo estiver diferente no seu setup
# ---------------------------------------------------------------------------
VENV_PYTHON = "/home/ubuntu/novamart/venv/bin/python3"
DBT_BIN = "/home/ubuntu/novamart/venv/bin/dbt"
DBT_PROJECT_DIR = "/home/ubuntu/novamart/novamart_analytics"
INGESTION_SCRIPT = "/home/ubuntu/novamart/scripts/continuous_ingestion.py"
LOG_DIR = "/home/ubuntu/novamart/logs"

# Lido do .env (chave DISCORD_WEBHOOK_URL) — nunca hardcoded no .py, já que
# um webhook é, na prática, uma credencial: quem tiver a URL consegue postar
# no seu canal do Discord.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

os.makedirs(LOG_DIR, exist_ok=True)


def run_cmd(cmd, cwd=None):
    """Roda um comando, captura stdout/stderr e duração."""
    start = time.time()
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    duration = time.time() - start
    return result.returncode, result.stdout, result.stderr, duration


def parse_dbt_failures(project_dir):
    """Lê target/run_results.json e retorna uma lista com cada nó que falhou
    (modelo ou teste) e a mensagem de erro/detalhe da falha."""
    path = os.path.join(project_dir, "target", "run_results.json")
    failures = []
    if not os.path.exists(path):
        return failures
    try:
        with open(path) as f:
            data = json.load(f)
        for result in data.get("results", []):
            if result.get("status") in ("error", "fail"):
                node = result.get("unique_id", "desconhecido")
                message = (result.get("message") or "").strip()
                failures.append(f"{node}: {message}")
    except Exception as e:
        failures.append(f"[não foi possível ler run_results.json: {e}]")
    return failures


def send_discord_alert(status, total_duration, stages, log_path):
    """Envia um embed para o Discord. Se falhou, anexa o log completo."""
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] DISCORD_WEBHOOK_URL não configurado (verifique o .env) — alerta não enviado.")
        return

    color = 3066993 if status == "success" else 15158332  # verde / vermelho
    emoji_map = {"ok": "✅", "erro": "❌", "pulado": "⏭️"}

    fields = []
    for name, stage_status, dur, detail in stages:
        value = f"{emoji_map[stage_status]} {dur:.1f}s"
        if detail:
            trimmed = detail[:900]
            if len(detail) > 900:
                trimmed += "\n... (log completo no arquivo anexado)"
            value += f"\n```{trimmed}```"
        fields.append({"name": name, "value": value, "inline": False})

    embed = {
        "title": "Pipeline NovaMart — " + ("Sucesso ✅" if status == "success" else "Falhou ❌"),
        "description": f"Duração total: **{total_duration:.1f}s**",
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat(),
    }
    payload = {"embeds": [embed]}

    try:
        if status != "success" and log_path and os.path.exists(log_path):
            with open(log_path, "rb") as f:
                requests.post(
                    DISCORD_WEBHOOK_URL,
                    data={"payload_json": json.dumps(payload)},
                    files={"file": (os.path.basename(log_path), f)},
                    timeout=15,
                )
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    except Exception as e:
        print(f"[WARN] Falha ao enviar alerta ao Discord: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="NovaMart Pipeline Orchestrator")
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Roda os dbt build com --full-refresh (reconstrói modelos incrementais do zero).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOG_DIR, f"pipeline_{run_id}.log")
    log_lines = []
    stages = []  # (nome, status "ok"/"erro"/"pulado", duração, detalhe do erro)
    pipeline_start = time.time()
    overall_status = "success"

    def log(msg):
        if msg:
            print(msg)
            log_lines.append(str(msg))

    # 1) Ingestão -------------------------------------------------------
    log(f"[{datetime.now()}] Iniciando ingestão...")
    rc, out, err, dur = run_cmd([VENV_PYTHON, INGESTION_SCRIPT, "--orders", "5"])
    log(out)
    log(err)
    if rc != 0:
        stages.append(("Ingestão", "erro", dur, err or out))
        overall_status = "failure"
    else:
        stages.append(("Ingestão", "ok", dur, None))

    # 2) dbt build por camada, para na primeira que falhar ---------------
    layers = [
        ("dbt build (staging)", "path:models/stg"),
        ("dbt build (intermediate)", "path:models/int"),
        ("dbt build (marts)", "path:models/marts"),
    ]

    for name, select in layers:
        if overall_status == "failure":
            stages.append((name, "pulado", 0, None))
            continue

        cmd = [DBT_BIN, "build", "--select", select]
        if args.full_refresh:
            cmd.append("--full-refresh")

        log(f"[{datetime.now()}] Rodando {name} ({' '.join(cmd[1:])}) ...")
        rc, out, err, dur = run_cmd(cmd, cwd=DBT_PROJECT_DIR)
        log(out)
        log(err)

        if rc != 0:
            failures = parse_dbt_failures(DBT_PROJECT_DIR)
            detail = "\n".join(failures) if failures else (err or out)
            stages.append((name, "erro", dur, detail))
            overall_status = "failure"
        else:
            stages.append((name, "ok", dur, None))

    # 3) dbt docs generate — só roda se tudo passou -----------------------
    if overall_status == "success":
        log(f"[{datetime.now()}] Rodando dbt docs generate ...")
        rc, out, err, dur = run_cmd([DBT_BIN, "docs", "generate"], cwd=DBT_PROJECT_DIR)
        log(out)
        log(err)
        stages.append(("dbt docs generate", "ok" if rc == 0 else "erro", dur, None if rc == 0 else (err or out)))
        if rc != 0:
            overall_status = "failure"
    else:
        stages.append(("dbt docs generate", "pulado", 0, None))

    total_duration = time.time() - pipeline_start

    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))

    log(f"[{datetime.now()}] Pipeline finalizado: {overall_status} em {total_duration:.1f}s")
    send_discord_alert(overall_status, total_duration, stages, log_path if overall_status == "failure" else None)


if __name__ == "__main__":
    main()
