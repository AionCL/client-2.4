#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>

namespace {
constexpr size_t Block = 64 * 1024;
constexpr size_t MaxHits = 128;
const char* const Names[] = {"g_minFov", "g_camMax"};
struct Hit { uintptr_t address; unsigned name; };
Hit hits[MaxHits];
size_t hitCount;
unsigned char buffer[Block + 16];
HMODULE self;
void* stackAllocation;
HANDLE logFile = INVALID_HANDLE_VALUE;
unsigned errors;
ULONGLONG deadline;

void Log(const char* format, ...) {
    char line[1024];
    va_list args;
    va_start(args, format);
    int length = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    if (length <= 0) return;
    DWORD written;
    DWORD count = static_cast<DWORD>(length < 1024 ? length : 1023);
    if (!WriteFile(logFile, line, count, &written, nullptr) || written != count)
        OutputDebugStringA("AionCL diagnostic log write failed");
}

bool Readable(const MEMORY_BASIC_INFORMATION& m) {
    if (m.State != MEM_COMMIT || (m.Protect & (PAGE_GUARD | PAGE_NOACCESS))) return false;
    DWORD p = m.Protect & 0xff;
    return p == PAGE_READONLY || p == PAGE_READWRITE || p == PAGE_WRITECOPY ||
           p == PAGE_EXECUTE_READ || p == PAGE_EXECUTE_READWRITE || p == PAGE_EXECUTE_WRITECOPY;
}

bool Executable(uintptr_t address) {
    MEMORY_BASIC_INFORMATION m{};
    return VirtualQuery(reinterpret_cast<void*>(address), &m, sizeof(m)) == sizeof(m) &&
           Readable(m) && m.Type == MEM_IMAGE && (m.Protect & 0xf0);
}

bool Read(uintptr_t address, void* output, size_t length) {
    if (!length || length > sizeof(buffer) || address > UINTPTR_MAX - length) return false;
    MEMORY_BASIC_INFORMATION m{};
    if (VirtualQuery(reinterpret_cast<void*>(address), &m, sizeof(m)) != sizeof(m) || !Readable(m))
        return false;
    uintptr_t base = reinterpret_cast<uintptr_t>(m.BaseAddress);
    if (address < base || length > m.RegionSize || address - base > m.RegionSize - length) return false;
    SIZE_T received = 0;
    BOOL ok = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(address), output, length, &received);
    if (!ok || received != length) {
        DWORD error = GetLastError();
        if (errors++ < 16) Log("read_error address=%p size=%zu received=%zu error=%lu\n",
            reinterpret_cast<void*>(address), length, static_cast<size_t>(received), error);
        return false;
    }
    return true;
}

bool Vtable(uintptr_t address) {
    uintptr_t methods[3]{};
    return Read(address, methods, sizeof(methods)) && Executable(methods[0]) &&
           Executable(methods[1]) && Executable(methods[2]);
}

void Inspect(const Hit& hit) {
    // Infer candidates from a nearby vtable, without assuming Shugo's layout is valid.
    for (size_t back = sizeof(uintptr_t); back <= 64; ++back) {
        if (hit.address < back) continue;
        uintptr_t object = hit.address - back;
        uintptr_t vt = 0;
        if (!Read(object, &vt, sizeof(vt)) || !Vtable(vt)) continue;
        Log("candidate name=%s object=%p name_offset=%zu vtable=%p\n", Names[hit.name],
            reinterpret_cast<void*>(object), back, reinterpret_cast<void*>(vt));
        // Only report plausible numeric fields after the 128-byte inline name.
        for (size_t offset = (back + 128 + 3) & ~size_t(3); offset < 224; offset += 4) {
            float value;
            int32_t integer;
            if (!Read(object + offset, &integer, sizeof(integer))) continue;
            memcpy(&value, &integer, sizeof(value));
            if (isfinite(value) && value >= 1.0f && value <= 180.0f)
                Log("numeric object=%p offset=%zu float=%.9g\n", reinterpret_cast<void*>(object), offset, value);
            if (integer >= 1 && integer <= 180)
                Log("numeric object=%p offset=%zu int=%ld\n", reinterpret_cast<void*>(object), offset, static_cast<long>(integer));
        }
    }
}

void MatchStrings(uintptr_t address, size_t bytes, size_t step, const MEMORY_BASIC_INFORMATION& m) {
    for (size_t i = 0; i < step && i < bytes; ++i) {
        if (buffer[i] != 'g') continue;
        for (unsigned n = 0; n < 2; ++n) {
            size_t length = strlen(Names[n]) + 1;
            if (length > bytes - i || memcmp(buffer + i, Names[n], length)) continue;
            if (hitCount == MaxHits) return;
            hits[hitCount++] = {address + i, n};
            Log("string name=%s address=%p allocation=%p type=%lx protect=%lx\n",
                Names[n], reinterpret_cast<void*>(address + i), m.AllocationBase, m.Type, m.Protect);
            Inspect(hits[hitCount - 1]);
        }
    }
}

void MatchReferences(uintptr_t address, size_t bytes, size_t step, unsigned& count) {
    for (size_t i = 0; i < step && i + sizeof(uintptr_t) <= bytes; ++i) {
        uintptr_t pointer;
        memcpy(&pointer, buffer + i, sizeof(pointer));
        for (size_t n = 0; n < hitCount; ++n) {
            if (pointer != hits[n].address) continue;
            Log("reference name=%s at=%p target=%p\n", Names[hits[n].name],
                reinterpret_cast<void*>(address + i), reinterpret_cast<void*>(pointer));
            if (++count >= 256) return;
        }
    }
}

void Scan(bool references) {
    SYSTEM_INFO info{};
    GetSystemInfo(&info);
    uintptr_t address = reinterpret_cast<uintptr_t>(info.lpMinimumApplicationAddress);
    uintptr_t maximum = reinterpret_cast<uintptr_t>(info.lpMaximumApplicationAddress);
    unsigned refs = 0;
    uint64_t total = 0;
    while (address < maximum && GetTickCount64() < deadline) {
        MEMORY_BASIC_INFORMATION m{};
        if (VirtualQuery(reinterpret_cast<void*>(address), &m, sizeof(m)) != sizeof(m)) {
            Log("query_error address=%p error=%lu\n", reinterpret_cast<void*>(address), GetLastError());
            break;
        }
        uintptr_t base = reinterpret_cast<uintptr_t>(m.BaseAddress);
        if (!m.RegionSize || base > UINTPTR_MAX - m.RegionSize) break;
        uintptr_t end = base + m.RegionSize;
        if (end <= address) break;
        if (Readable(m) && m.AllocationBase != self && m.AllocationBase != stackAllocation) {
            for (uintptr_t pos = address; pos < end; ) {
                if (GetTickCount64() >= deadline) break;
                size_t step = static_cast<size_t>((end - pos) < Block ? end - pos : Block);
                size_t length = static_cast<size_t>((end - pos) < sizeof(buffer) ? end - pos : sizeof(buffer));
                if (Read(pos, buffer, length)) {
                    total += step;
                    if (references) MatchReferences(pos, length, step, refs);
                    else MatchStrings(pos, length, step, m);
                }
                pos += step;
                if ((!references && hitCount == MaxHits) || refs >= 256) break;
            }
        }
        if ((!references && hitCount == MaxHits) || refs >= 256) break;
        address = end;
    }
    Log("scan_end references=%u bytes=%llu hits=%zu refs=%u errors=%u timeout=%u\n",
        references ? 1u : 0u, static_cast<unsigned long long>(total), hitCount, refs, errors,
        GetTickCount64() >= deadline ? 1u : 0u);
}

DWORD WINAPI Worker(void*) {
    // The client retains its startup import. Pin before scanning so later unloads cannot race us.
    HMODULE pinned;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
        reinterpret_cast<LPCWSTR>(&Worker), &pinned)) return 1;
    wchar_t path[MAX_PATH];
    DWORD length = GetModuleFileNameW(self, path, MAX_PATH);
    if (!length || length >= MAX_PATH) return 2;
    wchar_t* slash = wcsrchr(path, L'\\');
    if (!slash || static_cast<size_t>(slash - path) + 40 >= MAX_PATH) return 3;
    swprintf(slash + 1, 40, L"aioncl-camera-%lu.log", GetCurrentProcessId());
    logFile = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (logFile == INVALID_HANDLE_VALUE) {
        OutputDebugStringA("AionCL diagnostic could not create log");
        return 4;
    }
    MEMORY_BASIC_INFORMATION stack{};
    VirtualQuery(&stack, &stack, sizeof(stack));
    stackAllocation = stack.AllocationBase;
    Log("diagnostic=1 bits=%zu pid=%lu block=%zu read_only=1\n", sizeof(void*) * 8, GetCurrentProcessId(), Block);
    const DWORD waits[] = {2000, 6000, 12000};
    for (unsigned pass = 0; pass < 3; ++pass) {
        Sleep(waits[pass]);
        Log("pass=%u\n", pass);
        hitCount = 0;
        errors = 0;
        deadline = GetTickCount64() + 8000;
        Scan(false);
        deadline = GetTickCount64() + 8000;
        if (hitCount) Scan(true);
        FlushFileBuffers(logFile);
    }
    Log("complete=1\n");
    FlushFileBuffers(logFile);
    CloseHandle(logFile);
    return 0;
}
}

BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        self = module;
        // No scanning, loading, or waiting under the loader lock.
        HANDLE thread = CreateThread(nullptr, 0, Worker, nullptr, 0, nullptr);
        if (thread) CloseHandle(thread);
        else OutputDebugStringA("AionCL diagnostic could not create worker");
    }
    return TRUE;
}
