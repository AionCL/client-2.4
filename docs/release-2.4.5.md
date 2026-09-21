# Client 2.4.5 camera preview

Release: https://github.com/AionCL/client-2.4/releases/tag/v2.4.5
Source commit: cbeacab1186b16aa546c94fdb02262089ada5c52.

Only aioncl-client-2.4.5-017.zip is new. It contains tools/AionCL.Camera.exe.
All previous packages, their hashes and URLs remain unchanged. The launcher
installs the helper after the base client and existing patches; no full-client
repack or permanent version.dll replacement is required.

Package SHA-256: 9f21798c244c0274c65b635966134a5048682abae2b2efc33c545c0ba5538ed9.
Build and package commands are documented under patches/camera/runtime.
Python package roundtrip/boundary tests and Windows launcher download/extract
validation passed. External helper readback test passed on the original x64
client. Final launcher in-game and map-transition recipe remains pending.
