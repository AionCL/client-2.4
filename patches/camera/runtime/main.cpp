// External x64 transport: share the diagnostic's bounded reader and identity guards.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#include "../diagnostic/camera-values.hpp"

static HANDLE target;
static HMODULE crySystem;
static SIZE_T RemoteQuery(LPCVOID address, PMEMORY_BASIC_INFORMATION info, SIZE_T size) {
    return VirtualQueryEx(target, address, info, size);
}
static HANDLE TargetProcess() { return target; }
static HMODULE TargetModule(LPCWSTR) { return crySystem; }
#define AIONCL_CAMERA_EXTERNAL
#define VirtualQuery RemoteQuery
#define GetCurrentProcess TargetProcess
#define GetModuleHandleW TargetModule
#include "../diagnostic/version.cpp"
namespace {
#include "../diagnostic/camera-patch.hpp"
}
#undef VirtualQuery
#undef GetCurrentProcess
#undef GetModuleHandleW

static bool Number(const wchar_t* text, unsigned long& value) {
    if (!*text) return false;
    for (const wchar_t* p = text; *p; ++p) if (*p < L'0' || *p > L'9') return false;
    wchar_t* end;
    value = wcstoul(text, &end, 10);
    return !*end && value != ULONG_MAX;
}

int wmain(int argc, wchar_t** argv) {
    unsigned long pid, fov, distance;
    if (argc != 4 || !Number(argv[1], pid) || !Number(argv[2], fov) ||
        !Number(argv[3], distance) || !pid || fov < 60 || fov > 170 || distance < 5 || distance > 100) return 2;
    target = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE |
        PROCESS_VM_OPERATION | SYNCHRONIZE, FALSE, pid);
    if (!target) return 3;
    wchar_t game[MAX_PATH], own[MAX_PATH];
    DWORD size = MAX_PATH;
    if (!QueryFullProcessImageNameW(target, 0, game, &size) ||
        !GetModuleFileNameW(nullptr, own, MAX_PATH)) return 4;
    // Only control the game belonging to this package installation.
    wchar_t* slash = wcsrchr(own, L'\\');
    if (!slash) return 4;
    *slash = 0;
    slash = wcsrchr(own, L'\\');
    if (!slash) return 4;
    *slash = 0;
    wchar_t expected[MAX_PATH];
    if (swprintf(expected, MAX_PATH, L"%ls\\bin64\\aionclassic.bin", own) < 0 || _wcsicmp(game, expected)) return 5;
    BOOL wow = FALSE;
    if (!IsWow64Process(target, &wow) || wow) return 5;
    wchar_t mutexName[80];
    swprintf(mutexName, 80, L"Local\\AionCL.Camera.%lu", pid);
    HANDLE mutex = CreateMutexW(nullptr, TRUE, mutexName);
    if (!mutex || GetLastError() == ERROR_ALREADY_EXISTS) return 6;
    wchar_t logPath[MAX_PATH];
    if (swprintf(logPath, MAX_PATH, L"%ls\\tools\\camera-%lu.log", own, pid) < 0) return 7;
    logFile = CreateFileW(logPath, GENERIC_WRITE, FILE_SHARE_READ, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (logFile == INVALID_HANDLE_VALUE) return 7;
    Log("camera_runtime=1 pid=%lu fov=%lu distance=%lu\n", pid, fov, distance);
    camera::Values desired[2]{};
    for (unsigned n = 0; n < 2; ++n) {
        desired[n].integer = static_cast<int32_t>(n ? distance : fov);
        desired[n].floating = static_cast<float>(desired[n].integer);
        snprintf(desired[n].text, sizeof(desired[n].text), "%ld", static_cast<long>(desired[n].integer));
    }
    uintptr_t objects[2]{};
    // Wait for the engine to load; discovery is bounded and never relaxes identity checks.
    for (unsigned attempt = 0; attempt < 20 && WaitForSingleObject(target, 3000) == WAIT_TIMEOUT; ++attempt) {
        HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid);
        if (snapshot == INVALID_HANDLE_VALUE) continue;
        MODULEENTRY32W entry{}; entry.dwSize = sizeof(entry);
        if (Module32FirstW(snapshot, &entry)) do {
            if (!_wcsicmp(entry.szModule, L"CrySystem.dll")) crySystem = reinterpret_cast<HMODULE>(entry.modBaseAddr);
        } while (Module32NextW(snapshot, &entry));
        CloseHandle(snapshot);
        if (!crySystem) continue;
        hitCount = 0; errors = 0; deadline = GetTickCount64() + 30000;
        Scan(false);
        if (!stringScanComplete || errors) continue;
        objects[0] = objects[1] = 0;
        bool ambiguous = false;
        for (size_t i = 0; i < hitCount; ++i) {
            if (hits[i].address < sizeof(uintptr_t) + 1) continue;
            uintptr_t object = hits[i].address - sizeof(uintptr_t) - 1;
            camera::Values values{};
            if (!PatchObject(object, hits[i].name, values)) continue;
            unsigned n = hits[i].name;
            if (objects[n] && objects[n] != object) ambiguous = true;
            objects[n] = object;
        }
        if (ambiguous) { Log("refused=ambiguous\n"); break; }
        if (!objects[0] || !objects[1]) continue;
        Log("ready=1\n");
        while (WaitForSingleObject(target, 1000) == WAIT_TIMEOUT) {
            camera::Values current[2]{};
            if (!PatchObject(objects[0], 0, current[0]) || !PatchObject(objects[1], 1, current[1])) {
                Log("stopped=identity_changed\n"); break;
            }
            bool ok = true;
            for (unsigned n = 0; n < 2; ++n) {
                if (current[n].floating == desired[n].floating) continue;
                if (!Store(objects[n], desired[n])) {
                    camera::Values identity{};
                    for (unsigned rollback = 0; rollback <= n; ++rollback)
                        if (PatchObject(objects[rollback], rollback, identity, true))
                            Store(objects[rollback], current[rollback]);
                    ok = false; break;
                }
                Log("applied name=%s before=%.9g after=%.9g\n", Names[n], current[n].floating, desired[n].floating);
                FlushFileBuffers(logFile);
            }
            if (!ok) break;
        }
        break;
    }
    Log("complete=1\n");
    CloseHandle(logFile); CloseHandle(mutex); CloseHandle(target);
    return 0;
}
