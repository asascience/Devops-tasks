#!/bin/bash
URL_FILE="url.txt"
EXPECTED_STATUS=200
EXPECTED_REDIRECT_STATUS=302
EMAIL="pavani.ankam@tetratech.com"
RECIPIENT="pavani.ankam@tetratech.com"
SUBJECT="Alert URL:"
LOGFILE="/home/rpsoilmaphostadmin/monitoring/monitor_url.log"
SMTP_HOST="10.5.12.199"
SMTP_PORT="25"
if ! command -v msmtp &> /dev/null; then
    echo "msmtp is not installed. Installing msmtp..."
    if [ -x "$(command -v apt-get)" ]; then
        sudo apt-get update
        sudo apt-get install -y msmtp
    elif [ -x "$(command -v yum)" ]; then
        sudo yum install -y msmtp
    else
        echo "Package manager not supported. Please install msmtp manually."
        exit 1
    fi
fi
MSMTP_CONFIG_FILE="$HOME/.msmtprc"
cat <<EOL > "$MSMTP_CONFIG_FILE"
account default
host ${SMTP_HOST}
port ${SMTP_PORT}
from $EMAIL
auth off
tls off
logfile $HOME/.msmtp.log
EOL

chmod 600 "$MSMTP_CONFIG_FILE"

send_email() {
    local url=$1
    local status=$2
    SUBJECT="${SUBJECT} ${url} is down"
    local body="The URL $url is down or not returning the expected status code. Status: $status"
    echo -e "Subject:$SUBJECT\n\n$body" | msmtp "$RECIPIENT"
    echo "$(date): $url is down with status $status" >> "$LOGFILE"
}

while IFS= read -r url; do
    if [ -z "$url" ]; then
        continue
    fi
    STATUS=$(curl -o /dev/null -s -w "%{http_code}\n" "$url")
    if [ "$STATUS" -ne "$EXPECTED_STATUS" ] && [ "$STATUS" -ne "$EXPECTED_REDIRECT_STATUS" ]; then
        send_email "$url" "$STATUS"
         echo "URL : ${url} - FAILED $STATUS"
    else
        echo "URL : ${url} - OK"
    fi
done < "$URL_FILE"
