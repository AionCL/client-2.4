# Camera patch

This patch installs the x64 `version.dll` built from ShugoConsoleDll. The launcher writes `%APPDATA%\\ShugoConsole\\config.toml` before starting Aion:

```toml
g_minFov = 80
g_camMax = 30
```

The DLL reads these values at runtime and applies them to the CryEngine CVars. Values are constrained by the launcher to FOV 60–170 and camera distance 5–50.
