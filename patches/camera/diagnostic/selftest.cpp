#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

// In-process fixture only: no client files or game memory are touched.
int main(int argc, char** argv) {
    if (argc != 2) return 1;
    auto* region = static_cast<unsigned char*>(VirtualAlloc(nullptr, 3 * 65536, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE));
    if (!region) return 2;
    memcpy(region + 65532, "g_minFov", 9); // Spans a scanner block boundary.
    memcpy(region + 131072 - 9, "g_camMax", 9); // Ends immediately before a guard page.
    memcpy(region + 128, "g_minfov", 9);
    DWORD old;
    if (!VirtualProtect(region + 131072, 65536, PAGE_READWRITE | PAGE_GUARD, &old)) return 3;
    printf("fixture fov=%p cam=%p\n", region + 65532, region + 131072 - 9);
    HMODULE dll = LoadLibraryA(argv[1]);
    if (!dll) { printf("load_error=%lu\n", GetLastError()); return 4; }
    DWORD (WINAPI* language)(DWORD, LPWSTR, DWORD) = nullptr;
    FARPROC exported = GetProcAddress(dll, "VerLanguageNameW");
    static_assert(sizeof(language) == sizeof(exported));
    memcpy(&language, &exported, sizeof(language));
    wchar_t name[100];
    if (!language || !language(0x409, name, 100)) return 5;
    Sleep(75000);
    MEMORY_BASIC_INFORMATION info{};
    VirtualQuery(region + 131072, &info, sizeof(info));
    bool ok = (info.Protect & PAGE_GUARD) && !memcmp(region + 65532, "g_minFov", 9) &&
        !memcmp(region + 131072 - 9, "g_camMax", 9);
    printf("fixture_unchanged=%u guard_intact=%u\n", ok ? 1u : 0u, (info.Protect & PAGE_GUARD) ? 1u : 0u);
    return ok ? 0 : 6;
}
