# Improvement scope

Future work, not implemented yet.

## Factory and backend network separation

Real robots may run on a restricted factory network, separate from the
backend. A local Mosquitto broker could forward telemetry through an approved
network boundary to the backend broker, without giving robots direct access
to the API or database.

- Simulate separate networks: factory-side simulator and broker; backend in K3s.
- Bridge only telemetry, using TLS and dedicated credentials. No robot commands.
- Test bounded buffering and recovery during outages, and show stale telemetry.

This is a network-separation demo, not a production OT security design.
Real deployment needs approved firewall and industrial DMZ rules; TLS alone
does not provide isolation. Fully air-gapped networks need a separate,
approved export mechanism.
