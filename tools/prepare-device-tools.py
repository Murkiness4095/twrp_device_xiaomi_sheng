#!/usr/bin/env python3
"""Generate device-local UI/languages using upstream's custom-theme hooks.

Reads the selected frontend; never writes to bootable/recovery or vendor/twrp.
"""
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape


def language_init(output):
    # Recovery deletes customlanguages/ before loading the built-in theme.
    # Install device-local copies into the real language directory during init,
    # before recovery starts; this also avoids Soong's theme-copy ordering.
    files = sorted((output/'languages').glob('*.xml'))
    lines = ['# Generated device-local language overlay; no partition writes.', 'on init']
    lines += ['    copy /system/etc/sheng-device-languages/'+p.name+' /twres/languages/'+p.name for p in files]
    (output/'init.recovery.sheng-tools.rc').write_text('\n'.join(lines)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    recovery = source/'bootable/recovery'
    tree = Path(__file__).resolve().parent.parent
    if (recovery/'orangefox.mk').is_file():
        output = tree/'generated/orangefox'
        (output/'languages').mkdir(parents=True, exist_ok=True)
        theme = recovery/'gui/theme/portrait_hdpi'
        ui = (theme/'ui.xml').read_text()
        advanced = (theme/'pages/advanced.xml').read_text()
        start = advanced.index('<page name="fox_modules">')
        end = advanced.index('</page>', start)
        page = advanced[start:end]
        anchor = '<listitem name="{@module_of_set}">'
        entry = '''<listitem name="{@disable_avb2=Disable vbmeta AVB2.0}">
                    <icon res="build"/>
                    <action function="set">tw_back=fox_modules</action>
                    <action function="set">tw_action=disableAVB2</action>
                    <action function="set">tw_action_param=</action>
                    <action function="set">tw_text1={@disable_avb2_confirm=Disable vbmeta AVB2.0?}</action>
                    <action function="set">tw_action_text1={@disabling_AVB2=Disabling vbmeta AVB2.0...}</action>
                    <action function="set">tw_complete_text1={@disabling_AVB2_complete=vbmeta AVB2.0 disabled!}</action>
                    <action function="set">tw_slider_text={@swipe_to_confirm=Swipe to Confirm}</action>
                    <action function="page">confirm_action</action>
                </listitem>
                '''
        if page.count(anchor) != 1:
            raise RuntimeError('Unsupported OrangeFox Fox plugins list')
        page = page.replace(anchor, entry+anchor)
        advanced = advanced[:start]+page+advanced[end:]
        inner = advanced[advanced.index('<recovery>')+len('<recovery>'):advanced.rindex('</recovery>')]
        # Keep all native pages/styles; override only the device-local copy of
        # advanced.xml, with the button calling the existing native action.
        include = '<xml name="/twres/pages/advanced.xml"/>'
        if ui.count(include) != 1:
            raise RuntimeError('Unsupported OrangeFox advanced include')
        ui = ui.replace(include, '')
        ui = ui.replace('</recovery>', inner+'\n</recovery>')
        ET.fromstring(ui)
        (output/'ui.xml').write_text('\n'.join(line.rstrip() for line in ui.splitlines())+'\n')
        supplements = json.loads((tree/'tools/device-tools-orangefox-translations.json').read_text())
        files = list((recovery/'gui/theme/common/languages').glob('*.xml')) + list((recovery/'gui/theme/extra-languages/languages').glob('*.xml'))
        for path in files:
            text = path.read_text()
            if 'name="auto_disable_avb2"' in text:
                continue
            strings = supplements[path.stem]
            extra = '\n'.join('        <string name="'+key+'">'+escape(value)+'</string>' for key,value in strings.items())
            text = text.replace('</resources>', extra+'\n\t</resources>')
            ET.fromstring(text)
            (output/'languages'/path.name).write_text(text)
        language_init(output)
        print('OrangeFox: native AVB action in Fox plugins; original auto option and translations retained')
        return
    output = tree/'generated/twrp'
    output.mkdir(parents=True, exist_ok=True)
    upstream = recovery/'gui/theme'
    ui = (upstream/'landscape_hdpi/ui.xml').read_text()
    common = (upstream/'common/landscape.xml').read_text()
    start = common.index('<page name="advanced">')
    end = common.index('</page>', start)
    advanced = common[start:end]
    anchor = '<listbox style="advanced_listbox">'
    at = advanced.index('>', advanced.index('<placement', advanced.index(anchor))) + 1
    entries = '''
                <listitem name="{@sheng_disable_avb=Disable AVB 2.0 verification}">
                    <actions>
                        <action function="set">tw_back=advanced</action>
                        <action function="set">tw_action=cmd</action>
                        <action function="set">tw_action_param=/system/bin/sheng-avb --disable</action>
                        <action function="set">tw_text1={@sheng_disable_avb=Disable AVB 2.0 verification}</action>
                        <action function="set">tw_text2={@boot_slot_a=Slot A} + {@boot_slot_b=Slot B}: vbmeta + vbmeta_system</action>
                        <action function="set">tw_text3=</action>
                        <action function="set">tw_text4=</action>
                        <action function="set">tw_action_text1={@sheng_disable_avb=Disable AVB 2.0 verification}</action>
                        <action function="set">tw_complete_text1={@sheng_disable_avb=Disable AVB 2.0 verification}</action>
                        <action function="set">tw_slider_text={@swipe_to_confirm=Swipe to Confirm}</action>
                        <action function="page">confirm_action</action>
                    </actions>
                </listitem>
                <listitem name="{@install_btn=Install} Magisk 30.7">
                    <actions>
                        <action function="queueclear"/>
                        <action function="set">tw_selectimage=0</action>
                        <action function="set">tw_file=Magisk 30.7</action>
                        <action function="set">tw_filename=/FFiles/OF_Magisk/Magisk.zip</action>
                        <action function="queuezip"/>
                        <action function="page">flash_confirm</action>
                    </actions>
                </listitem>'''
    advanced = advanced[:at] + entries + advanced[at:]
    common = common[:start] + advanced + common[end:]
    # The upstream custom-theme hook copies one XML file. Inline the shared
    # layout so its Advanced page is overridden without replacing source files.
    inner = common[common.index('<recovery>')+len('<recovery>'):common.rindex('</recovery>')]
    ui, count = re.subn(r'<include>\s*<xmlfile name="landscape.xml"/>\s*</include>',
                        lambda _: inner, ui)
    if count != 1:
        raise RuntimeError('Unsupported TWRP theme include')
    version = re.search(r'#define TW_THEME_VERSION (\d+)', (recovery/'variables.h').read_text()).group(1)
    ui = ui.replace('{themeversion}', version)
    # This tree uses the default status positions and top alignment.
    for placeholder, value in [('battery_pos','0'), ('cpu_pos','0'),
                               ('clock_12_pos','0'), ('clock_24_pos','0'),
                               ('statusicons_align','%status_topalign_header_y%')]:
        ui = ui.replace('{'+placeholder+'}', value)
    document = ET.fromstring(ui)
    # PageSet reads first_node for each section; combine sections that used to
    # be in separate include files, preserving their original child order.
    for tag in ('resources', 'variables', 'styles', 'templates', 'pages'):
        sections = document.findall(tag)
        for section in sections[1:]:
            sections[0].extend(list(section))
            document.remove(section)
    ET.indent(document, space='\t')
    (output/'ui.xml').write_text('<!-- Device-local customization of the pinned TeamWin theme; upstream notices retained. -->\n'+ET.tostring(document, encoding='unicode')+'\n')
    translations = json.loads((tree/'tools/device-tools-translations.json').read_text())
    languages = sorted((upstream/'common/languages').glob('*.xml')) + sorted((upstream/'extra-languages/languages').glob('*.xml'))
    if {p.stem for p in languages} != set(translations):
        raise RuntimeError('Every bundled language must have device tool translations')
    custom = output/'languages'
    custom.mkdir(exist_ok=True)
    for language in languages:
        text = language.read_text()
        # The pinned German file has a missing separator between attributes.
        # Correct only the device-local copy used by the custom-language hook.
        text = text.replace('name="install_reboot"version=', 'name="install_reboot" version=')
        strings = translations[language.stem]
        extra = '\n'.join('        <string name="'+key+'">'+escape(value)+'</string>'
                          for key, value in zip(('sheng_disable_avb',), strings))
        text = text.replace('</resources>', extra+'\n\t</resources>')
        ET.fromstring(text)
        (custom/language.name).write_text(text)
    language_init(output)
    report = {'frontend':'twrp','languages':len(languages),'upstream_commit':
              '5c3d206a5eeb3d446bcda8248a405a4b278bab5c',
              'ui_sha256':hashlib.sha256((output/'ui.xml').read_bytes()).hexdigest(),
              'upstream_source_modified':False}
    (output/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
