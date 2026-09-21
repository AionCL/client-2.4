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

## Validated storage and opt-in patch prototype

- DONE: layout32 PID 10964, task result 0, original restored. Exact objects have
  category 0, type 3, internal int/float/text pointers, matching numeric values.
  CrySystem vtable RVA 1a2974; getter prefixes (slots 1,2,3):
  8b81980000008b00c3; 8b819c000000d900c3; 8b8194000000c3.
- DONE: layout64 PID 23824, task result 0, original restored. Same storage
  validation; vtable RVA 21b128; getter prefixes:
  488b81a80000008b00c3; 488b81b0000000f30f1000c3; 488b81a0000000c3.
  Numeric storage is this+184/188/192, versus this+160/164/168 on x86.
- DONE: both logs retrieved to VM evidence directory. These checks validate the
  target structure for the exact binaries, not the visible camera behavior.
- Added a separately compiled AIONCL_CAMERA_PATCH prototype, explicit child-only
  AIONCL_CAMERA_TEST=1 required. Rejects ambiguous/incomplete scans, mismatched
  CrySystem vtable/getters, non-internal pointers, inconsistent or changing values.
  Writes only 40 bytes per CVar (numeric representations), requests 80/30, observes
  ten seconds, then rolls back. No code patches or page-protection changes.
- DONE: native value tests pass ASan/UBSan with leak checks disabled because
  LeakSanitizer fails under this sandbox's ptrace. Initial LSan run failed for
  that environment reason. Both prototype DLLs compile warning-free (PE32/PE32+).
- Prototype hashes: x86 cdc8be35439a082995e8c5bacb4a99a4e3e5afc884c109385216fdcf3fc5b591;
  x64 ca08ab4ea230a70c956b1a908df0d35b88e6508a61e4f55b29cef07d460c95af.
- Added -CameraPatch harness mode, system.cfg backup/restore, and required
  patch_test applied=1 restored=1 result. Both PowerShell scripts parse correctly.
- DONE: enabled x86 patch fixture exits 0, fixture unchanged, guard intact,
  patch_skipped reason=unvalidated_layout, complete=1. No prototype has yet been
  applied inside Aion at this checkpoint.

## Automated patch results and manual test preparation

- DONE: prototype source committed/pushed as 6deb5df before Aion writes.
- DONE: x86 PID 28428, task result 0: FOV 73 -> 80, distance 12 -> 30, both stable
  for ten seconds, then original 73/12 bytes restored. patch_test applied=1
  restored=1. Original DLL and system.cfg restored; state Completed=true.
- DONE: x64 PID 27484, same successful ten-second application/readback/rollback,
  task result 0, original DLL and system.cfg restored. Both logs on VM.
- No in-game visual test performed yet. These results prove the narrow storage
  operation, not camera behavior during character play or production stability.
- Added opt-in AIONCL_CAMERA_MANUAL=1 flow: waits up to 30 minutes for a PID-scoped
  .apply signal, rescans after login, applies, waits for .restore or 30 minutes.
  Test harness -ManualCamera -StartOnly detaches a temporary scheduled task,
  records its identity, and removes it when the session ends. Watchdog covers the
  longer session; exact PID, DLL and system.cfg restoration checks remain active.
- DONE: updated code compiles x86/x64; value tests pass; updated Windows scripts
  parse correctly. Next gate: automated signal/apply/restore run of manual mode
  before opening the actual user recipe session.

## Manual protocol validated - user recipe pending

- DONE: source committed/pushed as 05191b2 before manual-mode runtime test.
- DONE: manual-smoke64-1, PID 26896. Waited without changing camera until .apply.
  Fresh scan validated both CVars, applied 80/30, then .restore rolled back to
  73/12. patch_test applied=1 restored=1, state Completed=true. Original DLL and
  system.cfg hashes verified after exit. Temporary task automatically removed.
  Log retrieved to VM evidence directory. A query for the deleted task returned
  absent (exit 1); this is expected cleanup, not a failed camera test.
- Current manual-capable build SHA256:
  x86 79bb7fc591e3654bd01bfbcff706f63783f1117a9fd9f6048fafdb60e4170439;
  x64 cefb1948acb7a5740e3057fd1db0323024cb60a4b896b64305a5903185e925c2.
  Both compile, the manual protocol was exercised on x64. Windows x86 scratch
  still has the earlier auto-test build; use VM artifact if x86 manual is needed.
- Plain read-only build still imports ReadProcessMemory, not WriteProcessMemory.
- ACTIVE at checkpoint: actual user x64 recipe in
  `D:/codex-work/camera-diagnostic-20260920/user-recette64-1`.
  Read state.json for exact PID and task.json for task identity. The worker waits
  30 minutes for the user to reach a character in-game. Do NOT send .apply before
  the user confirms in-game. The user does not need to copy or install files.
- After confirmation: create empty `D:/games/aioncl-recette/bin64/aioncl-camera-PID.apply`,
  then verify `manual_applied fov=80 distance=30` before asking for camera checks.
  Ask for maximum zoom-out, view angle, rotation/collision, map-change stability.
  At end create `.restore` counterpart or let normal game exit trigger file
  restoration. Confirm state Completed=true and hashes. No launcher integration
  or public update payload published: visual/in-game stability remains pending.
- Verified user recipe process PID 12112 in interactive session 1, started
  2026-09-21 06:14:52 UTC (08:14:52 Paris). Task:
  AionCL-Camera-f58af7acfca9456385765bbe8f5de0ac. No .apply signal sent.
  Before resuming, check process and state: this record is historical once the
  30-minute wait expires or the user closes the client. Never reuse a stale PID.

## Resume 2026-09-21 12:12 UTC - Windows tunnel unavailable

- DONE: inspected Git before changes; main clean and synchronized with origin.
  Reviewed the previous recipe handoff and successful automated x86/x64 results.
- BLOCKED: SSH to 127.0.0.1:2222 using the existing explicit SSH configuration
  returns Connection refused. No Windows command ran, no apply signal was sent,
  and no client file or camera value was changed during this resume.
- The earlier PID 12112 recipe is historical and its configured wait has elapsed.
  Automatic restoration was armed, but its actual completion cannot be verified
  until Windows is reachable. Do not claim restoration or reuse that PID.
- NEXT: restore tunnel availability, inspect user-recette64-1/state.json and
  result.txt, verify original DLL/config hashes and scheduled-task cleanup.
  Then open a fresh manual recipe if needed and wait for explicit confirmation
  that the character is in-game before signaling apply. Visual FOV/distance
  validation and launcher integration remain pending; no build publication needed.

## Direct Windows SSH access recovered

- DONE: user supplied Windows Wi-Fi address 192.168.1.7. Direct port 22 responds.
  Initial strict host check rejected this previously unknown address; no key was
  accepted or host verification disabled.
- DONE: retried with HostKeyAlias=[127.0.0.1]:2222 to check the existing trusted
  Windows tunnel key. Authentication succeeded and hostname returned Zbook-Aymen.
  Recovery command: ssh -F /var/lib/codex/.ssh/config -o BatchMode=yes
  -o StrictHostKeyChecking=yes -o 'HostKeyAlias=[127.0.0.1]:2222'
  -o ConnectTimeout=8 -p 22 codex@192.168.1.7 hostname
- No Windows files or camera values changed. Next: inspect the historical recipe
  state and verify restoration before starting any fresh camera test.

## Fresh user camera recipe via direct SSH

- DONE: clean Git inspected. Previous user-recette64-1 state Completed=true,
  result reports restoration. Actual x64 DLL, x86 DLL and system.cfg hashes match
  recorded originals. Old scheduled task absent. Prototype x64 hash matches
  cefb1948acb7a5740e3057fd1db0323024cb60a4b896b64305a5903185e925c2.
- Initial script invocation failed under PowerShell execution policy. Retried
  successfully with process-scoped -ExecutionPolicy Bypass; no policy persisted.
- ACTIVE: user-recette64-2, PID 12736, interactive session 1, process verified
  by PID as aionclassic.bin. Windows reports StartUtc 2026-09-21T10:42:36.6859468Z;
  use live state/PID checks, not previous journal times, to establish liveness.
  Task AionCL-Camera-20c1dab5628144578440a5044a7b3503. State/result under
  D:/codex-work/camera-diagnostic-20260920/user-recette64-2/.
  Log D:/games/aioncl-recette/bin64/aioncl-camera-12736.log is being produced.
- No apply signal sent. User instructed to enter character and explicitly report
  in-game before activation. Temporary x64 DLL is installed with watchdog armed;
  do not describe this active session as already restored. Next: confirm live PID
  and manual_ready, then after user confirmation signal apply and verify
  manual_applied before requesting visual checks. Restore and verify at end.

## First in-game activation refused safely

- User confirmed character in-game at maximum zoom and provided baseline image.
  Verified PID 12736 and manual_ready, then sent its .apply signal.
- FAILED activation: in-game rescan read 2171977728 bytes with errors=0 but
  timeout=1 at eight seconds. patch_skipped reason=incomplete_scan; no writes.
- DONE: harness ended recipe; Completed=true, original x64 DLL and system.cfg
  hashes verified. User needs a fresh session, not the terminated PID.
- Extend only explicit in-game rescan deadline to 30 seconds; retain bounded
  blocks, completeness/identity guards, startup deadlines and restoration.
- DONE: x86/x64 builds warning-free, PE32/PE32+ verified; native ASan/UBSan
  value tests pass. Correction committed/pushed as 1d096f5 before deployment.
- ACTIVE: updated x64 DLL transferred automatically; user-recette64-3 launched,
  PID 21876, StartUtc 2026-09-21T10:47:00.4376714Z from Windows state.
  Task AionCL-Camera-4f7b182863b84e0b831492e32e5f45b9. No apply signal sent;
  wait for user to confirm character again. State/result in the corresponding
  D:/codex-work/camera-diagnostic-20260920/user-recette64-3 directory.

## In-game application confirmed - visual feedback pending

- User confirmed ready again. Verified live PID 21876, Completed=false and
  manual_ready, then sent its .apply signal.
- DONE: fresh scan completed: bytes=2056499200, hits=11, errors=0, timeout=0.
  Log confirms patch_applied g_minFov before=60 after=80 and g_camMax
  before=32 after=30; manual_applied fov=80 distance=30 timeout_seconds=1800.
- IMPORTANT: actual in-game defaults differ from login tests (73/12). This test
  reduces distance 32 to 30; it does NOT demonstrate extended maximum zoom.
  User informed and asked for same-angle screenshot, then zoom-limit comparison.
- ACTIVE: manual test holding values, restoration watchdog armed. No restore
  signal sent yet; await visual feedback. Restore originals 60/32 at test end,
  then verify disk restoration via state/result and hashes. Do not claim visual
  success, extended range or launcher readiness from memory readback alone.

## Requested distance-100 experiment

- User reports visible change and provides second screenshot, then explicitly
  requests exaggerated distance 100. Wider framing is consistent with FOV effect;
  visual extended-distance behavior is not yet validated.
- DONE: sent restore to PID 21876 before rebuilding. Log confirms original
  FOV 60 and distance 32 restored, patch_test applied=1 restored=1, Completed=true.
- Change experimental target to FOV 80 / distance 100, extend distance validation
  upper bound to exactly 100 and add boundary tests rejecting 101. Existing
  identity guards and rollback retained. Requires fresh session and user-ready
  confirmation; do not modify memory behind the active prototype's watchdog.
- DONE: native ASan/UBSan tests pass including 100/101 boundary; warning-free
  x86/x64 builds verified PE32/PE32+. Committed/pushed 6ff5a6a before transfer.
- ACTIVE: updated x64 recipe user-recette64-4, PID 8796, Windows StartUtc
  2026-09-21T10:51:55.9806286Z; task AionCL-Camera-7aff1925f57942bb9e3f8d3a62734d83.
  State/result at D:/codex-work/camera-diagnostic-20260920/user-recette64-4/.
  No apply signal yet. Await fresh in-game confirmation then verify manual_ready
  and signal aioncl-camera-8796.apply only if this PID is still the live recipe.
  Target is now 80/100; retain automatic rollback and verify restoration at end.

## Distance 100 applied in-game - user comparison pending

- User confirmed ready. Verified PID 8796 in session 1, Completed=false and
  manual_ready before sending its .apply signal.
- DONE: fresh scan completed, bytes=2049470464 hits=11 errors=0 timeout=0.
  Log confirms g_minFov 60 -> 80, g_camMax 32 -> 100, and
  manual_applied fov=80 distance=100 timeout_seconds=1800.
- ACTIVE: user-recette64-4 holds experimental values with watchdog armed.
  User asked to zoom out to maximum, capture the result and check zoom-in.
  Visible extended distance and stability remain pending user feedback.
- NEXT: verify live PID/state before further action; at recipe end signal
  aioncl-camera-8796.restore only if this is still the active session. Confirm
  rollback to 60/32 and disk restoration. No production/launcher deployment.

## User validates x64 camera effect; recipe restored

- DONE: user explicitly reports perfect operation and supplies screenshot showing
  substantially increased camera range. First visual x64 in-game validation of
  FOV 80 / distance 100 obtained. This does not establish long-session stability,
  map-transition behavior or x86 visual equivalence.
- DONE: notified user of test closure, sent .restore to PID 8796. Log confirms
  FOV 60 / distance 32 restored, patch_test applied=1 restored=1, complete=1;
  state Completed=true. Actual original x64 DLL and system.cfg hashes verified.
- Evidence retrieved to /tmp/aioncl-camera-evidence-20260920/ingame-distance100-8796.log.
- NEXT: extend stability coverage (zone changes, camera collision, repeated
  sessions), separately validate x86 in-game before supporting it. Design launcher
  integration only after stability gates; no permanent DLL replacement or public
  update deployed. Current Windows client is restored, not persistently patched.

## Integration preparation - external helper

- User requested launcher camera controls with distance maximum 100 and an
  additional post-base client package. Worktrees inspected before edits.
- Added experimental x64 external helper reusing bounded scanner and exact CVar
  guards through VirtualQueryEx/ReadProcessMemory. It checks target image path,
  architecture, duplicate helper mutex and getter signatures. No DLL replacement.
- Helper compiles PE32+ on canonical VM; native value tests pass. Initial build
  failed on NOMINMAX redefinition, corrected with guard and rebuilt successfully.
- New transport still requires Windows runtime validation before release. Launcher
  settings integration is being prepared; no manifest/release published yet.
- DONE: external64-3 interactive task ran helper against original x64 DLL,
  PID 15068. Log ready=1; FOV 60 -> 80 and distance 10 -> 100, then engine reset
  73/12 was detected and reapplied to 80/100. Game exited on controlled test end,
  helper complete=1. Completed=true, original DLL/config hashes verified. Temporary
  helper removed and helper task unregistered. Earlier external64-1 SSH child
  produced no scan evidence; external64-2 refused overlapping game. Neither is
  counted as successful runtime validation. No credentials used or logged.
- Added small append-only package builder and roundtrip/boundary tests. Local
  v2.4.5 package has one tools/AionCL.Camera.exe entry and preserves all 16 base/
  existing patch packages. Python tests pass; release not published at checkpoint.
- DONE: published v2.4.5 pre-release at full commit cbeacab1186b16aa546c94fdb02262089ada5c52
  (initial abbreviated target rejected by GitHub; full SHA succeeded). New archive
  017 SHA256 9f21798c244c0274c65b635966134a5048682abae2b2efc33c545c0ba5538ed9.
- DONE: launcher 2.5.41 CI 35604087975 passed; UI dialog screenshot and bounds
  validated in interactive desktop. Actual launcher downloader/extractor validated
  public manifest, downloaded only archive 017, checked hashes and helper argument
  rejection in scratch directory, then removed test output: CAMERA_PACKAGE_PASS.
- Published launcher-v2.5.41 at 02cc3415da553a85a43be23cb330cc9d465bf281.
  User workflow: launcher update -> client update -> Settings Camera/FOV enable
  80/100 -> start game. Still needs in-game confirmation of external transport,
  zone changes and relaunch/disable checks. Original client files restored after
  experiments; no client DLL permanently replaced. Detailed release docs added.
