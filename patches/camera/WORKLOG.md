# Camera diagnostic worklog

## 2026-09-20 - Recovery

### Verified

- Client and launcher working trees are clean at initial inspection.
- Incoming ShugoConsoleDll working tree is clean (master); use a per-command
  safe.directory override because the extracted repository has another owner.
- Its version.cpp is the upstream implementation, including Shugo initialization
  inside DllMain. Do not deploy it as a validated camera patch.
- Existing camera README describes functionality that is NOT validated by this
  recovery. User reports x86/x64 crashes in VERSION.dll (0xc0000005).
- No dedicated camera worklog found in inspected repositories. This file is the
  persistent action and recovery journal from this point forward.

### In progress

- Verify Windows SSH tunnel at local port 2222. System SSH configuration has a
  permissions error; use -F /var/lib/codex/.ssh/config. Network needs execution
  outside the sandbox. Initial connection then failed host-key verification.
- Back up VM and Windows Shugo sources before changing diagnostic code.
- Restore a clean version.cpp in the working copy, then implement a bounded,
  read-only diagnostic using VirtualQuery and ReadProcessMemory.

### Required remaining gates

1. Build x86 and verify PE32, exports, imports and absence of memory writes.
2. Commit and push source before Windows testing.
3. Test explicitly with bin32/aionclassic.bin, guaranteed automatic restoration
   of original version.dll, and collect diagnostic logs without credentials.
4. Identify actual CVar structures; string addresses alone are insufficient.
5. Only then implement and validate a minimal camera patch, separately on x86
   and x64. Launcher integration and distribution require stable validation.

### Operational constraints

- Windows client: D:/games/aioncl-recette; source: D:/codex-work/ShugoConsoleDll.
- Original DLL suffix: version.dll.aioncl-original. Never permanently replace it.
- Do not log command lines, passwords, or unrestricted process memory dumps.
- Experimental files/backups stay outside tracked source. Restore after tests.
- Windows source is reported dirty and uncompilable; do not assume it matches VM.

## Recovery and x86 fixture results

- DONE: SSH uses `-F /var/lib/codex/.ssh/config -p 2222 127.0.0.1`, known host
  verification enforced. Windows user is codex. Use approved network execution.
- DONE: VM backup `/tmp/aioncl-shugo-source-before-20260920.tar.gz`, SHA256
  `41d40bdc316ab24bc33540b10c8f7436d009ac3ae413efe0a0eb9b9c82e5a61f`.
  VM upstream commit `5789b64a6730f5a09ba9860bd2349f4ca651c9ca`.
- DONE: Windows Aion-Version-Dll directory backed up to
  `D:/codex-work/camera-recovery-20260920/Aion-Version-Dll`. Then version.cpp
  restored from HEAD. exports.cpp changes and older backups/build32 preserved.
- DONE: Both Windows active version.dll files match their aioncl-original copies.
- FAILED then resolved: sudo installation requires a password. Downloaded Debian
  MinGW packages and extracted to `/tmp/aioncl-mingw/root` without sudo. Compiler:
  `/tmp/aioncl-mingw/root/usr/bin/i686-w64-mingw32-g++-posix`.
- DONE: New independent diagnostic source in `diagnostic/`, no Shugo or Detours.
  First link failed on reserved LIBRARY VERSION token; quoting fixed it.
- DONE: x86 build with warnings as errors; verified PE32/i386 and 16 matching
  forwarded exports/ordinals. DLL SHA256:
  `fa36f4d8535a513cccf41bff840ffef59f3db8bd75dda121e6ca0ea4507bcc93`.
  Artifact: `/tmp/aioncl-camera-diagnostic32.dll`.
- FAILED then resolved: fixture initially needed libgcc_s_dw2-1.dll. Rebuilt with
  static GCC runtime. Function pointer conversion warning also fixed.
- DONE: Isolated Windows x86 fixture exited 0. Target addresses 0121fffc and
  0122fff7 detected in all three passes; block-boundary overlap works; guard
  remains intact; fixture bytes unchanged; zero read errors/timeouts; complete=1.
  Log: `D:/codex-work/camera-diagnostic-20260920/aioncl-camera-34240.log`.
- DONE: Windows PowerShell parser accepted Test-Startup.ps1 (PARSE_OK).
- Observation only: upstream memory.cpp subtracts pattern size from bytesRead
  without a short-read check. This is a risk, not a proven explanation of crashes.

### Next exact action

Review and commit/push diagnostic source, then run Test-Startup.ps1 on Windows:
`-Architecture bin32 -Diagnostic D:/codex-work/camera-diagnostic-20260920/aioncl-camera-diagnostic32.dll
-State D:/codex-work/camera-diagnostic-20260920/startup32-1.json`.
Retrieve the process-specific log and verify original restoration hashes. The
script includes finally restoration plus a 110-second independent watchdog.
Real Aion startup and CVar identification remain NOT EXECUTED at this checkpoint.

## First client startup attempt

- DONE: source committed/pushed as 13fbfbe before client test.
- FAILED validation: bin32 PID 25488 exited 0 after the first scan (66 MB read,
  zero hits/errors). Log `bin32/aioncl-camera-25488.log` is incomplete. No CVar
  identification possible from this attempt.
- FAILED then resolved: finally restoration initially hit a sharing violation
  after process exit. Retried remotely after lock cleared; original restored and
  relay removed. Verified original SHA256:
  `5bb611eff3f92d830a2fd7a3b0916ba05cbffacccd570e9020432adb5be7605f`.
- Added bounded retries to restoration and an original-DLL baseline test mode.
- Windows has an active aymen console session 1; SSH uses codex outside this
  desktop. Need distinguish noninteractive startup failure from diagnostic issues.
- DONE: x64 diagnostic and fixture also compile with warnings as errors; PE32+
  verified. x64 execution not yet tested.

## Session isolation and x64 fixture

- DONE: original x86 DLL baseline under SSH also exits 0 (PID 22916). Restoration
  with retries succeeded. Thus early SSH termination is not diagnostic-specific.
- DONE: x64 isolated fixture exits 0, detects 000001b11d82fffc and
  000001b11d83fff7 in all passes, guard intact, data unchanged, no read errors or
  timeouts, complete=1. Windows log: camera-diagnostic64-20260920/aioncl-camera-1696.log.
- DONE: retrieved fixture and first startup logs to
  `/tmp/aioncl-camera-evidence-20260920/` on VM.
- IN PROGRESS: original x86 baseline on active desktop via temporary scheduled
  task (Invoke-InteractiveTest.ps1). PID 30208 verified running in session 1.
  Results directory: `D:/codex-work/camera-diagnostic-20260920/interactive-baseline32-1`.
  Test must finish and restore before next run.
- Next: after baseline completion and commit/push, use Invoke-InteractiveTest.ps1
  without -Baseline, with the x86 diagnostic path and a new RunDirectory.

## Interactive baseline corrections

- Baseline PID 30208 stayed alive at 85 seconds; user screenshots confirm login
  screen and authentication failure. The initial test's -DEVMODE-only arguments
  omitted AionCL's server settings. No server outage inferred from that failure.
- Restoration harness failed to stop that process: comparison mixed UTC with a
  locally parsed DateTime. Corrected parsing to DateTimeOffset.UtcDateTime and
  persisted exact process ID. Completed state prevents a late watchdog action.
- Baseline DLL was already original throughout. Subsequent inspection found no
  Aion process running. No diagnostic installed during interactive baseline.
- Harness now reads reviewed launcher.json/server-config.json copies beside it,
  using the existing launcher argument template and configured IPv4 login host.
- User screenshot contents are not copied into logs; no credentials collected.
- DONE: corrected baseline with AionCL arguments (PID 10832) survived 85 seconds,
  terminated automatically, original hash verified, Completed=true, scheduled
  task result 0 and removed. Run: interactive-baseline32-2.
- Updated camera README to explicitly mark historical Shugo payloads unvalidated.

## First successful in-client x86 scan

- DONE: commit 4bf08e4 pushed; interactive-scan32-1 (PID 29884) completed all
  three passes, client alive, zero read errors/timeouts, scheduled task result 0,
  original restored and verified automatically.
- Found only g_camMax at 6d9e564c, MEM_IMAGE allocation 6d9a0000, referenced at
  6d9b9a84. This is NOT an identified CVar. No g_minFov hit.
- Readable memory grew from 66 MB to 223 MB to 971 MB, indicating delayed loading.
- Diagnostic revision 2 adds a fourth pass after at least 60 seconds and matches
  ASCII case variants while recording exact_case. Test timeout raised to 130s,
  watchdog to 165s. Fixture adds lowercase spelling and waits for the late pass.
- Local reference binaries exist under /opt/codex-data/reference/aioncl-tmp;
  their identity versus the Windows binaries has NOT been verified.

## Revision 2 validation and static evidence

- DONE: reference Game.dll and CrySystem.dll SHA256 match Windows in both
  architectures. Game32 f8b5be13fcebc23d276ab4b37212101a336ce819b3c1fca68502f4821298ab4f;
  Game64 f259b60f74768c226eafff085551700bcaf3aa43a20ede7fe3925e0e31daaf0f.
- DONE: revision 2 builds PE32 and PE32+ with -Wall -Wextra -Werror. SHA256:
  x86 85794a1ebba5cf43b7cec67aa87fc960ff31089ecdb02dc15d579385727f2118;
  x64 acd542bb364b38a490d968311f5a44e1a18ba01e1a9cfde1b1756b4d125c4f90.
- DONE: fixtures PID 24372 (x86) and 24752 (x64) exit 0, complete four passes,
  detect lowercase target with exact_case=0, preserve guard and fixture bytes.
  Full logs retrieved to VM evidence directory; no read errors/timeouts.
- Static x64 Game.dll: image base 180000000; g_camMax RVA 8eb250, registration
  call RVA 21231 (vtable +18), result stored [rdi+6ee0], default string 10.00.
  g_minFov RVA 8ee050, call RVA 225ad, result [rdi+7220], default string 60.
  These are static clues, NOT runtime CVar structure validation.
- Next: commit/push revision 2, interactive x86 run with late pass, restore, then
  separate x64 run. Runtime patch is still gated on CVar identity validation.

## 2026-09-21 - Resumed runtime validation

- DONE: x86 revision 2 PID 1208 completed all passes, alive, restored, task result
  0. At late pass: g_camMax object ebb5a480, name +5, vtable 70ba2974, int +160
  and float +164 both 12. g_minFov object ebc13640, same layout/vtable, value 73.
  Three transient partial reads handled; late pointer-reference scan timed out.
- PARTIAL: x64 PID 2952 produced a complete four-pass log with two candidates:
  g_minFov object 41e92600, g_camMax 41e9f600; name +9, vtable 18021b128,
  int +184/float +188 = 60 and 32 respectively. Reference scans timed out.
  Controller task returned 0xc000013a (interrupted), not a demonstrated game
  crash. State Completed=true; on resume both active original DLL hashes match
  their backups, no Aion process and no temporary scheduled task remain.
- DONE: logs 1208 and 2952 retrieved to /tmp/aioncl-camera-evidence-20260920.
- Static x64 vtable at CrySystem RVA 21b128 identifies CXConsoleVariable:
  slot 1 -> RVA 199d80 reads integer via [this+168]; slot 2 -> RVA 199d90 reads
  float via [this+176]; slot 3 -> RVA 199db0 returns string pointer [this+160].
  Do NOT assume inline values are authoritative until these pointers are checked.
- Revision 3 adds read-only evidence of numeric storage pointers, sanitized
  numeric text, and first 16 executable bytes of three known getter slots.
  No memory patch created or applied yet.
- User will perform distance/FOV in-game testing only after an explicit ready
  notice. Current tests are automated diagnostics and close the client.
