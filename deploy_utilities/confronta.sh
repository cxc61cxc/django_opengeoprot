#!/bin/bash

# Uso: ./confronta.sh file_locale utente@host:/percorso/file_remoto

if [ "$#" -ne 1 ]; then
  #echo "Uso: $0 <file_locale> <utente@host:/percorso/remoto>"
  echo "Uso: $0 <file_locale> (path relativo a code/)"
  exit 1
fi

FILE_LOCALE="$1"

REMOTE_HOST="lodoli@docker"

REMOTE_ROOT="/var/www/sisric/"

REMOTE_SPEC="$2"

# Estrai host e percorso remoto
#REMOTE_HOST="${REMOTE_SPEC%%:*}"
#REMOTE_PATH="${REMOTE_SPEC#*:}"
REMOTE_PATH="$REMOTE_ROOT$FILE_LOCALE"

# Verifica se il file locale esiste
if [ ! -f "code/$FILE_LOCALE" ]; then
  echo "File locale non trovato: $FILE_LOCALE"
  exit 2
fi
echo "File locale trovato: $FILE_LOCALE"
echo "Percorso remoto: $REMOTE_PATH"

# Confronta i due file
#diff "code/$FILE_LOCALE" <(ssh "$REMOTE_HOST" "cat '$REMOTE_PATH'") || echo "Differenze trovate"

echo "diff $REMOTE_PATH $FILE_LOCALE"
echo " < linee file remoto"
echo " > linee file licale"

# affiancatto
diff -y <(ssh "$REMOTE_HOST" "cat '$REMOTE_PATH'") "code/$FILE_LOCALE" || echo "Differenze trovate"
# echo
# echo
# unified for patch
# diff -u <(ssh "$REMOTE_HOST" "cat '$REMOTE_PATH'") "code/$FILE_LOCALE" || echo "Differenze trovate"
