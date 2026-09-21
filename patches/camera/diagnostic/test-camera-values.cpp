#include "camera-values.hpp"
#include <assert.h>
#include <limits>

int main() {
    for (unsigned n = 0; n < 2; ++n) {
        camera::Values valid = camera::Desired(n);
        assert(camera::Valid(valid, n));
        auto broken = valid;
        broken.integer++;
        assert(!camera::Valid(broken, n));
        broken = valid;
        memset(broken.text, '7', sizeof(broken.text));
        assert(!camera::Valid(broken, n));
        broken = valid;
        strcpy(broken.text, "80secret");
        assert(!camera::Valid(broken, n));
        broken = valid;
        broken.floating = std::numeric_limits<float>::quiet_NaN();
        assert(!camera::Valid(broken, n));
        broken = valid;
        strcpy(broken.text, "1e999");
        assert(!camera::Valid(broken, n));
        broken = valid;
        strcpy(broken.text, "80.1");
        assert(!camera::Valid(broken, n));
    }
    camera::Values distance{12, 12.0f, "12.000000"};
    assert(camera::Valid(distance, 1));
    camera::Values fov{73, 73.0f, "73"};
    assert(camera::Valid(fov, 0));
    assert(camera::Valid(fov, 1));
    camera::Values maximum{100, 100.0f, "100"};
    assert(camera::Valid(maximum, 1));
    camera::Values excessive{101, 101.0f, "101"};
    assert(!camera::Valid(excessive, 1));
    assert(camera::Desired(0).integer == 80);
    assert(camera::Desired(1).integer == 100);
    assert(!camera::Valid(distance, 0));
    assert(!camera::Valid(distance, 2));
    puts("camera value validation: PASS");
}
