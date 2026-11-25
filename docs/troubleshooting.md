# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `start.ps1` reports that a port is in use | Another process is listening on 3000, 3001 or 9090 | Find the process with `Get-NetTCPConnection -LocalPort 3000 -State Listen`, then change the port in `.env` or stop that process. |
| Compose error `GRAFANA_ADMIN_PASSWORD must be set` | `.env` is missing or incomplete | Copy `.env.example` to `.env` and set the values. |
| Scripts blocked by the execution policy | Windows policy | Run `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1`. |
| Grafana shows no data | Prometheus is unhealthy or the data source is wrong | Run `.\scripts\status.ps1`. Check *Connections → Data sources → Prometheus → Test*. |
| A container restarts repeatedly | Bad configuration or a memory limit was hit | Run `docker compose logs <service>` and `docker inspect <service> --format '{{.State.OOMKilled}}'`. |
| A Prometheus config change has no effect | It has not been reloaded | Run `.\scripts\validate.ps1`, then `Invoke-RestMethod -Method Post http://127.0.0.1:9090/-/reload`. |
| A target on the host is `down` with "connection refused" | The app isn't running, or it is unreachable from the container | Check the app is running. From a container, run `docker exec prometheus wget -qO- http://host.docker.internal:8000/health/live/`. |
| Docker Desktop is slow or the host is low on memory | The host has too little free RAM | Close unused applications. You can also cap WSL2 memory in `%UserProfile%\.wslconfig`. |
