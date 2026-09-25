# Run on K3s

These manifests run Mosquitto, PostgreSQL, the telemetry API, and one simulator
in the `fleet` namespace. Only the dashboard/API is exposed through Traefik;
MQTT and PostgreSQL stay inside the cluster.

## Secrets

From the repository root:

```bash
bash scripts/setup-local-secrets.sh
```

This needs OpenSSL and Docker. It creates the MQTT CA and broker certificate,
separate passwords for the simulator and API, and a PostgreSQL password under
`k8s/base/secrets/`. Git ignores the generated files. Running it again does
not replace existing credentials.

Keep a private backup of `k8s/base/secrets/mqtt-ca.key`. Kustomize reads the
generated `.env` files and creates Kubernetes Secrets when you run
`kubectl apply -k k8s/base`; the files themselves are not committed. Docker
Compose uses the same MQTT files but keeps its existing local PostgreSQL
password.

The broker certificate lasts one year. If robots will connect through an
external hostname, add that name to `k8s/base/mqtt-server.ext` before issuing
the certificate. The setup script does not rotate certificates or passwords.

## Local cluster on macOS

K3s runs on Linux; `k3d` runs it in Docker on a Mac. With Docker Desktop,
`k3d`, and `kubectl` installed, create the cluster once:

```bash
k3d cluster create k3s-fleet-cluster --agents 0 \
  --port '127.0.0.1:8080:80@loadbalancer'
```

Build the two project images, import them into k3d, and apply the manifests:

```bash
docker build -t telemetry-api:latest services/telemetry-api
docker build -t device-sim:latest services/device-sim
k3d image import telemetry-api:latest device-sim:latest -c k3s-fleet-cluster
kubectl --context k3d-k3s-fleet-cluster apply -k k8s/base
kubectl --context k3d-k3s-fleet-cluster -n fleet get pods
```

The dashboard is at [http://localhost:8080](http://localhost:8080). After
changing application code, rebuild and import its image again, then restart
that Deployment so the pods pick up the new image.

To pause the cluster, run `k3d cluster stop k3s-fleet-cluster`. Start it again
with `k3d cluster start k3s-fleet-cluster`.

## Use the published images

After tests pass on `main`, CI publishes `ghcr.io/silentli/telemetry-api` and
`ghcr.io/silentli/device-sim` with full commit-SHA and `latest` tags. The
`k8s/overlays/ghcr` overlay uses the SHA tags; the base keeps the locally built
images for the k3d steps above.

Before deploying a newer version, change the tag for each image in
`k8s/overlays/ghcr/kustomization.yaml` to the SHA of its last successful
publishing run. The SHAs can differ because CI only publishes a service when
that service or its workflow changes. Then apply the overlay:

```bash
kubectl --context k3d-k3s-fleet-cluster apply -k k8s/overlays/ghcr
kubectl --context k3d-k3s-fleet-cluster -n fleet rollout status deployment/device-sim
kubectl --context k3d-k3s-fleet-cluster -n fleet rollout status deployment/telemetry-api
```

The images must be pullable by the cluster. If the GHCR packages are private,
make them public or configure image pull credentials. On a separate K3s
machine, also change the `localhost` hostname in `k8s/base/ingress.yaml` to
one that points to your cluster and use its kubectl context instead of the
k3d context above.

The generated files and Kubernetes Secrets are a simple setup for this demo,
not a complete production secret-management plan. In particular, do not
expose MQTT to external robots until its certificate covers their broker
hostname and you have decided how those robots will reach the broker.

The broker's `mosquitto.acl` lets `robot-sim` publish to `factory/telemetry`
and `telemetry-api` subscribe to it. Neither account is a broker administrator.
