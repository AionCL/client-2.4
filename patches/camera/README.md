# Camera patch

Status (2026-09-20): the ShugoConsole binaries below are historical experimental
payloads, with reported x86/x64 client crashes. Their camera behavior is NOT
validated. Do not treat this directory as a stable release. Current read-only
diagnostics and recovery procedure: [diagnostic](diagnostic/README.md).
Verified progress and remaining gates: [worklog](WORKLOG.md).

This patch installs the x64 `version.dll` built from ShugoConsoleDll. The launcher writes `%APPDATA%\\ShugoConsole\\config.toml` before starting Aion:

```toml
g_minFov = 80
g_camMax = 30
```

The intended behavior is to apply these values to the CryEngine CVars. Values are constrained by the launcher to FOV 60–170 and camera distance 5–50; this does not establish that the current DLL is safe or compatible with this client.
