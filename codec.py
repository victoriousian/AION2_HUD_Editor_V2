"""
Decode/Encode functions for AION2 DeviceSetting.dat files.
"""

import json
import copy
import struct
import re
from collections import OrderedDict

from constants import xor_crypt, HA_MAP, VA_MAP, HA_REV, VA_REV, DEFAULT_HUD_LAYOUT


# ═══════════════════════════════════════════════════════════════════════
#  Decode: .dat -> characters list
# ═══════════════════════════════════════════════════════════════════════

def _find_json_blocks(p2: bytes):
    """Find JSON blocks in Phase 2 raw bytes."""
    blocks = []
    prev_end = 0
    i = 0
    while i < len(p2):
        if p2[i] == 0x7B and i + 1 < len(p2) and p2[i + 1] in (0x0D, 0x0A):
            depth = 0; in_str = False; esc = False; end = -1
            for j in range(i, len(p2)):
                b = p2[j]
                if esc:
                    esc = False; continue
                if b == 0x5C and in_str:
                    esc = True; continue
                if b == 0x22:
                    in_str = not in_str
                if not in_str:
                    if b == 0x7B:
                        depth += 1
                    elif b == 0x7D:
                        depth -= 1
                        if depth == 0:
                            end = j + 1; break
            if end > 0:
                has_null = end < len(p2) and p2[end] == 0x00
                blocks.append({
                    'hdr_start': prev_end,
                    'json_start': i,
                    'json_end': end,
                    'has_null': has_null,
                })
                prev_end = end + (1 if has_null else 0)
                i = prev_end
                continue
        i += 1
    return blocks


def _format_chat(chat):
    return {
        "Type": chat.get("Type"),
        "Opened": chat.get("Opened"),
        "Size": chat.get("Size"),
        "HorizontalAnchor": HA_MAP.get(chat.get("HA"), chat.get("HA")),
        "VerticalAnchor": VA_MAP.get(chat.get("VA"), chat.get("VA")),
        "HorizontalOffset": chat.get("HO", 0),
        "VerticalOffset": chat.get("VO", 0),
    }


def _format_hud(elem):
    result = {
        "Tag": elem.get("Tag"),
        "HorizontalAnchor": HA_MAP.get(elem.get("HA"), elem.get("HA")),
        "VerticalAnchor": VA_MAP.get(elem.get("VA"), elem.get("VA")),
        "HorizontalOffset": elem.get("HO", 0),
        "VerticalOffset": elem.get("VO", 0),
        "Hidden": elem.get("Hidden", elem.get("Hide", False)),
        "Reverse": elem.get("Reverse", False),
    }
    sz = elem.get("Size")
    if sz and sz != [0, 0]:
        result["Size"] = sz
    return result


def decode_dat(dat_path, progress_cb=None):
    """Decode DeviceSetting.dat -> (global_settings, characters, encode_ctx)

    progress_cb(percent, message) is called for UI updates.
    """
    def _progress(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    _progress(0, "파일 읽는 중...")
    with open(dat_path, 'rb') as f:
        raw = f.read()

    _progress(10, "복호화 중...")
    file_header = raw[:4]
    decrypted = bytearray(xor_crypt(raw[4:]))

    _progress(25, "Phase 1 파싱 중 (전역 설정)...")
    # Phase 1: UTF-16LE JSON - brace-matching
    depth = 0
    in_str = False
    phase1_byte_end = 0
    i = 0
    while i < len(decrypted) - 1:
        ch16 = struct.unpack_from('<H', decrypted, i)[0]
        c = chr(ch16) if ch16 < 0x10000 else '?'
        if c == '"':
            in_str = not in_str
        elif not in_str:
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    phase1_byte_end = i + 2
                    break
        i += 2

    phase1_text = decrypted[:phase1_byte_end].decode('utf-16-le', errors='replace')
    main_json = json.loads(phase1_text, strict=False)

    global_settings = {
        "Version": main_json.get("Version"),
        "TextLanguage": main_json.get("TextLanguage"),
        "LastSelectedServerInfo": main_json.get("LastSelectedServerInfo"),
        "Resolution": {
            "Fullscreen": f"{main_json.get('LastFullscreenResolutionX')}x{main_json.get('LastFullscreenResolutionY')}",
            "Windowed": f"{main_json.get('LastWindowedResolutionX')}x{main_json.get('LastWindowedResolutionY')}",
            "RefreshRate": main_json.get("GraphicDisplayRefreshRate"),
        },
        "GraphicTemplate": main_json.get("GraphicTemplate"),
        "Upscaler": main_json.get("GraphicUpscaler"),
        "UpscalerQuality": main_json.get("GraphicUpscalerQuality"),
    }

    _progress(40, "Phase 2 파싱 중 (캐릭터 HUD)...")
    phase2 = bytes(decrypted[phase1_byte_end:])
    json_blocks = _find_json_blocks(phase2)

    _progress(55, "캐릭터 데이터 추출 중...")
    block_data = []
    block_meta = []
    for idx, block in enumerate(json_blocks):
        hdr = phase2[block['hdr_start']:block['json_start']]
        raw_json = phase2[block['json_start']:block['json_end']]
        obj = json.loads(raw_json.decode('utf-8', errors='replace'), strict=False)

        is_section_boundary = len(hdr) >= 24
        if is_section_boundary and len(hdr) >= 16:
            char_id = struct.unpack_from('<I', hdr, 12)[0]
        elif len(hdr) >= 4:
            char_id = struct.unpack_from('<I', hdr, 0)[0]
        else:
            char_id = 0

        block_data.append({
            'idx': idx, 'char_id': char_id, 'obj': obj,
            'mc': obj.get('MultiChat', []),
            'he': obj.get('HudEdit', []),
            'hg': obj.get('HudEditGroup', []),
        })
        block_meta.append({
            'idx': idx,
            'header': bytearray(hdr),
            'is_section_boundary': is_section_boundary,
            'char_id': char_id,
            'original_obj': obj,
            'original_json_raw': raw_json,
        })

    _progress(70, "캐릭터별 그룹화 중...")
    characters_map = OrderedDict()
    for bd in block_data:
        cid = bd['char_id']
        if cid is None or cid == 0:
            continue
        if cid not in characters_map:
            characters_map[cid] = []
        characters_map[cid].append(bd)

    _progress(85, "캐릭터 JSON 변환 중...")
    characters = []
    for cid, blocks in characters_map.items():
        hex_id = f"0x{cid:08X}"
        all_mc, all_he, all_hg = [], [], []
        for bd in blocks:
            all_mc.extend(bd['mc'])
            all_he.extend(bd['he'])
            all_hg.extend(bd['hg'])

        char_obj = {"CharacterID": cid, "CharacterID_Hex": hex_id}
        if all_mc:
            seen_types = set()
            unique_mc = []
            for c in all_mc:
                ct = c.get("Type")
                if ct not in seen_types:
                    seen_types.add(ct)
                    unique_mc.append(c)
            char_obj["ChatTabs"] = [_format_chat(c) for c in unique_mc]
        if all_he:
            char_obj["HudElements"] = [_format_hud(e) for e in all_he]
        if all_hg:
            char_obj["HudGroups"] = all_hg

        # Apply default HUD layout for characters with no HUD data
        if not char_obj.get("HudElements"):
            char_obj["HudElements"] = copy.deepcopy(DEFAULT_HUD_LAYOUT)

        characters.append(char_obj)

    _progress(100, "디코딩 완료!")

    original_characters = copy.deepcopy(characters)

    encode_ctx = {
        'raw_bytes': raw,
        'file_header': file_header,
        'decrypted': bytes(decrypted),
        'phase1_byte_end': phase1_byte_end,
        'block_meta': block_meta,
        'main_json': main_json,
        'original_characters': original_characters,
    }

    return global_settings, characters, encode_ctx


# ═══════════════════════════════════════════════════════════════════════
#  Encode: characters list -> .dat
# ═══════════════════════════════════════════════════════════════════════

def _format_json_phase2(obj: dict) -> bytes:
    """Format Phase 2 JSON block matching AION2 style."""
    text = json.dumps(obj, indent='\t', ensure_ascii=False, separators=(',', ': ')
                      ).replace('\n', '\r\n')
    def collapse_array(m):
        inner = m.group(1)
        values = [v.strip() for v in re.split(r'\r?\n', inner) if v.strip()]
        values = [v.rstrip(',') for v in values]
        return '[ ' + ', '.join(values) + ' ]'
    text = re.sub(
        r'\[\r\n(\t+(?:[\d.eE+\-]+,?\r\n)*\t*[\d.eE+\-]+\r\n\t*)\]',
        collapse_array, text
    )
    return text.encode('utf-8')


def _chat_to_game(chat: dict) -> dict:
    result = {}
    if 'Opened' in chat:
        result['Opened'] = chat['Opened']
    if 'Type' in chat:
        result['Type'] = chat['Type']
    if 'Size' in chat:
        result['Size'] = chat['Size']
    if 'HorizontalAnchor' in chat:
        result['HA'] = HA_REV.get(chat['HorizontalAnchor'], chat['HorizontalAnchor'])
    elif 'HA' in chat:
        result['HA'] = chat['HA']
    if 'VerticalAnchor' in chat:
        result['VA'] = VA_REV.get(chat['VerticalAnchor'], chat['VerticalAnchor'])
    elif 'VA' in chat:
        result['VA'] = chat['VA']
    if 'HorizontalOffset' in chat:
        result['HO'] = chat['HorizontalOffset']
    elif 'HO' in chat:
        result['HO'] = chat['HO']
    if 'VerticalOffset' in chat:
        result['VO'] = chat['VerticalOffset']
    elif 'VO' in chat:
        result['VO'] = chat['VO']
    return result


def _hud_to_game(elem: dict) -> dict:
    result = {}
    if 'Tag' in elem:
        result['Tag'] = elem['Tag']
    if 'HorizontalAnchor' in elem:
        result['HA'] = HA_REV.get(elem['HorizontalAnchor'], elem['HorizontalAnchor'])
    elif 'HA' in elem:
        result['HA'] = elem['HA']
    if 'VerticalAnchor' in elem:
        result['VA'] = VA_REV.get(elem['VerticalAnchor'], elem['VerticalAnchor'])
    elif 'VA' in elem:
        result['VA'] = elem['VA']
    if 'HorizontalOffset' in elem:
        result['HO'] = elem['HorizontalOffset']
    elif 'HO' in elem:
        result['HO'] = elem['HO']
    if 'VerticalOffset' in elem:
        result['VO'] = elem['VerticalOffset']
    elif 'VO' in elem:
        result['VO'] = elem['VO']
    if 'Size' in elem:
        result['Size'] = elem['Size']
    if 'Hidden' in elem:
        result['Hide'] = elem['Hidden']
    elif 'Hide' in elem:
        result['Hide'] = elem['Hide']
    if 'Reverse' in elem:
        result['Reverse'] = elem['Reverse']
    return result


def encode_dat(characters, encode_ctx, output_path, progress_cb=None):
    """Encode characters back to DeviceSetting.dat format.

    Uses encode_ctx from decode_dat() to preserve original binary structure.
    """
    def _progress(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    _progress(0, "인코딩 준비 중...")

    file_header = encode_ctx['file_header']
    decrypted = encode_ctx['decrypted']
    phase1_byte_end = encode_ctx['phase1_byte_end']
    block_meta = encode_ctx['block_meta']
    original_characters = encode_ctx.get('original_characters', [])

    # Build char_id -> modified data mapping
    modified = {}
    for char in characters:
        cid = char.get('CharacterID', 0)
        if cid:
            modified[cid] = char

    # Detect which characters were actually changed by user
    orig_char_map = {}
    for oc in original_characters:
        cid = oc.get('CharacterID', 0)
        if cid:
            orig_char_map[cid] = oc

    changed_char_ids = set()
    for cid, mod_char in modified.items():
        orig_char = orig_char_map.get(cid)
        if orig_char is None or mod_char != orig_char:
            changed_char_ids.add(cid)

    _progress(15, "블록 데이터 매핑 중...")

    # Build new JSON for each block
    char_block_counter = {}
    for bm in block_meta:
        cid = bm['char_id']
        orig = bm['original_obj']

        if cid not in char_block_counter:
            char_block_counter[cid] = 0
        occurrence = char_block_counter[cid]
        char_block_counter[cid] += 1

        # If this character wasn't changed, preserve original raw bytes
        if cid not in changed_char_ids:
            bm['new_obj'] = orig
            bm['modified'] = False
            continue

        if cid in modified:
            mod = modified[cid]
            has_mc_orig = bool(orig.get('MultiChat'))
            has_he_orig = bool(orig.get('HudEdit'))
            has_hg_orig = 'HudEditGroup' in orig

            all_mc, all_he, all_hg = [], [], []
            for key, val in mod.items():
                if key.endswith('_MultiChat') or key == 'ChatTabs':
                    for item in val:
                        all_mc.append(_chat_to_game(item))
                elif key.endswith('_HudEdit') or key == 'HudElements':
                    for item in val:
                        all_he.append(_hud_to_game(item))
                elif key.endswith('_HudEditGroup') or key == 'HudGroups':
                    all_hg.extend(val)

            new_obj = {"Version": orig.get("Version", 102)}
            if occurrence == 0:
                # First block for this character: put ALL data here
                if all_mc:
                    new_obj['MultiChat'] = all_mc
                if all_he:
                    new_obj['HudEdit'] = all_he
                if all_hg:
                    new_obj['HudEditGroup'] = all_hg
            # Subsequent blocks for same char: leave as Version-only

            bm['new_obj'] = new_obj
            bm['modified'] = True
        else:
            bm['new_obj'] = orig
            bm['modified'] = False

    _progress(40, "Phase 1 보존 중...")
    new_phase1 = bytes(decrypted[:phase1_byte_end])

    _progress(55, "Phase 2 재구성 중...")
    new_phase2 = bytearray()
    total = len(block_meta)
    for idx, bm in enumerate(block_meta):
        header = bytearray(bm['header'])
        if not bm.get('modified', False):
            json_with_null = bm['original_json_raw'] + b'\x00'
        else:
            json_bytes = _format_json_phase2(bm['new_obj'])
            json_with_null = json_bytes + b'\x00'

        payload_size = len(json_with_null)
        if len(header) >= 4:
            struct.pack_into('<I', header, len(header) - 4, payload_size)

        new_phase2.extend(header)
        new_phase2.extend(json_with_null)
        _progress(55 + int(35 * (idx + 1) / total), f"블록 {idx+1}/{total} 인코딩 중...")

    _progress(92, "암호화 중...")
    new_payload = new_phase1 + bytes(new_phase2)
    encrypted = xor_crypt(new_payload)

    _progress(97, "파일 저장 중...")
    with open(output_path, 'wb') as f:
        f.write(file_header)
        f.write(encrypted)

    _progress(100, "인코딩 완료!")
    return 4 + len(encrypted)
