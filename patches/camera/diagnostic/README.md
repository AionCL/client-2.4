# Read-only camera diagnostic

Experimental, not an installable camera patch. The existing Shugo binaries are
not validated for this client. No launcher or update manifest uses this diagnostic.

Build on the canonical Linux VM with MinGW (replace the compiler for x64):

```sh
i686-w64-mingw32-g++-posix -std=c++17 -O2 -Wall -Wextra -Werror \
  -static-libgcc -static-libstdc++ -shared version.cpp version.def -o /tmp/camera32.dll
i686-w64-mingw32-g++-posix -O2 -Wall -Wextra -Werror \
  -static-libgcc -static-libstdc++ selftest.cpp -o /tmp/selftest32.exe
file /tmp/camera32.dll
objdump -p /tmp/camera32.dll
```

The DLL forwards all 16 exports and their ordinals to `aioncl_original.dll`, a
temporary byte-for-byte copy of the client's original DLL. It performs no hooks,
Shugo initialization, or game-memory writes. MinGW startup code may import
VirtualProtect for its own relocations; the scanner does not call it.

A worker starts after DllMain returns, pins the diagnostic module, and records
three bounded scans. Only VirtualQuery and ReadProcessMemory access inspected
memory. Guard/uncommitted/no-access pages, the scanner image and its worker stack
are excluded. Read failures are counted; the first 16 per pass are logged.
Blocks are 64 KiB with overlap, scans have 8-second deadlines, and hit/reference
counts are capped. Region boundaries are never crossed by a read. A string split
across two VirtualQuery regions is not detected. A timeout or hit cap means the
scan is incomplete, never proof of absence.

Logs contain target-name addresses, pointer references, and plausible numeric
fields near candidates with a validated executable-image vtable. No command
lines, arbitrary strings, or raw process dumps are logged. A candidate is NOT
proof of CVar identity or of safe write offsets.

Run selftest in a scratch Windows folder with a same-architecture original DLL
named `aioncl_original.dll`. Verify its log detects both printed fixture addresses
and ends with complete=1; the fixture must remain unchanged and its guard intact.

`Test-Startup.ps1` explicitly selects bin32 or bin64, refuses an already running
Aion or mismatched originals, checks PE machine type, starts a restoration
watchdog, and restores originals in finally with SHA256 verification. It stops
only Aion processes at the test path started after the test began. Each run needs
a new state JSON path. Logs remain beside the client DLL for collection. The
watchdog is a separate process; machine shutdown or termination of both test and
watchdog still requires running restoration from the saved state before reuse.

`-Baseline` runs the original client without installing a diagnostic. Restoration
retries transient file sharing violations for up to 30 seconds. To test on the
active desktop from SSH, use `Invoke-InteractiveTest.ps1` with a new RunDirectory.
It registers a temporary InteractiveToken scheduled task, never supplies a
password, captures results, and removes the completed task. Baseline and diagnostic
runs must use the same desktop/session and arguments for a meaningful comparison.

No credentials are required: startup uses only `-DEVMODE`. A surviving process
under SSH proves neither an interactive login nor an in-game camera effect.

API lifecycle reference: https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain
