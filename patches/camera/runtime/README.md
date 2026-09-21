# Camera helper (x64 preview)

Build on the canonical VM with MinGW:

```sh
x86_64-w64-mingw32-g++-posix -std=c++17 -O2 -Wall -Wextra -Werror \
  -Wno-unused-function -static -municode patches/camera/runtime/main.cpp \
  -o /tmp/AionCL.Camera.exe
```

Package as `tools/AionCL.Camera.exe` using `tools/package-camera.py`. This appends
one archive to the existing manifest; base archives, URLs and hashes are retained.
The launcher verifies its manifest hash before starting the helper with only
game PID, integer FOV (60-170) and maximum distance (5-100). No credentials.

This helper never replaces version.dll. It controls only the matching installation's
bin64/aionclassic.bin. A per-process mutex prevents duplicate controllers. Startup
discovery is bounded; exact CVar layout, self pointers and CrySystem getter bytes
must match. Invalid identities stop all further writes. The worker exits with the
game. Preferences are applied at the next launch; disable in launcher to leave
the game unmanaged. x86 support is not exposed by this runtime.

External transport needs its own in-game and zone-transition recipe. The earlier
DLL recipe proves camera effects but does not qualify every external-runtime path.
