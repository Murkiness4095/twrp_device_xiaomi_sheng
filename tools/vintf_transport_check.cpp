// SPDX-License-Identifier: Apache-2.0
// Query the actual platform libvintf, including older inherited HIDL versions.
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vintf/parse_xml.h>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    std::ifstream file(argv[1]);
    std::string xml((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    android::vintf::HalManifest manifest;
    std::string error;
    if (!android::vintf::fromXml(&manifest, xml, &error)) {
        std::cerr << error << '\n';
        return 1;
    }
    bool passed = true;
    auto hidl = [&](const char* package, size_t major, size_t minor, const char* iface,
                    android::vintf::Transport expected) {
        auto actual = manifest.getHidlTransport(package, {major, minor}, iface, "default");
        bool ok = actual == expected;
        std::cout << package << '@' << major << '.' << minor << "::" << iface
                  << "/default: " << (ok ? "PASS" : "FAIL") << '\n';
        passed = ok && passed;
    };
    for (size_t minor : {0, 1, 2})
        hidl("android.hardware.boot", 1, minor, "IBootControl", android::vintf::Transport::HWBINDER);
    for (size_t minor : {0, 1})
        hidl("android.hardware.health", 2, minor, "IHealth", android::vintf::Transport::HWBINDER);
    hidl("android.hardware.gatekeeper", 1, 0, "IGatekeeper", android::vintf::Transport::HWBINDER);
    hidl("android.hardware.fastboot", 1, 1, "IFastboot", android::vintf::Transport::EMPTY);
    auto aidl = [&](const char* package, const char* iface) {
        bool ok = manifest.getAidlInstances(package, iface).count("default") == 1;
        std::cout << package << '.' << iface << "/default: " << (ok ? "PASS" : "FAIL") << '\n';
        passed = ok && passed;
    };
    aidl("android.hardware.security.keymint", "IKeyMintDevice");
    aidl("android.hardware.security.keymint", "IRemotelyProvisionedComponent");
    aidl("android.hardware.security.sharedsecret", "ISharedSecret");
    aidl("android.hardware.security.secureclock", "ISecureClock");
    return passed ? 0 : 1;
}
