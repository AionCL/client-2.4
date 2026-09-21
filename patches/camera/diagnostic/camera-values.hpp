#pragma once
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

namespace camera {
struct Values {
    int32_t integer;
    float floating;
    char text[32];
};
static_assert(sizeof(Values) == 40);

inline bool Valid(const Values& value, unsigned name) {
    if (name > 1 || !memchr(value.text, 0, sizeof(value.text))) return false;
    size_t length = strlen(value.text);
    if (!length) return false;
    for (size_t i = 0; i < length; ++i) {
        char c = value.text[i];
        if ((c < '0' || c > '9') && c != '.' && c != '+' && c != '-') return false;
    }
    char* end = nullptr;
    float parsed = strtof(value.text, &end);
    float low = name == 0 ? 30.0f : 1.0f;
    float high = name == 0 ? 170.0f : 50.0f;
    return end == value.text + length && isfinite(value.floating) && isfinite(parsed) &&
        value.floating >= low && value.floating <= high &&
        value.integer == static_cast<int32_t>(value.floating) && fabsf(parsed - value.floating) < 0.001f;
}

inline Values Desired(unsigned name) {
    Values result{};
    result.integer = name == 0 ? 80 : 30;
    result.floating = static_cast<float>(result.integer);
    snprintf(result.text, sizeof(result.text), "%ld", static_cast<long>(result.integer));
    return result;
}
}
