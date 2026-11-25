# Application integration

> Status: planned for Phase 2. Nothing in this document has been applied to the Funeral Back Office System yet.

## Integration contract

Every monitored application should expose these endpoints:

| Endpoint | Purpose | Healthy | Unhealthy |
|---|---|---|---|
| `/health/live/` | The process responds | 200 with JSON `{"status":"ok"}` | No response |
| `/health/ready/` | Required dependencies, such as the database, are available | 200 with JSON | 503 with JSON naming the failed check, with no error details |
| `/metrics` | Prometheus metrics (django-prometheus) | 200 text format | Not applicable |

## Reaching an application on the Windows host from Docker

- Inside a container, `localhost` is the container itself, not Windows.
- Both Prometheus and Uptime Kuma have `host.docker.internal:host-gateway` set in `extra_hosts`. With Docker Desktop, `host.docker.internal` resolves to the Windows host.
- Docker Desktop forwards `host.docker.internal` traffic to services on the host's loopback interface. If Django is bound only to `127.0.0.1:8000`, it is usually reachable without exposing it to the LAN. This must be verified in Phase 2. If it does not work, bind to a specific interface, never to `0.0.0.0` on an untrusted network.
- `ALLOWED_HOSTS` must include `host.docker.internal`.
- If a Windows Firewall rule is ever needed, scope it to the Docker/WSL virtual adapter subnet only.

## Prometheus target, added in Phase 2

```yaml
- job_name: funeral-back-office
  metrics_path: /metrics
  static_configs:
    - targets: ["host.docker.internal:8000"]
      labels:
        application: funeral-back-office
        environment: development
```

Every target must carry `application` and `environment` labels. Dashboards and alerts filter on them.

## Privacy rules for instrumentation

- Use django-prometheus's view-name labels, not raw URL paths, so case identifiers never become label values.
- Never put names, ID numbers or other personal data in labels.
- Restrict `/metrics` to monitoring hosts.
- Do not capture request bodies.
