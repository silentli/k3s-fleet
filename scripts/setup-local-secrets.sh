#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secrets_dir="$repo_dir/k8s/base/secrets"

mqtt_files=(
  mqtt-ca.key
  mqtt-ca.crt
  mqtt-server.key
  mqtt-server.crt
  mqtt-passwordfile
  device-sim-mqtt.env
  telemetry-api-mqtt.env
)

existing_mqtt=0
for name in "${mqtt_files[@]}"; do
  if [[ -e "$secrets_dir/$name" ]]; then
    if [[ ! -s "$secrets_dir/$name" ]]; then
      echo "$name is empty; refusing to replace it." >&2
      exit 1
    fi
    ((existing_mqtt += 1))
  fi
done

if ((existing_mqtt > 0 && existing_mqtt < ${#mqtt_files[@]})); then
  echo "MQTT secrets are incomplete in $secrets_dir; refusing to overwrite them." >&2
  echo "Restore the missing files from your private backup before retrying." >&2
  exit 1
fi

if [[ -e "$secrets_dir/postgres.env" && ! -s "$secrets_dir/postgres.env" ]]; then
  echo "postgres.env is empty; refusing to replace it." >&2
  exit 1
fi

for name in device-sim-mqtt.env telemetry-api-mqtt.env postgres.env; do
  if [[ -e "$secrets_dir/$name" ]] && grep -q 'replace-with-' "$secrets_dir/$name"; then
    echo "$name still contains an example password; refusing to use it." >&2
    exit 1
  fi
done

if ((existing_mqtt == ${#mqtt_files[@]})) && [[ -s "$secrets_dir/postgres.env" ]]; then
  echo "Secrets already exist; nothing changed."
  exit 0
fi

command -v openssl >/dev/null || { echo "OpenSSL is required." >&2; exit 1; }
if ((existing_mqtt == 0)); then
  command -v docker >/dev/null || { echo "Docker is required for mosquitto_passwd." >&2; exit 1; }
fi

mkdir -p "$secrets_dir"
chmod 700 "$secrets_dir"
stage_dir="$(mktemp -d "$secrets_dir/.setup.XXXXXX")"
trap 'rm -r -- "$stage_dir"' EXIT

if ((existing_mqtt == 0)); then
  robot_password="$(openssl rand -hex 24)"
  api_password="$(openssl rand -hex 24)"

  openssl req -x509 -newkey rsa:3072 -sha256 -days 3650 -nodes \
    -keyout "$stage_dir/mqtt-ca.key" -out "$stage_dir/mqtt-ca.crt" \
    -subj "/CN=Fleet MQTT CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
  openssl req -newkey rsa:2048 -sha256 -nodes \
    -keyout "$stage_dir/mqtt-server.key" -out "$stage_dir/mqtt-server.csr" \
    -subj "/CN=mosquitto"
  openssl x509 -req -in "$stage_dir/mqtt-server.csr" \
    -CA "$stage_dir/mqtt-ca.crt" -CAkey "$stage_dir/mqtt-ca.key" \
    -CAcreateserial -out "$stage_dir/mqtt-server.crt" -days 365 -sha256 \
    -extfile "$repo_dir/k8s/base/mqtt-server.ext"
  openssl verify -CAfile "$stage_dir/mqtt-ca.crt" "$stage_dir/mqtt-server.crt"

  # -U hashes this new plaintext file once; never run it on an existing hash file.
  printf 'robot-sim:%s\ntelemetry-api:%s\n' "$robot_password" "$api_password" \
    > "$stage_dir/mqtt-passwordfile"
  docker run --rm --user "$(id -u):$(id -g)" \
    -v "$stage_dir:/work" eclipse-mosquitto:2.0.18 \
    mosquitto_passwd -U /work/mqtt-passwordfile

  printf 'MQTT_USERNAME=robot-sim\nMQTT_PASSWORD=%s\n' "$robot_password" \
    > "$stage_dir/device-sim-mqtt.env"
  printf 'MQTT_USERNAME=telemetry-api\nMQTT_PASSWORD=%s\n' "$api_password" \
    > "$stage_dir/telemetry-api-mqtt.env"

  chmod 600 "$stage_dir/mqtt-ca.key" "$stage_dir/device-sim-mqtt.env" \
    "$stage_dir/telemetry-api-mqtt.env"
  # Compose runs Mosquitto as a non-root user. The enclosing directory is 700.
  chmod 644 "$stage_dir/mqtt-ca.crt" "$stage_dir/mqtt-server.crt" \
    "$stage_dir/mqtt-server.key" "$stage_dir/mqtt-passwordfile"

  for name in "${mqtt_files[@]}"; do
    mv "$stage_dir/$name" "$secrets_dir/$name"
  done
  echo "Created MQTT CA, broker certificate, and two client credentials."
fi

if [[ ! -e "$secrets_dir/postgres.env" ]]; then
  postgres_password="$(openssl rand -hex 24)"
  printf 'POSTGRES_PASSWORD=%s\nDATABASE_URL=postgresql+psycopg://fleet:%s@postgres:5432/fleet\n' \
    "$postgres_password" "$postgres_password" > "$stage_dir/postgres.env"
  chmod 600 "$stage_dir/postgres.env"
  mv "$stage_dir/postgres.env" "$secrets_dir/postgres.env"
  echo "Created PostgreSQL credentials."
fi

echo "Private files are in $secrets_dir (ignored by Git). Back up mqtt-ca.key privately."
