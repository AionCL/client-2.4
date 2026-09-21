// Included only in the opt-in patch build, inside the scanner namespace.
constexpr size_t ValueOffset = sizeof(uintptr_t) == 8 ? 184 : 160;
constexpr size_t PointerOffset = sizeof(uintptr_t) == 8 ? 160 : 148;

bool PatchObject(uintptr_t object, unsigned name, camera::Values& values, bool identityOnly = false) {
    if (!object || object % 16 || name > 1) return false;
    MEMORY_BASIC_INFORMATION m{};
    if (!VirtualQuery(reinterpret_cast<void*>(object), &m, sizeof(m)) ||
        m.Type != MEM_PRIVATE || m.Protect != PAGE_READWRITE) return false;
    unsigned char prefix[sizeof(uintptr_t) + 10]{};
    uintptr_t vt;
    uintptr_t pointers[3]{};
    uint32_t type;
    if (!Read(object, prefix, sizeof(prefix)) || prefix[sizeof(uintptr_t)] != 0 ||
        memcmp(prefix + sizeof(uintptr_t) + 1, Names[name], 9)) return false;
    memcpy(&vt, prefix, sizeof(vt));
    uintptr_t cry = reinterpret_cast<uintptr_t>(GetModuleHandleW(L"CrySystem.dll"));
    size_t vtableRva = sizeof(uintptr_t) == 8 ? 0x21b128 : 0x1a2974;
    if (!cry || vt != cry + vtableRva || !Vtable(vt) ||
        !Read(object + PointerOffset, pointers, sizeof(pointers)) ||
        !Read(object + (sizeof(uintptr_t) == 8 ? 156 : 144), &type, sizeof(type)) || type != 3 ||
        pointers[0] != object + ValueOffset + 8 || pointers[1] != object + ValueOffset ||
        pointers[2] != object + ValueOffset + 4) return false;
    const unsigned char integer64[] = {0x48,0x8b,0x81,0xa8,0,0,0,0x8b,0,0xc3};
    const unsigned char float64[] = {0x48,0x8b,0x81,0xb0,0,0,0,0xf3,0x0f,0x10,0,0xc3};
    const unsigned char string64[] = {0x48,0x8b,0x81,0xa0,0,0,0,0xc3};
    const unsigned char integer32[] = {0x8b,0x81,0x98,0,0,0,0x8b,0,0xc3};
    const unsigned char float32[] = {0x8b,0x81,0x9c,0,0,0,0xd9,0,0xc3};
    const unsigned char string32[] = {0x8b,0x81,0x94,0,0,0,0xc3};
    const unsigned char* signatures[] = {
        sizeof(uintptr_t) == 8 ? integer64 : integer32,
        sizeof(uintptr_t) == 8 ? float64 : float32,
        sizeof(uintptr_t) == 8 ? string64 : string32};
    const size_t sizes[] = {
        sizeof(uintptr_t) == 8 ? sizeof(integer64) : sizeof(integer32),
        sizeof(uintptr_t) == 8 ? sizeof(float64) : sizeof(float32),
        sizeof(uintptr_t) == 8 ? sizeof(string64) : sizeof(string32)};
    for (unsigned i = 0; i < 3; ++i) {
        uintptr_t method;
        unsigned char code[16]{};
        MEMORY_BASIC_INFORMATION codeRegion{};
        if (!Read(vt + (i + 1) * sizeof(uintptr_t), &method, sizeof(method)) ||
            !Executable(method) || !VirtualQuery(reinterpret_cast<void*>(method), &codeRegion, sizeof(codeRegion)) ||
            reinterpret_cast<uintptr_t>(codeRegion.AllocationBase) != cry ||
            !Read(method, code, sizes[i]) || memcmp(code, signatures[i], sizes[i])) return false;
    }
    return Read(object + ValueOffset, &values, sizeof(values)) && (identityOnly || camera::Valid(values, name));
}

bool Store(uintptr_t object, const camera::Values& values) {
    SIZE_T written = 0;
    BOOL ok = WriteProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(object + ValueOffset),
        &values, sizeof(values), &written);
    if (!ok || written != sizeof(values)) {
        Log("patch_write_failed error=%lu bytes=%zu\n", GetLastError(), static_cast<size_t>(written));
        return false;
    }
    camera::Values verify{};
    return Read(object + ValueOffset, &verify, sizeof(verify)) && !memcmp(&verify, &values, sizeof(values));
}

void CameraPatch() {
    // The plain diagnostic cannot write. A separately built binary also needs an explicit opt-in.
    wchar_t enabled[8]{};
    if (GetEnvironmentVariableW(L"AIONCL_CAMERA_TEST", enabled, 8) != 1 || enabled[0] != L'1') {
        Log("patch_skipped reason=not_enabled\n");
        return;
    }
    if (!stringScanComplete || errors) { Log("patch_skipped reason=incomplete_scan\n"); return; }
    uintptr_t objects[2]{};
    camera::Values originals[2]{};
    for (size_t i = 0; i < hitCount; ++i) {
        if (hits[i].address < sizeof(uintptr_t) + 1) continue;
        uintptr_t object = hits[i].address - sizeof(uintptr_t) - 1;
        camera::Values current{};
        if (!PatchObject(object, hits[i].name, current)) continue;
        unsigned n = hits[i].name;
        if (objects[n] && objects[n] != object) { Log("patch_skipped reason=ambiguous\n"); return; }
        objects[n] = object;
        originals[n] = current;
    }
    if (!objects[0] || !objects[1]) { Log("patch_skipped reason=unvalidated_layout\n"); return; }
    Sleep(1000);
    for (unsigned n = 0; n < 2; ++n) {
        camera::Values current{};
        if (!PatchObject(objects[n], n, current) || memcmp(&current, &originals[n], sizeof(current))) {
            Log("patch_skipped reason=unstable\n"); return;
        }
    }
    bool attempted[2]{};
    bool applied = true;
    for (unsigned n = 0; n < 2; ++n) {
        attempted[n] = true;
        if (!Store(objects[n], camera::Desired(n))) { applied = false; break; }
        Log("patch_applied name=%s before=%.9g after=%ld\n", Names[n], originals[n].floating,
            static_cast<long>(camera::Desired(n).integer));
    }
    FlushFileBuffers(logFile);
    if (applied) {
        for (unsigned second = 0; second < 10; ++second) {
            Sleep(1000);
            for (unsigned n = 0; n < 2; ++n) {
                camera::Values current{};
                if (!PatchObject(objects[n], n, current) || current.floating != camera::Desired(n).floating) {
                    Log("patch_unstable name=%s\n", Names[n]); applied = false;
                }
            }
            if (!applied) break;
        }
    }
    bool restored = true;
    for (unsigned n = 0; n < 2; ++n) {
        if (!attempted[n]) continue;
        // Revalidate object identity before rollback; never restore into a freed/reused object.
        camera::Values current{};
        if (!PatchObject(objects[n], n, current, true) || !Store(objects[n], originals[n])) {
            Log("patch_restore_failed name=%s\n", Names[n]); restored = false;
        } else Log("patch_restored name=%s value=%.9g\n", Names[n], originals[n].floating);
    }
    Log("patch_test applied=%u restored=%u\n", applied ? 1u : 0u, restored ? 1u : 0u);
}
