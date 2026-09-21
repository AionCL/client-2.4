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
four bounded scans (including a late pass after at least 60 seconds). Target names
are matched ignoring ASCII case, with exact_case reported separately.
Only VirtualQuery and ReadProcessMemory access inspected
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

Place reviewed launcher.json and server-config.json copies beside the test script.
No credentials are required: startup uses the launcher's configured arguments and
resolves the configured login host to IPv4. A surviving process
under SSH proves neither an interactive login nor an in-game camera effect.

API lifecycle reference: https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain

## Separate patch prototype

Compile with `-DAIONCL_CAMERA_PATCH` to produce a different, opt-in test DLL. The
plain diagnostic build still has no game-memory writes. Patch tests additionally
require `-CameraPatch` in the PowerShell harness, which sets a child-only opt-in
environment variable and snapshots/restores system.cfg as well as the original DLL.

This prototype targets only the verified CrySystem CVar layout and getter byte
signatures, exact names, internal self-pointers, type 3, and a unique object per
name. It refuses incomplete scans, inconsistent numeric representations, changing
values, and unsupported layouts. It writes only the 40-byte int/float/numeric-text
area of each CVar: FOV 80, distance 30. It verifies writes and ten seconds of
readback, then restores the original bytes after rechecking identity. It never
changes page protection or engine code, and never calls an unverified function.

This proves storage updates only; it is NOT proof of an in-game camera effect or
production stability. No launcher integration or update-feed publication yet.

Native value-validation tests:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined \
  test-camera-values.cpp -o /tmp/camera-values-test
ASAN_OPTIONS=detect_leaks=0 /tmp/camera-values-test
```

Leak detection is disabled under the VM sandbox's ptrace environment; ASan/UBSan
memory and undefined-behavior checks remain enabled.

## In-game recipe

`Invoke-InteractiveTest.ps1 -ManualCamera -StartOnly` starts a detached interactive
test, saving task identity to RunDirectory/task.json. The worker waits up to 30
minutes for `bin64/aioncl-camera-PID.apply` (or bin32). Create this empty signal
only once the user is in game. The scanner discovers and validates the CVars again
before applying 80/30. This in-game rescan allows 30 seconds for the larger loaded
world; startup scans keep their 8-second deadlines. Incomplete scans still refuse
all writes. It then holds for up to 30 minutes, with continuous readback.
Creating `aioncl-camera-PID.restore` requests immediate rollback and ends the test.
Signals are consumed automatically. Normal game exit also lets the controller
restore the original DLL and system.cfg; the temporary scheduled task removes
itself. No login credentials are supplied, inspected, or saved by these tools.

`manual_ready` means no camera change has been made yet; `manual_applied` confirms
the requested values were written and read back. Visual validation is still the
user's responsibility. All statements of stability must distinguish these stages.
