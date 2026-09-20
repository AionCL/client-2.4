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
