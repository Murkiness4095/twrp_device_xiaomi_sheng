#!/usr/bin/env python3
"""Apply the required Android 12.1 input/copy fixes to either recovery frontend.

This changes upstream recovery code, not the device hardware configuration.
It deliberately does not change the DRM mode-selection policy.
"""
import argparse
import shutil
from pathlib import Path


def change(text, old, new, count=1):
    if new in text:
        return text
    if text.count(old) != count:
        raise RuntimeError('Unsupported recovery source context: '+old[:80])
    return text.replace(old, new)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    a = p.parse_args()
    recovery = a.source/'bootable/recovery'
    updates = {}
    makefile=a.source/'build/make/core/Makefile'
    if makefile.is_file():
        zstd=shutil.which('zstd')
        if not zstd:
            raise RuntimeError('Install the host zstd package for the embedded-kernel ramdisk')
        updates[makefile]=change(makefile.read_text(), 'else ifeq ($(BOARD_RAMDISK_USE_LZMA),true)',
                                 'else ifeq ($(BOARD_RAMDISK_USE_ZSTD),true)\n'
                                 'COMPRESSION_COMMAND_DEPS := '+zstd+'\n'
                                 'COMPRESSION_COMMAND := '+zstd+' -15 -T4 --long=23 -q -c\n'
                                 'RAMDISK_EXT := .zst\n'
                                 'else ifeq ($(BOARD_RAMDISK_USE_LZMA),true)')
    events = recovery/'minuitwrp/events.cpp'
    text = events.read_text()
    text = change(text, '                touchReleaseOnNextSynReport = 1;',
                  '''                // Preserve authoritative tracking-ID release in this report.
                if (touchReleaseOnNextSynReport != 2)
                    touchReleaseOnNextSynReport = 1;''', 2)
    text = change(text, 'strdup(EXPAND(TW_INPUT_BLACKLIST))', 'strdup(TW_INPUT_BLACKLIST)')
    text = change(text, 'if (strcmp(e->deviceName, blacklist) == 0) {',
                  '''if (strcmp(e->deviceName, blacklist) == 0 ||
            (strcmp(blacklist, "NVTCapacitivePen") == 0 &&
             strncmp(e->deviceName, blacklist, strlen(blacklist)) == 0)) {''')
    updates[events] = text
    # Coordinates are zero-based, including the horizontal tablet transform.
    updates[events] = change(updates[events], 'y = gr_fb_height() - y;',
                             'y = gr_fb_height() - 1 - y;')
    prebuilt = recovery/'prebuilt/Android.mk'
    updates[prebuilt] = change(prebuilt.read_text(), 'LOCAL_MODULE := relink_libraries\n',
                              '''LOCAL_MODULE := relink_libraries
# A changed library implementation must invalidate the ramdisk copy timestamp.
LOCAL_ADDITIONAL_DEPENDENCIES += $(TARGET_OUT_SHARED_LIBRARIES)/libminuitwrp.so
''')
    gui = recovery/'gui/gui.cpp'
    text = gui.read_text()
    if 'const bool got_event = input_handler.processInput(input_timeout_ms); // drain input within the frame budget' not in text:
        text = change(text,
                      '\t\tbool got_event = input_handler.processInput(input_timeout_ms); // get inputs but don\'t send drag notices',
                      '\t\tinput_handler.processInput(input_timeout_ms); // drain input within the frame budget')
    text = change(text, '''		// This is really 2 or TW_FRAMERATE times per second
		// As long as we get events, increase the timeout so we can catch up with input
		long timeout = got_event ? 500000000 : (1.0 / TW_FRAMERATE * 1000000000);''',
                  '''		// Continuous touch events must not defer drawing for half a second.
		const long timeout = 1000000000L / TW_FRAMERATE;''')
    text = change(text, 'input_timeout_ms = idle_frames > 15 ? 1000 : 0;',
                  'input_timeout_ms = idle_frames > 15 ? (1000 + TW_FRAMERATE - 1) / TW_FRAMERATE : 0;')
    text = change(text,
                  'input_handler.processInput(input_timeout_ms); // drain input within the frame budget',
                  'const bool got_event = input_handler.processInput(input_timeout_ms); // drain input within the frame budget')
    text = change(text,
                  '\n\tdo\n\t{\n\t\tconst bool got_event = input_handler.processInput(input_timeout_ms);',
                  '''
\t// Rendering can exceed one frame on this high-resolution panel. Its time
\t// must not consume the budget for draining the next batch of raw input.
\tclock_gettime(CLOCK_MONOTONIC, &lastCall);
\tdo
\t{
\t\tconst bool got_event = input_handler.processInput(input_timeout_ms);''')
    text = change(text, 'if (diff.tv_sec || diff.tv_nsec > timeout)',
                  'if (!got_event || diff.tv_sec || diff.tv_nsec >= timeout)')
    updates[gui] = text
    installer = recovery/'twrpinstall/twinstall.cpp'
    warning = 'gui_warn("flash_ab_reboot=To flash additional zips, please reboot recovery to switch to the updated slot.");'
    if installer.is_file() and warning in installer.read_text():
        updates[installer] = change(installer.read_text(),
            '\t\t\t'+warning,
            '\t\t\tif (ret_val == INSTALL_SUCCESS)\n\t\t\t\t'+warning)
        marker='DataManager::SetValue(FOX_ZIP_INSTALLER_CODE, 1); // mark as custom ROM install'
        if marker in updates[installer]:
            updates[installer]=change(updates[installer], '\t\t\t'+marker,
                '\t\t\tif (ret_val == INSTALL_SUCCESS)\n\t\t\t\t'+marker)
    manager = recovery/'partitionmanager.cpp'
    updates[manager] = change(manager.read_text(),
        '''\t\t\tif ((*iter)->Can_Flash_Img && (*iter)->Is_Present) {
\t\t\t\tstruct PartitionList part;
\t\t\t\tpart.Display_Name = (*iter)->Backup_Display_Name;''',
        '''\t\t\tif ((*iter)->Can_Flash_Img && (*iter)->Is_Present) {
\t\t\t\tstruct PartitionList part;
\t\t\t\t// Show exact partition identifiers in the image target picker.
\t\t\t\tpart.Display_Name = (*iter)->Mount_Point.substr(1);
\t\t\t\tfor (char& letter : part.Display_Name)
\t\t\t\t\tif (letter >= 'A' && letter <= 'Z') letter += 'a' - 'A';''')
    # Android 12.1 vendor/twrp does not export this flag to the Soong GUI module.
    vendor = a.source/'vendor/twrp'
    if (vendor/'build/soong/Android.bp').is_file():
        bp = vendor/'build/soong/Android.bp'
        text = change(bp.read_text(), '        "tw_use_samsung_haptics",',
                      '        "tw_use_samsung_haptics",\n        "tw_no_haptics",')
        text = change(text, '        tw_brightness_path: {',
                      '        tw_no_haptics: {\n             cflags: ["-DTW_NO_HAPTICS"]\n        },\n        tw_brightness_path: {')
        updates[bp] = text
        soong = vendor/'config/BoardConfigSoong.mk'
        text = change(soong.read_text(), '    tw_use_samsung_haptics \\\n',
                      '    tw_use_samsung_haptics \\\n    tw_no_haptics \\\n')
        text = change(text,
                      'SOONG_CONFIG_twrpGlobalVars_tw_use_samsung_haptics := $(TW_USE_SAMSUNG_HAPTICS)\n',
                      'SOONG_CONFIG_twrpGlobalVars_tw_use_samsung_haptics := $(TW_USE_SAMSUNG_HAPTICS)\nSOONG_CONFIG_twrpGlobalVars_tw_no_haptics := $(TW_NO_HAPTICS)\n')
        # Some OrangeFox setup scripts add this include to the shared vendor tree.
        # Make it optional when switching the same checkout to the TWRP frontend.
        if 'include bootable/recovery/orangefox_soong.mk' in text:
            text = change(text, 'include bootable/recovery/orangefox_soong.mk',
                          '-include bootable/recovery/orangefox_soong.mk')
        updates[soong] = text
    # This GUI object exists only in OrangeFox. No OrangeFox code is injected
    # into a TWRP checkout.
    battery = recovery/'gui/battery.cpp'
    if (recovery/'orangefox.mk').is_file() and battery.is_file():
        text = battery.read_text()
        for field, attr, default, axis in [('mDX','dx',0,'X'),('mDY','dy',0,'Y'),
                                           ('mDW','dw',32,'X'),('mDH','dh',18,'Y'),
                                           ('mCX','x',0,'X'),('mCY','y',0,'Y')]:
            text = change(text, f'{field} = LoadAttrIntScale{axis}(child, "{attr}", {default});',
                          f'{field} = scale_theme_min(LoadAttrInt(child, "{attr}", {default}));')
        text = change(text, '\tSetPlacement(TOP_LEFT);', '''	SetPlacement(TOP_LEFT);
	ImageResource* layoutImage = mStateMode ? mImg100 : mImg;
	if (layoutImage && layoutImage->GetResource()) {
		mRenderW = layoutImage->GetWidth();
		mRenderH = layoutImage->GetHeight();
	}''')
        text = change(text, 'gr_blit(finalImage->GetResource(), 0, 0, mRenderW, mRenderH, mRenderX - iconRealX, mRenderY);',
                      'gr_blit(finalImage->GetResource(), 0, 0, finalImage->GetWidth(), finalImage->GetHeight(), mRenderX - iconRealX, mRenderY);')
        updates[battery] = text
        # About-card holes are part of an aspect-preserving image. Anchor each
        # portrait to its card and scale the insets with that same image scale.
        gui_image = recovery/'gui/image.cpp'
        text = change(gui_image.read_text(),
                      '\tLoadPlacement(FindNode(node, "placement"), &mRenderX, &mRenderY, NULL, NULL, &mPlacement);',
                      '''\tLoadPlacement(FindNode(node, "placement"), &mRenderX, &mRenderY, NULL, NULL, &mPlacement);
\txml_node<>* imagePlacement = FindNode(node, "placement");
\tmRenderX += scale_theme_min(LoadAttrInt(imagePlacement, "offsetx", 0));
\tmRenderY += scale_theme_min(LoadAttrInt(imagePlacement, "offsety", 0));''')
        updates[gui_image] = text
        # Keep the user's original PNG intact; normalize only its loaded surface.
        resources = recovery/'gui/resources.cpp'
        text = change(resources.read_text(),
                      '\tCheckAndScaleImage(temp_surface, &mSurface, retain_aspect);',
                      '''\tconst int requestedWidth = LoadAttrInt(node, "width", 0);
\tif (temp_surface && requestedWidth > 0) {
\t\tconst float sourceScale = static_cast<float>(requestedWidth) / gr_get_width(temp_surface);
\t\tgr_surface resized = nullptr;
\t\tif (res_scale_surface(temp_surface, &resized, sourceScale, sourceScale) == 0)
\t\t\ttemp_surface = resized;
\t}
\tCheckAndScaleImage(temp_surface, &mSurface, retain_aspect);''')
        updates[resources] = text
        settings = recovery/'gui/theme/portrait_hdpi/pages/settings.xml'
        text = settings.read_text()
        for row in range(1, 5):
            text = change(text,
                          f'<placement x="%card_img_x%" y="%card_img{row}_y%"/>',
                          f'<placement x="0" y="%card{row}_y%" offsetx="%card_img_x%" offsety="72"/>')
        updates[settings] = text
        image_resources = recovery/'gui/theme/portrait_hdpi/resources/images.xml'
        updates[image_resources] = change(image_resources.read_text(),
                    '<image name="maintainer_img" filename="Default/About/maintainer" retainaspect="1"/>',
                    '<image name="maintainer_img" filename="Default/About/maintainer" width="192" retainaspect="1"/>')
        avatar = Path(__file__).resolve().parent.parent/'assets/maintainer-original.png'
        if not avatar.is_file():
            raise FileNotFoundError('Maintainer avatar asset missing: '+str(avatar))
    # Check every source context before writing any of the planned edits.
    for path, text in updates.items():
        if path.read_text() != text:
            path.write_text(text)
    if (recovery/'orangefox.mk').is_file() and battery.is_file():
        shutil.copy2(avatar, recovery/'gui/theme/portrait_hdpi/images/Default/About/maintainer.png')
    print('Applied common input/frame-budget/runtime-copy fixes; OrangeFox battery fix when present')


if __name__ == '__main__':
    main()
