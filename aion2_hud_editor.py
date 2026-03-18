#!/usr/bin/env python
"""
AION2 HUD Editor
==================
Standalone application that decodes DeviceSetting.dat, provides a visual HUD
preview with editing capabilities, and re-encodes back to .dat format.

Flow:
    Launch  ->  Select .dat file  ->  Decode (with progress UI)  ->  Preview
    Preview ->  Edit / Copy / Import JSON  ->  Save back to .dat (with backup)

Default .dat path:
    C:\\Users\\{user}\\AppData\\Local\\AION2\\Saved\\PersistentDownloadDir\\UserSetting\\DeviceSetting.dat
"""

import sys
import os
import json
import copy
import struct
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
#  Constants & Crypto
# ═══════════════════════════════════════════════════════════════════════

XOR_KEY = bytes([0x25, 0xA8, 0x7E, 0x91])

HA_MAP = {1: "Left", 2: "Center", 3: "Right"}
VA_MAP = {1: "Top", 2: "Center", 3: "Bottom"}
HA_REV = {"Left": 1, "Center": 2, "Right": 3}
VA_REV = {"Top": 1, "Center": 2, "Bottom": 3}


def xor_crypt(data: bytes) -> bytes:
    return bytes([b ^ XOR_KEY[i % 4] for i, b in enumerate(data)])


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
    """Decode DeviceSetting.dat -> (global_settings, characters, raw_dat_bytes, phase1_end, block_meta)

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
    # Build block data
    from collections import OrderedDict
    block_data = []
    block_meta = []  # for encoder
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
            char_obj["ChatTabs"] = [_format_chat(c) for c in all_mc]
        if all_he:
            char_obj["HudElements"] = [_format_hud(e) for e in all_he]
        if all_hg:
            char_obj["HudGroups"] = all_hg
        characters.append(char_obj)

    _progress(100, "디코딩 완료!")

    # Store raw data needed for encoding
    # Keep a deep copy of original characters for modification detection
    import copy as _copy
    original_characters = _copy.deepcopy(characters)

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


# ═══════════════════════════════════════════════════════════════════════
#  HUD Preview Constants & Translations
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_HUD_SIZES = {
    "Minimap":                   (200, 200),
    "Chat":                      (400, 300),
    "Target":                    (280, 60),
    "UserInfo_HP":               (200, 20),
    "UserInfo_MP":               (200, 20),
    "UserInfo_AbnormalBtn":      (30, 30),
    "UserInfo_AbnormalBuff":     (200, 30),
    "UserInfo_AbnormalDeBuff":   (200, 30),
    "UserInfo_Class":            (60, 60),
    "QuickSlotItem1":            (270, 50),
    "QuickSlotItem2":            (270, 50),
    "AutoSlotSealStone":         (50, 50),
    "AutoSlotPotion":            (50, 50),
    "PartyForce":                (180, 200),
    "NPCTalk_BossCaption":       (400, 40),
    "NPCTalk_Caption":           (400, 60),
    "NPCTalk_FocusCameraTalk":   (400, 60),
    "NPCTalk_OnelineCaption":    (400, 30),
    "GetItemList":               (200, 150),
    "GatherProgress":            (200, 30),
    "CooltimeSkill":             (300, 30),
    "Indicator":                 (30, 400),
    "Timer":                     (150, 40),
    "GaugeBossWideSkill":        (300, 30),
    "AutoMove":                  (200, 20),
    "Gauge":                     (300, 30),
    "CounterAttack":             (80, 80),
    "VoiceChat":                 (100, 30),
    "FieldEventEntrance":        (180, 40),
    "KeyGuide":                  (200, 30),
    "GaugeBossSkill":            (300, 30),
}

CHAT_BASE_SIZE = (380, 250)

CATEGORY_COLORS = {
    "Chat":        ("#2196F3", "#BBDEFB"),
    "QuickSlot":   ("#FF9800", "#FFE0B2"),
    "AutoSlot":    ("#FF5722", "#FFCCBC"),
    "UserInfo":    ("#4CAF50", "#C8E6C9"),
    "NPCTalk":     ("#9C27B0", "#E1BEE7"),
    "Target":      ("#F44336", "#FFCDD2"),
    "Minimap":     ("#009688", "#B2DFDB"),
    "Party":       ("#3F51B5", "#C5CAE9"),
    "Gauge":       ("#CDDC39", "#F0F4C3"),
    "Other":       ("#607D8B", "#CFD8DC"),
}

CHAT_TAB_COLORS = {
    "Legion":  "#4CAF50",
    "Whisper": "#E91E63",
    "Party":   "#2196F3",
    "Force":   "#FF9800",
    "Combat":  "#F44336",
    "System":  "#9E9E9E",
    "Common":  "#795548",
    "Server":  "#673AB7",
    "Object":  "#00BCD4",
}

TAG_KO = {
    "NPCTalk_BossCaption":     "NPC대화_보스자막",
    "NPCTalk_Caption":         "NPC대화_자막",
    "NPCTalk_FocusCameraTalk": "NPC대화_포커스카메라",
    "NPCTalk_OnelineCaption":  "NPC대화_한줄자막",
    "GetItemList":             "아이템획득목록",
    "Minimap":                 "미니맵",
    "QuickSlotItem1":          "퀵슬롯1",
    "QuickSlotItem2":          "퀵슬롯2",
    "AutoSlotSealStone":       "자동슬롯_봉인석",
    "AutoSlotPotion":          "자동슬롯_물약",
    "UserInfo_AbnormalBtn":    "상태이상버튼",
    "UserInfo_HP":             "HP바",
    "UserInfo_MP":             "MP바",
    "UserInfo_AbnormalBuff":   "버프",
    "UserInfo_AbnormalDeBuff": "디버프",
    "UserInfo_Class":          "클래스정보",
    "VoiceChat":               "음성채팅",
    "PartyForce":              "파티/포스",
    "Target":                  "타겟정보",
    "GatherProgress":          "채집진행바",
    "CooltimeSkill":           "스킬쿨타임",
    "Indicator":               "인디케이터",
    "Timer":                   "타이머",
    "GaugeBossWideSkill":      "보스광역스킬게이지",
    "GaugeBossSkill":          "보스스킬게이지",
    "AutoMove":                "자동이동",
    "Gauge":                   "게이지",
    "Chat":                    "채팅창",
    "CounterAttack":           "반격",
    "FieldEventEntrance":      "필드이벤트입장",
    "KeyGuide":                "키가이드",
}

CHAT_TYPE_KO = {
    "Legion":  "군단",
    "Whisper": "귓속말",
    "Party":   "파티",
    "Force":   "포스",
    "Combat":  "전투",
    "System":  "시스템",
    "Common":  "일반",
    "Server":  "서버",
    "Object":  "오브젝트",
}

ANCHOR_KO = {
    "Left": "좌", "Center": "중앙", "Right": "우",
    "Top": "상", "Bottom": "하",
}

FIELD_KO = {
    "Tag":               "태그",
    "HorizontalAnchor":  "수평앵커",
    "VerticalAnchor":    "수직앵커",
    "HorizontalOffset":  "수평오프셋",
    "VerticalOffset":    "수직오프셋",
    "Size":              "크기",
    "Hidden":            "숨김",
    "Reverse":           "반전",
    "Opened":            "열림",
    "Type":              "타입",
}


def ko_tag(tag):
    return TAG_KO.get(tag, tag)

def ko_chat(chat_type):
    return CHAT_TYPE_KO.get(chat_type, chat_type)

def ko_anchor(anchor):
    return ANCHOR_KO.get(anchor, anchor)

def ko_field(field):
    return FIELD_KO.get(field, field)

def get_category(tag):
    for prefix in ["Chat", "QuickSlot", "AutoSlot", "UserInfo", "NPCTalk",
                    "Target", "Minimap", "Party", "Gauge"]:
        if tag.startswith(prefix):
            return prefix
    return "Other"

def get_color(tag):
    cat = get_category(tag)
    return CATEGORY_COLORS.get(cat, CATEGORY_COLORS["Other"])


# ═══════════════════════════════════════════════════════════════════════
#  Startup Dialog (file selection + decode progress)
# ═══════════════════════════════════════════════════════════════════════

class StartupDialog:
    """First window: select .dat file, decode with progress bar, then launch preview."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AION2 HUD 에디터")
        self.root.geometry("550x300")
        self.root.resizable(False, False)

        self.result = None  # will hold (global_settings, characters, encode_ctx, dat_path)

        # Center on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 550) // 2
        y = (sh - 300) // 2
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()

    def _get_default_dat_path(self):
        user = os.getlogin()
        return os.path.join(
            'C:\\Users', user,
            'AppData', 'Local', 'AION2', 'Saved',
            'PersistentDownloadDir', 'UserSetting', 'DeviceSetting.dat'
        )

    def _build_ui(self):
        # Title
        title_frame = ttk.Frame(self.root, padding=20)
        title_frame.pack(fill=tk.X)

        ttk.Label(title_frame, text="AION2 HUD 에디터",
                  font=('맑은 고딕', 16, 'bold')).pack()
        ttk.Label(title_frame, text="DeviceSetting.dat 파일을 선택하세요",
                  font=('맑은 고딕', 10)).pack(pady=(5, 0))

        # File selection
        file_frame = ttk.LabelFrame(self.root, text="파일 경로", padding=10)
        file_frame.pack(fill=tk.X, padx=20, pady=5)

        default_path = self._get_default_dat_path()
        self.path_var = tk.StringVar(value=default_path)
        self.path_entry = ttk.Entry(file_frame, textvariable=self.path_var, width=55)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.browse_btn = ttk.Button(file_frame, text="찾아보기...", command=self._browse)
        self.browse_btn.pack(side=tk.RIGHT)

        # Buttons
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X, padx=20)

        self.open_btn = ttk.Button(btn_frame, text="열기 (디코딩 시작)",
                                   command=self._start_decode)
        self.open_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(btn_frame, text="종료",
                   command=self._quit).pack(side=tk.RIGHT)

        # Progress
        progress_frame = ttk.LabelFrame(self.root, text="진행 상황", padding=10)
        progress_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                             maximum=100, length=480)
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = ttk.Label(progress_frame, text="대기 중...",
                                         font=('맑은 고딕', 9))
        self.progress_label.pack(pady=(5, 0))

    def _browse(self):
        path = filedialog.askopenfilename(
            title="DeviceSetting.dat 선택",
            filetypes=[("DAT 파일", "*.dat"), ("모든 파일", "*.*")],
            initialdir=os.path.dirname(self.path_var.get())
        )
        if path:
            self.path_var.set(path)

    def _start_decode(self):
        dat_path = self.path_var.get().strip()
        if not dat_path or not os.path.isfile(dat_path):
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{dat_path}")
            return

        # Disable buttons during decode
        self.open_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        self.path_entry.config(state=tk.DISABLED)

        # Run decode in thread
        self._decode_thread = threading.Thread(target=self._decode_worker,
                                                args=(dat_path,), daemon=True)
        self._decode_thread.start()
        self._poll_decode()

    def _decode_worker(self, dat_path):
        self._decode_error = None
        self._decode_result = None
        try:
            def progress_cb(pct, msg):
                self._pending_progress = (pct, msg)

            self._pending_progress = (0, "시작...")
            gs, chars, ctx = decode_dat(dat_path, progress_cb)
            self._decode_result = (gs, chars, ctx, dat_path)
        except Exception as e:
            self._decode_error = str(e)
            self._pending_progress = (0, f"오류: {e}")

    def _poll_decode(self):
        if hasattr(self, '_pending_progress'):
            pct, msg = self._pending_progress
            self.progress_var.set(pct)
            self.progress_label.config(text=msg)

        if self._decode_thread.is_alive():
            self.root.after(50, self._poll_decode)
        else:
            if self._decode_error:
                messagebox.showerror("디코딩 오류", self._decode_error)
                self.open_btn.config(state=tk.NORMAL)
                self.browse_btn.config(state=tk.NORMAL)
                self.path_entry.config(state=tk.NORMAL)
                self.progress_label.config(text="대기 중...")
                self.progress_var.set(0)
            elif self._decode_result:
                self.result = self._decode_result
                self.root.after(300, self.root.destroy)  # brief pause to show 100%

    def _quit(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.result


# ═══════════════════════════════════════════════════════════════════════
#  Copy Dialog
# ═══════════════════════════════════════════════════════════════════════

class CopyDialog(tk.Toplevel):
    """Dialog for copying HUD layout between characters."""

    def __init__(self, parent, characters, current_idx, char_name_fn):
        super().__init__(parent)
        self.title("레이아웃 복사")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.characters = characters
        self.char_name_fn = char_name_fn
        self.result = None

        names = [char_name_fn(c) for c in characters]
        pad = {'padx': 10, 'pady': 5}

        # Source
        src_frame = ttk.LabelFrame(self, text="소스 (복사 원본)", padding=10)
        src_frame.pack(fill=tk.X, **pad)

        self.src_var = tk.StringVar()
        self.src_combo = ttk.Combobox(src_frame, textvariable=self.src_var,
                                       values=names, state='readonly', width=55)
        self.src_combo.pack(fill=tk.X)
        self.src_combo.current(current_idx)
        self.src_combo.bind('<<ComboboxSelected>>', self._update_preview)

        # Target
        tgt_frame = ttk.LabelFrame(self, text="대상 (복사할 캐릭터)", padding=10)
        tgt_frame.pack(fill=tk.X, **pad)

        self.tgt_list_frame = ttk.Frame(tgt_frame)
        self.tgt_list_frame.pack(fill=tk.X)

        self.tgt_vars = []
        for i, name in enumerate(names):
            var = tk.BooleanVar(value=False)
            self.tgt_vars.append(var)
            cb = ttk.Checkbutton(self.tgt_list_frame, text=name, variable=var,
                                  command=self._update_preview)
            cb.pack(anchor=tk.W)

        tgt_btn_frame = ttk.Frame(tgt_frame)
        tgt_btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(tgt_btn_frame, text="전체선택",
                    command=self._select_all_targets).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(tgt_btn_frame, text="선택해제",
                    command=self._select_no_targets).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(tgt_btn_frame, text="반전",
                    command=self._invert_targets).pack(side=tk.LEFT)

        # Options
        opt_frame = ttk.LabelFrame(self, text="복사 옵션", padding=10)
        opt_frame.pack(fill=tk.X, **pad)

        self.copy_chat_var = tk.BooleanVar(value=True)
        self.copy_hud_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(opt_frame, text="채팅탭 (채팅창 위치)",
                          variable=self.copy_chat_var,
                          command=self._update_preview).pack(anchor=tk.W)
        ttk.Checkbutton(opt_frame, text="HUD요소 (HUD 위치)",
                          variable=self.copy_hud_var,
                          command=self._update_preview).pack(anchor=tk.W)

        # Preview
        preview_frame = ttk.LabelFrame(self, text="미리보기", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.preview_text = tk.Text(preview_frame, height=6, width=60,
                                     font=('Consolas', 9), bg='#1e1e2e',
                                     fg='#c0c0c0', state=tk.DISABLED)
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, **pad)

        self.ok_btn = ttk.Button(btn_frame, text="복사", command=self._on_ok)
        self.ok_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="취소", command=self.destroy).pack(side=tk.RIGHT)

        self._update_preview()

        # Center on parent
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

    def _select_all_targets(self):
        for v in self.tgt_vars:
            v.set(True)
        self._update_preview()

    def _select_no_targets(self):
        for v in self.tgt_vars:
            v.set(False)
        self._update_preview()

    def _invert_targets(self):
        for v in self.tgt_vars:
            v.set(not v.get())
        self._update_preview()

    def _update_preview(self, event=None):
        src_idx = self.src_combo.current()
        tgt_indices = [i for i, v in enumerate(self.tgt_vars) if v.get()]
        copy_chat = self.copy_chat_var.get()
        copy_hud = self.copy_hud_var.get()

        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete('1.0', tk.END)

        if src_idx < 0:
            self.preview_text.insert(tk.END, "소스 캐릭터를 선택하세요.")
            self.preview_text.config(state=tk.DISABLED)
            return

        src = self.characters[src_idx]
        src_name = src.get('CharacterID_Hex', '?')
        chat_count = len(src.get('ChatTabs', []))
        hud_count = len(src.get('HudElements', []))

        items = []
        if copy_chat:
            items.append(f"채팅탭 {chat_count}개")
        if copy_hud:
            items.append(f"HUD요소 {hud_count}개")
        what = ' + '.join(items) if items else '(선택 없음)'

        real_targets = [i for i in tgt_indices if i != src_idx]
        self_included = src_idx in tgt_indices

        self.preview_text.insert(tk.END, f"소스:   {src_name}\n")
        self.preview_text.insert(tk.END, f"복사:   {what}\n")
        self.preview_text.insert(tk.END, f"대상:   {len(real_targets)}개 캐릭터\n\n")

        if self_included:
            self.preview_text.insert(tk.END, "참고: 소스 = 대상은 건너뜁니다.\n")

        for i in real_targets:
            tgt = self.characters[i]
            tgt_name = tgt.get('CharacterID_Hex', '?')
            old_chat = len(tgt.get('ChatTabs', []))
            old_hud = len(tgt.get('HudElements', []))
            changes = []
            if copy_chat:
                changes.append(f"채팅: {old_chat} -> {chat_count}")
            if copy_hud:
                changes.append(f"HUD: {old_hud} -> {hud_count}")
            self.preview_text.insert(tk.END, f"  {tgt_name}: {', '.join(changes)}\n")

        if not real_targets:
            self.preview_text.insert(tk.END, "(대상 미선택)")

        self.ok_btn.config(state=tk.NORMAL if (real_targets and (copy_chat or copy_hud)) else tk.DISABLED)
        self.preview_text.config(state=tk.DISABLED)

    def _on_ok(self):
        src_idx = self.src_combo.current()
        tgt_indices = [i for i, v in enumerate(self.tgt_vars) if v.get() and i != src_idx]
        if not tgt_indices:
            return
        self.result = {
            'src_idx': src_idx,
            'tgt_indices': tgt_indices,
            'copy_chat': self.copy_chat_var.get(),
            'copy_hud': self.copy_hud_var.get(),
        }
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════
#  Main HUD Preview App
# ═══════════════════════════════════════════════════════════════════════

class HudPreviewApp:
    def __init__(self, root, global_settings, characters, encode_ctx, dat_path):
        self.root = root
        self.root.title("AION2 HUD 에디터")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)

        self.global_settings = global_settings
        self.characters = characters
        self.encode_ctx = encode_ctx
        self.dat_path = dat_path
        self.current_char = None
        self.tooltip_widget = None
        self.hover_item = None
        self.selected_item = None

        # Resolution from settings
        res = global_settings.get('Resolution', {})
        fs = res.get('Fullscreen', '2560x1440')
        if 'x' in str(fs):
            parts = str(fs).split('x')
            self.screen_w = int(parts[0])
            self.screen_h = int(parts[1])
        else:
            self.screen_w = 2560
            self.screen_h = 1440

        self.zoom = 1.0

        self._build_ui()

        if self.characters:
            self.char_combo.current(0)
            self._on_char_changed(None)

    def _char_display_name(self, char):
        cid = char.get('CharacterID', 0)
        hex_id = char.get('CharacterID_Hex', f'0x{cid:08X}')
        has_hud = bool(char.get('HudElements'))
        has_chat = bool(char.get('ChatTabs'))
        elements = []
        if has_chat:
            elements.append(f"채팅 {len(char['ChatTabs'])}")
        if has_hud:
            elements.append(f"HUD {len(char['HudElements'])}")
        detail = ', '.join(elements) if elements else '기본값'
        return f"캐릭터 {hex_id}  ({detail})"

    # ── UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Menu bar ─────────────────────────────────────────────────
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="다른 .dat 파일 열기...", command=self._open_other_dat)
        file_menu.add_separator()
        file_menu.add_command(label="HUD JSON 내보내기 (전체)...", command=self._export_json_all)
        file_menu.add_command(label="HUD JSON 내보내기 (현재 캐릭터)...", command=self._export_json_current)
        file_menu.add_separator()
        file_menu.add_command(label="HUD JSON 불러오기 (전체)...", command=self._import_json_all)
        file_menu.add_command(label="HUD JSON 불러오기 (현재 캐릭터)...", command=self._import_json_current)
        file_menu.add_separator()
        file_menu.add_command(label="DAT로 저장 (백업 + 덮어쓰기)", command=self._save_to_dat)
        file_menu.add_command(label="DAT로 다른 이름으로 저장...", command=self._save_dat_as)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.root.quit)

        # ── Top toolbar ─────────────────────────────────────────────
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="캐릭터:").pack(side=tk.LEFT, padx=(0, 5))
        self.char_var = tk.StringVar()
        names = [self._char_display_name(c) for c in self.characters]
        self.char_combo = ttk.Combobox(toolbar, textvariable=self.char_var,
                                        values=names, state='readonly', width=50)
        self.char_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.char_combo.bind('<<ComboboxSelected>>', self._on_char_changed)

        ttk.Label(toolbar, text="해상도:").pack(side=tk.LEFT, padx=(0, 5))
        self.res_var = tk.StringVar(value=f"{self.screen_w}x{self.screen_h}")
        res_combo = ttk.Combobox(toolbar, textvariable=self.res_var,
                                  values=["2560x1440", "1920x1080", "3840x2160", "1280x720"],
                                  state='readonly', width=12)
        res_combo.pack(side=tk.LEFT, padx=(0, 15))
        res_combo.bind('<<ComboboxSelected>>', self._on_res_changed)

        # Toggles
        self.show_hidden_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="숨김표시", variable=self.show_hidden_var,
                         command=self._redraw).pack(side=tk.LEFT, padx=5)

        self.show_chat_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="채팅탭", variable=self.show_chat_var,
                         command=self._redraw).pack(side=tk.LEFT, padx=5)

        self.show_hud_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="HUD요소", variable=self.show_hud_var,
                         command=self._redraw).pack(side=tk.LEFT, padx=5)

        # Zoom
        ttk.Label(toolbar, text="줌:").pack(side=tk.LEFT, padx=(15, 5))
        self.zoom_var = tk.DoubleVar(value=100.0)
        self.zoom_scale = ttk.Scale(toolbar, from_=30, to=150, orient=tk.HORIZONTAL,
                                     variable=self.zoom_var, length=120,
                                     command=self._on_zoom_changed)
        self.zoom_scale.pack(side=tk.LEFT, padx=(0, 5))
        self.zoom_label = ttk.Label(toolbar, text="100%", width=5)
        self.zoom_label.pack(side=tk.LEFT)
        ttk.Button(toolbar, text="맞춤", command=self._fit_zoom, width=4).pack(side=tk.LEFT, padx=5)

        # ── Second toolbar row ──────────────────────────────────────
        toolbar2 = ttk.Frame(self.root, padding=(5, 0, 5, 5))
        toolbar2.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar2, text="레이아웃 복사",
                    command=self._show_copy_dialog).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(toolbar2, text="HUD JSON 내보내기",
                    command=self._export_json_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar2, text="HUD JSON 불러오기",
                    command=self._import_json_all).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        save_btn = ttk.Button(toolbar2, text="DAT 저장 (백업+저장)",
                               command=self._save_to_dat)
        save_btn.pack(side=tk.LEFT, padx=5)

        # Show current dat path
        ttk.Label(toolbar2, text="파일:",
                  font=('맑은 고딕', 8)).pack(side=tk.LEFT, padx=(15, 2))
        self.dat_path_label = ttk.Label(toolbar2, text=self.dat_path,
                                         font=('Consolas', 8), foreground='gray')
        self.dat_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── Main area: canvas + info panel ──────────────────────────
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        canvas_frame = ttk.Frame(main_pane)
        main_pane.add(canvas_frame, weight=3)

        self.canvas = tk.Canvas(canvas_frame, bg='#1a1a2e', highlightthickness=0)
        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind('<Motion>', self._on_mouse_move)
        self.canvas.bind('<Leave>', self._on_mouse_leave)
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<MouseWheel>', self._on_scroll_zoom)

        # Info panel
        info_frame = ttk.LabelFrame(main_pane, text="요소 상세정보", padding=10)
        main_pane.add(info_frame, weight=1)

        self.info_text = tk.Text(info_frame, wrap=tk.WORD, font=('Consolas', 10),
                                  bg='#16213e', fg='#e0e0e0', insertbackground='#e0e0e0',
                                  state=tk.DISABLED, width=35)
        info_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scroll.set)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.info_text.tag_configure('title', font=('Consolas', 12, 'bold'), foreground='#64ffda')
        self.info_text.tag_configure('key', foreground='#82b1ff')
        self.info_text.tag_configure('val', foreground='#ffffff')
        self.info_text.tag_configure('section', font=('Consolas', 10, 'bold'),
                                      foreground='#ff9800', spacing1=10)
        self.info_text.tag_configure('hidden', foreground='#ff5252')
        self.info_text.tag_configure('divider', foreground='#455a64')

        # ── Status bar ──────────────────────────────────────────────
        self.status_var = tk.StringVar(value="준비")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                                relief=tk.SUNKEN, padding=(5, 2))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Initial fit
        self.root.update_idletasks()
        self._fit_zoom()

    # ── Event handlers ───────────────────────────────────────────────

    def _on_char_changed(self, event):
        idx = self.char_combo.current()
        if 0 <= idx < len(self.characters):
            self.current_char = self.characters[idx]
            self.selected_item = None
            self._redraw()
            self._update_info_all()

    def _on_res_changed(self, event):
        res = self.res_var.get()
        if 'x' in res:
            w, h = res.split('x')
            self.screen_w = int(w)
            self.screen_h = int(h)
            self._fit_zoom()
            self._redraw()

    def _on_zoom_changed(self, val):
        self.zoom = float(val) / 100.0
        self.zoom_label.config(text=f"{int(float(val))}%")
        self._redraw()

    def _on_scroll_zoom(self, event):
        if event.delta > 0:
            new_zoom = min(150, self.zoom_var.get() + 5)
        else:
            new_zoom = max(30, self.zoom_var.get() - 5)
        self.zoom_var.set(new_zoom)
        self._on_zoom_changed(new_zoom)

    def _fit_zoom(self):
        self.root.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            cw, ch = 900, 700
        zw = (cw - 20) / self.screen_w * 100
        zh = (ch - 20) / self.screen_h * 100
        z = min(zw, zh)
        z = max(30, min(150, z))
        self.zoom_var.set(z)
        self.zoom = z / 100.0
        self.zoom_label.config(text=f"{int(z)}%")
        self._redraw()

    def _on_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        items = self.canvas.find_overlapping(cx - 1, cy - 1, cx + 1, cy + 1)
        for item in reversed(items):
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith('elem_') or tag.startswith('chat_'):
                    self.selected_item = tag
                    self._redraw()
                    self._update_info_selected(tag)
                    return
        self.selected_item = None
        self._redraw()
        self._update_info_all()

    def _on_mouse_move(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        items = self.canvas.find_overlapping(cx - 1, cy - 1, cx + 1, cy + 1)
        found_tag = None
        for item in reversed(items):
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith('elem_') or tag.startswith('chat_'):
                    found_tag = tag
                    break
            if found_tag:
                break

        if found_tag != self.hover_item:
            self.hover_item = found_tag
            self._hide_tooltip()
            if found_tag:
                if found_tag.startswith('elem_'):
                    name = found_tag[5:]
                elif found_tag.startswith('chat_'):
                    parts = found_tag[5:].rsplit('_', 1)
                    name = f"Chat: {parts[0]}"
                else:
                    name = found_tag
                self._show_tooltip(event.x_root, event.y_root, name)

    def _on_mouse_leave(self, event):
        self._hide_tooltip()
        self.hover_item = None

    def _show_tooltip(self, x, y, text):
        self._hide_tooltip()
        tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x+15}+{y+10}")
        tw.attributes('-topmost', True)
        label = tk.Label(tw, text=text, font=('Consolas', 9),
                          bg='#263238', fg='#e0e0e0', padx=8, pady=4,
                          relief=tk.SOLID, borderwidth=1)
        label.pack()
        self.tooltip_widget = tw

    def _hide_tooltip(self):
        if self.tooltip_widget:
            self.tooltip_widget.destroy()
            self.tooltip_widget = None

    # ── Position calculation ─────────────────────────────────────────

    def _anchor_origin(self, ha, va):
        if ha == "Left":
            x = 0
        elif ha == "Center":
            x = self.screen_w / 2
        else:
            x = self.screen_w

        if va == "Top":
            y = 0
        elif va == "Center":
            y = self.screen_h / 2
        else:
            y = self.screen_h
        return x, y

    def _element_rect(self, elem, is_chat=False):
        ha = elem.get('HorizontalAnchor', 'Center')
        va = elem.get('VerticalAnchor', 'Center')
        ho = elem.get('HorizontalOffset', 0)
        vo = elem.get('VerticalOffset', 0)

        ax, ay = self._anchor_origin(ha, va)
        cx = ax + ho
        cy = ay + vo

        if is_chat:
            size_level = elem.get('Size', 1)
            w, h = CHAT_BASE_SIZE
            if size_level == 2:
                w, h = int(w * 1.3), int(h * 1.3)
        else:
            tag = elem.get('Tag', '')
            size_arr = elem.get('Size', None)
            if isinstance(size_arr, list) and len(size_arr) >= 2:
                w = size_arr[0] if size_arr[0] > 0 else DEFAULT_HUD_SIZES.get(tag, (120, 40))[0]
                h = size_arr[1] if size_arr[1] > 0 else DEFAULT_HUD_SIZES.get(tag, (120, 40))[1]
            else:
                w, h = DEFAULT_HUD_SIZES.get(tag, (120, 40))

        if ha == "Left":
            x = cx
        elif ha == "Right":
            x = cx - w
        else:
            x = cx - w / 2

        if va == "Top":
            y = cy
        elif va == "Bottom":
            y = cy - h
        else:
            y = cy - h / 2

        return x, y, w, h

    # ── Drawing ──────────────────────────────────────────────────────

    def _redraw(self):
        self.canvas.delete('all')
        if not self.current_char:
            return

        z = self.zoom
        sw = self.screen_w * z
        sh = self.screen_h * z
        self.canvas.configure(scrollregion=(0, 0, sw + 20, sh + 20))

        ox, oy = 10, 10

        # Screen bg
        self.canvas.create_rectangle(ox, oy, ox + sw, oy + sh,
                                      fill='#0f3460', outline='#16213e', width=2)
        # Grid
        grid_step = 200
        for gx in range(0, self.screen_w + 1, grid_step):
            self.canvas.create_line(ox + gx * z, oy, ox + gx * z, oy + sh,
                                     fill='#1a1a3e', dash=(2, 4))
        for gy in range(0, self.screen_h + 1, grid_step):
            self.canvas.create_line(ox, oy + gy * z, ox + sw, oy + gy * z,
                                     fill='#1a1a3e', dash=(2, 4))

        # Crosshair
        cx_s = self.screen_w / 2
        cy_s = self.screen_h / 2
        self.canvas.create_line(ox + cx_s * z - 20, oy + cy_s * z,
                                 ox + cx_s * z + 20, oy + cy_s * z,
                                 fill='#455a64', width=1)
        self.canvas.create_line(ox + cx_s * z, oy + cy_s * z - 20,
                                 ox + cx_s * z, oy + cy_s * z + 20,
                                 fill='#455a64', width=1)

        # Resolution label
        self.canvas.create_text(ox + sw / 2, oy - 2, text=f"{self.screen_w} x {self.screen_h}",
                                 fill='#455a64', anchor=tk.S, font=('Consolas', 9))

        # Anchor points
        anchor_points = [
            ("TL", 0, 0), ("TC", cx_s, 0), ("TR", self.screen_w, 0),
            ("CL", 0, cy_s), ("CC", cx_s, cy_s), ("CR", self.screen_w, cy_s),
            ("BL", 0, self.screen_h), ("BC", cx_s, self.screen_h), ("BR", self.screen_w, self.screen_h),
        ]
        for label, apx, apy in anchor_points:
            self.canvas.create_oval(ox + apx * z - 3, oy + apy * z - 3,
                                     ox + apx * z + 3, oy + apy * z + 3,
                                     fill='#455a64', outline='')

        # Chat tabs
        if self.show_chat_var.get():
            chat_tabs = self.current_char.get('ChatTabs', [])
            for i, ct in enumerate(chat_tabs):
                opened = ct.get('Opened', True)
                if not opened and not self.show_hidden_var.get():
                    continue

                x, y, w, h = self._element_rect(ct, is_chat=True)
                tag_id = f"chat_{ct.get('Type', 'unknown')}_{i}"
                color = CHAT_TAB_COLORS.get(ct.get('Type', ''), '#607D8B')

                is_selected = self.selected_item == tag_id
                outline_width = 3 if is_selected else 1.5
                fill_color = self._darken(color, 0.3)
                outline_color = '#ffffff' if is_selected else color

                if not opened:
                    fill_color = self._darken(color, 0.15)
                    outline_color = self._darken(color, 0.5)

                self.canvas.create_rectangle(
                    ox + x * z, oy + y * z,
                    ox + (x + w) * z, oy + (y + h) * z,
                    fill=fill_color, outline=outline_color, width=outline_width,
                    tags=('chat', tag_id),
                    dash=(4, 2) if not opened else ()
                )

                label = ct.get('Type', '?')
                if not opened:
                    label += ' (closed)'
                self.canvas.create_text(
                    ox + (x + 5) * z, oy + (y + 5) * z,
                    text=label, fill=color, anchor=tk.NW,
                    font=('Consolas', max(7, int(9 * z)), 'bold'),
                    tags=('chat', tag_id)
                )

        # HUD elements
        if self.show_hud_var.get():
            hud_elems = self.current_char.get('HudElements', [])
            for i, elem in enumerate(hud_elems):
                hidden = elem.get('Hidden', False)
                if hidden and not self.show_hidden_var.get():
                    continue

                tag_name = elem.get('Tag', f'Element_{i}')
                tag_id = f"elem_{tag_name}"
                border_color, fill_color = get_color(tag_name)
                x, y, w, h = self._element_rect(elem)

                is_selected = self.selected_item == tag_id

                if hidden:
                    fill_color = '#2a2a2a'
                    border_color = '#555555'
                    outline_width = 2 if is_selected else 1
                else:
                    fill_color = self._darken(fill_color, 0.4)
                    outline_width = 3 if is_selected else 1.5

                if is_selected:
                    border_color = '#ffffff'

                self.canvas.create_rectangle(
                    ox + x * z, oy + y * z,
                    ox + (x + w) * z, oy + (y + h) * z,
                    fill=fill_color, outline=border_color, width=outline_width,
                    tags=('hud', tag_id),
                    dash=(3, 3) if hidden else ()
                )

                # Label
                font_size = max(7, int(9 * z))
                display_name = tag_name
                est_width = sum(1.5 if ord(c) > 127 else 0.7 for c in display_name) * font_size
                if est_width > w * z:
                    max_chars = max(2, int(w * z / (font_size * 1.0)))
                    short_name = display_name[:max_chars-1] + '..'
                else:
                    short_name = display_name

                self.canvas.create_text(
                    ox + (x + w / 2) * z, oy + (y + h / 2) * z,
                    text=short_name, fill=border_color, anchor=tk.CENTER,
                    font=('Consolas', font_size),
                    tags=('hud', tag_id)
                )

                if hidden:
                    self.canvas.create_text(
                        ox + (x + w - 5) * z, oy + (y + 3) * z,
                        text='X', fill='#ff5252', anchor=tk.NE,
                        font=('Consolas', max(6, int(7 * z)), 'bold'),
                        tags=('hud', tag_id)
                    )

        # Status
        hud_count = len(self.current_char.get('HudElements', []))
        chat_count = len(self.current_char.get('ChatTabs', []))
        hidden_count = sum(1 for e in self.current_char.get('HudElements', [])
                           if e.get('Hidden', False))
        self.status_var.set(
            f"HUD: {hud_count}개 ({hidden_count}개 숨김)  |  "
            f"채팅: {chat_count}개 탭  |  "
            f"화면: {self.screen_w}x{self.screen_h}  |  줌: {int(self.zoom * 100)}%"
        )

    def _darken(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return '#333333'
        r = int(int(hex_color[0:2], 16) * factor)
        g = int(int(hex_color[2:4], 16) * factor)
        b = int(int(hex_color[4:6], 16) * factor)
        return f'#{r:02x}{g:02x}{b:02x}'

    # ── Copy dialog ─────────────────────────────────────────────────

    def _show_copy_dialog(self):
        if len(self.characters) < 2:
            messagebox.showinfo("레이아웃 복사", "복사하려면 최소 2개 캐릭터가 필요합니다.")
            return
        current_idx = self.char_combo.current()
        dlg = CopyDialog(self.root, self.characters, current_idx,
                          self._char_display_name)
        self.root.wait_window(dlg)
        if dlg.result:
            self._execute_copy(dlg.result)

    def _execute_copy(self, params):
        src = self.characters[params['src_idx']]
        copied = 0
        for tgt_idx in params['tgt_indices']:
            tgt = self.characters[tgt_idx]
            if params['copy_chat']:
                tgt['ChatTabs'] = copy.deepcopy(src.get('ChatTabs', []))
            if params['copy_hud']:
                tgt['HudElements'] = copy.deepcopy(src.get('HudElements', []))
            copied += 1

        names = [self._char_display_name(c) for c in self.characters]
        current_idx = self.char_combo.current()
        self.char_combo['values'] = names
        self.char_combo.current(current_idx)
        self._on_char_changed(None)

        src_name = src.get('CharacterID_Hex', '?')
        what = []
        if params['copy_chat']:
            what.append('채팅탭')
        if params['copy_hud']:
            what.append('HUD요소')
        messagebox.showinfo(
            "복사 완료",
            f"{src_name}에서 {' + '.join(what)}을(를)\n"
            f"{copied}개 캐릭터에 복사했습니다."
        )

    # ── JSON Export / Import ─────────────────────────────────────────

    def _extract_hud_data(self, char):
        """Extract only HUD-related data from a character dict."""
        data = {}
        if char.get('ChatTabs'):
            data['ChatTabs'] = char['ChatTabs']
        if char.get('HudElements'):
            data['HudElements'] = char['HudElements']
        if char.get('HudGroups'):
            data['HudGroups'] = char['HudGroups']
        return data

    def _export_json_all(self):
        """Export all characters' HUD data to a single JSON file."""
        path = filedialog.asksaveasfilename(
            title="JSON 내보내기 (전체 캐릭터 HUD)",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile="aion2_hud_all.json"
        )
        if not path:
            return
        export = []
        for char in self.characters:
            entry = {
                "CharacterID": char.get("CharacterID"),
                "CharacterID_Hex": char.get("CharacterID_Hex"),
            }
            entry.update(self._extract_hud_data(char))
            export.append(entry)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(export, f, indent='\t', ensure_ascii=False)
        messagebox.showinfo("내보내기 완료",
                            f"{len(export)}개 캐릭터 HUD 데이터를 저장했습니다.\n{path}")

    def _export_json_current(self):
        """Export current character's HUD data to a JSON file."""
        if not self.current_char:
            messagebox.showinfo("내보내기", "캐릭터를 선택하세요.")
            return
        hex_id = self.current_char.get('CharacterID_Hex', 'unknown')
        hud_data = self._extract_hud_data(self.current_char)
        if not hud_data:
            messagebox.showinfo("내보내기", "이 캐릭터에 HUD 데이터가 없습니다.")
            return
        path = filedialog.asksaveasfilename(
            title="JSON 내보내기 (현재 캐릭터 HUD)",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile=f"hud_{hex_id}.json"
        )
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(hud_data, f, indent='\t', ensure_ascii=False)
        messagebox.showinfo("내보내기 완료",
                            f"캐릭터 {hex_id} HUD 데이터를 저장했습니다.\n{path}")

    def _import_json_all(self):
        """Import all characters' HUD data from a JSON file."""
        path = filedialog.askopenfilename(
            title="JSON 불러오기 (전체 캐릭터 HUD)",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("불러오기 오류", f"JSON 파일 읽기 실패:\n{e}")
            return

        # Accept: array of {CharacterID, ChatTabs, ...} or {Characters: [...]}
        if isinstance(data, list):
            imported_chars = data
        elif isinstance(data, dict) and 'Characters' in data:
            imported_chars = data['Characters']
        else:
            messagebox.showerror("불러오기 오류",
                                 "올바른 형식이 아닙니다.\n"
                                 "캐릭터 배열 JSON이 필요합니다.")
            return

        # Match by CharacterID
        imported_map = {}
        for ic in imported_chars:
            cid = ic.get('CharacterID', 0)
            if cid:
                imported_map[cid] = ic

        updated = 0
        for char in self.characters:
            cid = char.get('CharacterID', 0)
            if cid in imported_map:
                ic = imported_map[cid]
                if 'ChatTabs' in ic:
                    char['ChatTabs'] = ic['ChatTabs']
                if 'HudElements' in ic:
                    char['HudElements'] = ic['HudElements']
                if 'HudGroups' in ic:
                    char['HudGroups'] = ic['HudGroups']
                updated += 1

        # Refresh UI
        names = [self._char_display_name(c) for c in self.characters]
        current_idx = self.char_combo.current()
        self.char_combo['values'] = names
        if current_idx >= 0:
            self.char_combo.current(current_idx)
        self._on_char_changed(None)

        messagebox.showinfo("불러오기 완료",
                            f"{updated}개 캐릭터 HUD 데이터를 불러왔습니다.\n"
                            f"(매칭: CharacterID 기준)")

    def _import_json_current(self):
        """Import HUD data from a JSON file into the current character."""
        if not self.current_char:
            messagebox.showinfo("불러오기", "캐릭터를 선택하세요.")
            return

        path = filedialog.askopenfilename(
            title="JSON 불러오기 (현재 캐릭터 HUD)",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("불러오기 오류", f"JSON 파일 읽기 실패:\n{e}")
            return

        if 'ChatTabs' in data:
            self.current_char['ChatTabs'] = data['ChatTabs']
        if 'HudElements' in data:
            self.current_char['HudElements'] = data['HudElements']
        if 'HudGroups' in data:
            self.current_char['HudGroups'] = data['HudGroups']

        # Refresh
        names = [self._char_display_name(c) for c in self.characters]
        current_idx = self.char_combo.current()
        self.char_combo['values'] = names
        self.char_combo.current(current_idx)
        self._on_char_changed(None)

        hex_id = self.current_char.get('CharacterID_Hex', '?')
        messagebox.showinfo("불러오기 완료",
                            f"캐릭터 {hex_id}에 HUD 데이터를 불러왔습니다.")

    # ── Save to .dat ─────────────────────────────────────────────────

    def _save_to_dat(self):
        """Save back to .dat with backup."""
        if not self.encode_ctx:
            messagebox.showerror("저장 오류", "인코딩 컨텍스트가 없습니다.")
            return

        dat_path = self.dat_path
        if not os.path.isfile(dat_path):
            messagebox.showerror("저장 오류", f"원본 파일을 찾을 수 없습니다:\n{dat_path}")
            return

        # Backup: DeviceSetting.dat -> DeviceSetting.dat.20260318_153000.bak
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{dat_path}.{timestamp}.bak"

        try:
            import shutil
            shutil.copy2(dat_path, backup_path)
        except Exception as e:
            messagebox.showerror("백업 오류", f"백업 실패:\n{e}")
            return

        # Encode and save
        try:
            # Deep copy characters to avoid mutation from _mc_consumed/_he_consumed
            chars_copy = copy.deepcopy(self.characters)
            # Also deep copy encode_ctx block_meta to avoid mutation
            ctx_copy = copy.deepcopy(self.encode_ctx)

            file_size = encode_dat(chars_copy, ctx_copy, dat_path)

            messagebox.showinfo(
                "저장 완료",
                f"저장 완료!\n\n"
                f"백업: {os.path.basename(backup_path)}\n"
                f"저장: {os.path.basename(dat_path)} ({file_size:,} 바이트)"
            )
            self.status_var.set(f"저장 완료 - {os.path.basename(dat_path)} ({file_size:,} 바이트)")
        except Exception as e:
            messagebox.showerror("인코딩 오류", f"DAT 저장 실패:\n{e}")

    def _save_dat_as(self):
        """Save to a different .dat path."""
        path = filedialog.asksaveasfilename(
            title="DAT 다른 이름으로 저장",
            defaultextension=".dat",
            filetypes=[("DAT 파일", "*.dat"), ("모든 파일", "*.*")],
            initialfile="DeviceSetting_modified.dat"
        )
        if not path:
            return
        try:
            chars_copy = copy.deepcopy(self.characters)
            ctx_copy = copy.deepcopy(self.encode_ctx)
            file_size = encode_dat(chars_copy, ctx_copy, path)
            messagebox.showinfo("저장 완료",
                                f"저장: {path}\n크기: {file_size:,} 바이트")
        except Exception as e:
            messagebox.showerror("인코딩 오류", f"DAT 저장 실패:\n{e}")

    def _open_other_dat(self):
        """Open a different .dat file (re-decode)."""
        path = filedialog.askopenfilename(
            title="다른 DAT 파일 열기",
            filetypes=[("DAT 파일", "*.dat"), ("모든 파일", "*.*")]
        )
        if not path:
            return

        # Show progress in status bar
        self.status_var.set("디코딩 중...")
        self.root.update_idletasks()

        try:
            def progress_cb(pct, msg):
                pass  # silent for re-open

            gs, chars, ctx = decode_dat(path, progress_cb)
            self.global_settings = gs
            self.characters = chars
            self.encode_ctx = ctx
            self.dat_path = path
            self.dat_path_label.config(text=path)

            # Refresh resolution
            res = gs.get('Resolution', {})
            fs = res.get('Fullscreen', '2560x1440')
            if 'x' in str(fs):
                parts = str(fs).split('x')
                self.screen_w = int(parts[0])
                self.screen_h = int(parts[1])
                self.res_var.set(f"{self.screen_w}x{self.screen_h}")

            # Refresh character list
            names = [self._char_display_name(c) for c in self.characters]
            self.char_combo['values'] = names
            if self.characters:
                self.char_combo.current(0)
                self._on_char_changed(None)

            self.status_var.set(f"열기 완료: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("디코딩 오류", f"파일 열기 실패:\n{e}")
            self.status_var.set("준비")

    # ── Info panel ───────────────────────────────────────────────────

    def _update_info_all(self):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete('1.0', tk.END)

        if not self.current_char:
            self.info_text.insert(tk.END, "캐릭터를 선택하세요")
            self.info_text.config(state=tk.DISABLED)
            return

        cid_hex = self.current_char.get('CharacterID_Hex', '?')
        self.info_text.insert(tk.END, f"캐릭터 {cid_hex}\n", 'title')
        self.info_text.insert(tk.END, '-' * 35 + '\n', 'divider')

        chat_tabs = self.current_char.get('ChatTabs', [])
        if chat_tabs:
            self.info_text.insert(tk.END, f"\nChatTabs ({len(chat_tabs)})\n", 'section')
            for ct in chat_tabs:
                opened = ct.get('Opened', True)
                marker = ' *' if opened else ''
                self.info_text.insert(tk.END, f"  {ct.get('Type', '?')}", 'key')
                self.info_text.insert(tk.END, f"{marker}\n", 'val')
                ha = ct.get('HorizontalAnchor', '?')
                va = ct.get('VerticalAnchor', '?')
                self.info_text.insert(tk.END,
                    f"    {ha}/{va} "
                    f"({ct.get('HorizontalOffset',0):.0f}, {ct.get('VerticalOffset',0):.0f})\n",
                    'val')

        hud_elems = self.current_char.get('HudElements', [])
        if hud_elems:
            self.info_text.insert(tk.END, f"\nHudElements ({len(hud_elems)})\n", 'section')
            for elem in hud_elems:
                tag = elem.get('Tag', '?')
                hidden = elem.get('Hidden', False)
                self.info_text.insert(tk.END, f"  {tag}", 'key')
                if hidden:
                    self.info_text.insert(tk.END, ' [Hidden]', 'hidden')
                self.info_text.insert(tk.END, '\n')
                ha = elem.get('HorizontalAnchor', '?')
                va = elem.get('VerticalAnchor', '?')
                self.info_text.insert(tk.END,
                    f"    {ha}/{va} "
                    f"({elem.get('HorizontalOffset',0):.1f}, {elem.get('VerticalOffset',0):.1f})\n",
                    'val')

        self.info_text.config(state=tk.DISABLED)

    def _update_info_selected(self, tag_id):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete('1.0', tk.END)

        if tag_id.startswith('elem_'):
            tag_name = tag_id[5:]
            hud_elems = self.current_char.get('HudElements', [])
            elem = None
            for e in hud_elems:
                if e.get('Tag') == tag_name:
                    elem = e; break
            if elem:
                self.info_text.insert(tk.END, f"{tag_name}\n", 'title')
                self.info_text.insert(tk.END, '-' * 35 + '\n', 'divider')
                self.info_text.insert(tk.END, '\n')
                for k, v in elem.items():
                    self.info_text.insert(tk.END, f"  {k}: ", 'key')
                    if k == 'Hidden' and v:
                        self.info_text.insert(tk.END, f"{v}\n", 'hidden')
                    else:
                        self.info_text.insert(tk.END, f"{v}\n", 'val')

                x, y, w, h = self._element_rect(elem)
                self.info_text.insert(tk.END, '\nComputed Position\n', 'section')
                self.info_text.insert(tk.END, f"  X: ", 'key')
                self.info_text.insert(tk.END, f"{x:.1f}\n", 'val')
                self.info_text.insert(tk.END, f"  Y: ", 'key')
                self.info_text.insert(tk.END, f"{y:.1f}\n", 'val')
                self.info_text.insert(tk.END, f"  W: ", 'key')
                self.info_text.insert(tk.END, f"{w:.0f}\n", 'val')
                self.info_text.insert(tk.END, f"  H: ", 'key')
                self.info_text.insert(tk.END, f"{h:.0f}\n", 'val')

        elif tag_id.startswith('chat_'):
            parts = tag_id[5:].rsplit('_', 1)
            chat_type = parts[0]
            chat_idx = int(parts[1]) if len(parts) > 1 else 0
            chat_tabs = self.current_char.get('ChatTabs', [])
            if chat_idx < len(chat_tabs):
                ct = chat_tabs[chat_idx]
                self.info_text.insert(tk.END, f"ChatTab: {chat_type}\n", 'title')
                self.info_text.insert(tk.END, '-' * 35 + '\n', 'divider')
                self.info_text.insert(tk.END, '\n')
                for k, v in ct.items():
                    self.info_text.insert(tk.END, f"  {k}: ", 'key')
                    self.info_text.insert(tk.END, f"{v}\n", 'val')

                x, y, w, h = self._element_rect(ct, is_chat=True)
                self.info_text.insert(tk.END, '\nComputed Position\n', 'section')
                self.info_text.insert(tk.END, f"  X: ", 'key')
                self.info_text.insert(tk.END, f"{x:.1f}\n", 'val')
                self.info_text.insert(tk.END, f"  Y: ", 'key')
                self.info_text.insert(tk.END, f"{y:.1f}\n", 'val')
                self.info_text.insert(tk.END, f"  W: ", 'key')
                self.info_text.insert(tk.END, f"{w:.0f}\n", 'val')
                self.info_text.insert(tk.END, f"  H: ", 'key')
                self.info_text.insert(tk.END, f"{h:.0f}\n", 'val')

        self.info_text.config(state=tk.DISABLED)


# ═══════════════════════════════════════════════════════════════════════
#  Main entry point
# ═══════════════════════════════════════════════════════════════════════

def main():
    # Phase 1: Startup dialog
    startup = StartupDialog()
    result = startup.run()

    if not result:
        sys.exit(0)

    global_settings, characters, encode_ctx, dat_path = result

    # Phase 2: Preview window
    root = tk.Tk()
    app = HudPreviewApp(root, global_settings, characters, encode_ctx, dat_path)
    root.mainloop()


if __name__ == '__main__':
    main()
