#!/usr/bin/env bash

# =====================
# === RILEVA SHELL ====
# =====================
get_script_source() {
    if [ -n "$BASH_SOURCE" ]; then
        echo "${BASH_SOURCE[0]}"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "${funcfiletrace[1]}"
    else
        echo "$0"
    fi
}

# =========================
# === USCITA SICURA ===
# =========================
safe_exit() {
    local code="$1"
    echo ">>> Exit code: $code" | tee -a "$LOG_FILE"

    # Se sourced, forza uscita completa
    if [[ "${BASH_SOURCE[0]}" != "$0" || "${ZSH_EVAL_CONTEXT}" == *file* ]]; then
        echo "❌ Questo script non può essere eseguito con 'source'. Uscita forzata."
        kill -INT $$
    else
        exit "$code"
    fi
}

# ==========================
# === CONFERMA UTENTE ===
# ==========================
ask_confirmation() {
    local message="$1"
    printf "%s [y/N] " "$message"
    read response
    if [[ "$response" != "y" && "$response" != "Y" ]]; then
        echo ">>> Operazione annullata." | tee -a "$LOG_FILE"
        safe_exit 0
    fi
}

# ======================
# === CONFIGURAZIONE ===
# ======================

ps -p $$ -o args=
BRANCH_NAME='main'
SOURCE_DIR="./code/"
DEST_HOST="lodoli@docker"
ROOT_PATH="/var/www/"
DEST_DIR="sisric/"
BACKUP_DIR="backup/"
DEST_PATH="$ROOT_PATH$DEST_DIR"

EXCLUDE_FILE=".rsync_exclude"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$ROOT_PATH$BACKUP_DIR${DEST_DIR%/}_$TIMESTAMP"

LOG_DIR="./deploy_logs"
LOG_FILE="$LOG_DIR/deploy_$TIMESTAMP.log"
mkdir -p "$LOG_DIR"
echo "Shell corrente: $SHELL" | tee -a "$LOG_FILE"
RSYNC_OPTS=(-avv --itemize-changes --checksum --exclude-from="$EXCLUDE_FILE")

# ==========================
# === VERIFICHE PRELIMINARI
# ==========================
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current_branch" != $BRANCH_NAME ]]; then
    echo "🚫 Branch corrente: '$current_branch'. Il deploy è permesso solo su $BRANCH_NAME." | tee -a "$LOG_FILE"
    safe_exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ La directory sorgente '$SOURCE_DIR' non esiste." | tee -a "$LOG_FILE"
    safe_exit 1
fi

if [ ! -f "$EXCLUDE_FILE" ]; then
    echo "❌ Il file di esclusione '$EXCLUDE_FILE' non esiste." | tee -a "$LOG_FILE"
    ask_confirmation "Vuoi continuare comunque?"
fi

# ======================
# === DUMP PARAMETRI ===
# ======================
{
    echo "=== DEPLOY START: $TIMESTAMP ==="
    echo "Exclude file: $EXCLUDE_FILE"
    cat "$EXCLUDE_FILE"
    echo -e "\n------------------------\n"
    echo "PARAMETRI:"
    echo "Branch: $BRANCH_NAME"
    echo "Current branch: $current_branch"
    echo "Source dir: $SOURCE_DIR"
    echo "Dest host: $DEST_HOST"
    echo "Dest path: $DEST_PATH"
    echo "Backup path: $BACKUP_PATH"
    echo "Rsync options: ${RSYNC_OPTS[*]}"
    echo
} | tee -a "$LOG_FILE"

# =========================
# === DRY RUN ============
# =========================
ask_confirmation "Vuoi continuare con il dry-run di verifica?"
echo ">>> Esecuzione DRY-RUN su host remoto '$DEST_HOST'..." | tee -a "$LOG_FILE"
rsync --dry-run "${RSYNC_OPTS[@]}" "$SOURCE_DIR" "${DEST_HOST}:${DEST_PATH}" | grep '^[<>c]' | tee -a "$LOG_FILE"

# =========================
# === BACKUP ============
# =========================
ask_confirmation "Vuoi procedere con il backup della destinazione?"
echo ">>> Creo backup remoto in: $BACKUP_PATH" | tee -a "$LOG_FILE"
ssh "$DEST_HOST" "cp -r -p \"$DEST_PATH\" \"$BACKUP_PATH\"" | tee -a "$LOG_FILE"
echo "✔️ Backup completato." | tee -a "$LOG_FILE"

# =========================
# === DEPLOY ============
# =========================
ask_confirmation "Vuoi procedere con il deploy effettivo?"
echo ">>> Deploy in corso..." | tee -a "$LOG_FILE"
rsync "${RSYNC_OPTS[@]}" "$SOURCE_DIR" "${DEST_HOST}:${DEST_PATH}" | tee -a "$LOG_FILE"
echo "✅ Deploy completato con successo." | tee -a "$LOG_FILE"
