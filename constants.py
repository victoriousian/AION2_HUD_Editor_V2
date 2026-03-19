"""
Constants, crypto, translation maps, and utility functions for AION2 HUD Editor.
"""

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
    "PolymorphSkill":            (120, 40),
    "QuickSlotStigma":           (270, 50),
    "QuickSlotSkill1":           (270, 50),
    "QuickSlotSkill2":           (270, 50),
    "Ride":                      (50, 50),
    "Fly":                       (50, 50),
    "PresetMode":                (80, 30),
    "PvPMode":                   (80, 30),
    "CurrencyWeeklyLimit":       (150, 30),
    "Currency":                  (150, 50),
    "MenuSubscribe":             (60, 60),
    "MenuBMShop":                (60, 60),
    "MenuDaevanion":             (60, 60),
    "MenuInventory":             (60, 60),
    "MenuSkill":                 (60, 60),
    "MenuJournal":               (60, 60),
    "ContinuousSkill":           (120, 40),
    "BtnParty":                  (40, 40),
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


DEFAULT_HUD_LAYOUT = [
    {"Tag": "NPCTalk_BossCaption", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -418.0, "Hidden": False, "Reverse": False},
    {"Tag": "NPCTalk_Caption", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -304.0, "Hidden": False, "Reverse": False},
    {"Tag": "NPCTalk_FocusCameraTalk", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -304.0, "Hidden": False, "Reverse": False},
    {"Tag": "NPCTalk_OnelineCaption", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -264.0, "Hidden": False, "Reverse": False},
    {"Tag": "GetItemList", "HorizontalAnchor": "Center", "VerticalAnchor": "Top", "HorizontalOffset": -404.0, "VerticalOffset": 593.0, "Hidden": False, "Reverse": False},
    {"Tag": "Minimap", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -33.0, "VerticalOffset": 116.0, "Hidden": False, "Reverse": False},
    {"Tag": "PolymorphSkill", "HorizontalAnchor": "Right", "VerticalAnchor": "Bottom", "HorizontalOffset": -778.7, "VerticalOffset": -13.0, "Hidden": False, "Reverse": False},
    {"Tag": "QuickSlotStigma", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -9.0, "Hidden": False, "Reverse": False},
    {"Tag": "QuickSlotSkill2", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 306.0, "VerticalOffset": -9.0, "Hidden": False, "Reverse": False},
    {"Tag": "QuickSlotSkill1", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": -306.0, "VerticalOffset": -9.0, "Hidden": False, "Reverse": False},
    {"Tag": "QuickSlotItem2", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 206.0, "VerticalOffset": -94.0, "Hidden": False, "Reverse": False},
    {"Tag": "QuickSlotItem1", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": -206.0, "VerticalOffset": -94.0, "Hidden": False, "Reverse": False},
    {"Tag": "AutoSlotSealStone", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 390.0, "VerticalOffset": -93.0, "Hidden": False, "Reverse": False},
    {"Tag": "AutoSlotPotion", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": -390.0, "VerticalOffset": -93.0, "Hidden": False, "Reverse": False},
    {"Tag": "UserInfo_AbnormalBtn", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": -430.0, "VerticalOffset": -157.0, "Hidden": False, "Reverse": False},
    {"Tag": "UserInfo_HP", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": -234.0, "VerticalOffset": -161.0, "Hidden": False, "Reverse": False},
    {"Tag": "UserInfo_MP", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 234.0, "VerticalOffset": -161.0, "Hidden": False, "Reverse": False},
    {"Tag": "UserInfo_AbnormalBuff", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 216.0, "VerticalOffset": -194.0, "Hidden": False, "Reverse": False},
    {"Tag": "UserInfo_AbnormalDeBuff", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": -216.0, "VerticalOffset": -194.0, "Hidden": False, "Reverse": False},
    {"Tag": "UserInfo_Class", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -80.0, "Hidden": False, "Reverse": False},
    {"Tag": "VoiceChat", "HorizontalAnchor": "Left", "VerticalAnchor": "Top", "HorizontalOffset": 321.0, "VerticalOffset": 136.0, "Hidden": False, "Reverse": False},
    {"Tag": "PartyForce", "HorizontalAnchor": "Left", "VerticalAnchor": "Top", "HorizontalOffset": 0.0, "VerticalOffset": 138.0, "Hidden": False, "Reverse": False},
    {"Tag": "Target", "HorizontalAnchor": "Center", "VerticalAnchor": "Top", "HorizontalOffset": 150.0, "VerticalOffset": 1.0, "Hidden": False, "Reverse": False},
    {"Tag": "GatherProgress", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -269.0, "Hidden": False, "Reverse": False},
    {"Tag": "CooltimeSkill", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -261.0, "Hidden": False, "Reverse": False},
    {"Tag": "Ride", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 506.0, "VerticalOffset": 0.0, "Hidden": False, "Reverse": False},
    {"Tag": "Fly", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": -506.0, "VerticalOffset": 0.0, "Hidden": False, "Reverse": False},
    {"Tag": "PresetMode", "HorizontalAnchor": "Left", "VerticalAnchor": "Bottom", "HorizontalOffset": 1056.7, "VerticalOffset": -12.0, "Hidden": False, "Reverse": False},
    {"Tag": "PvPMode", "HorizontalAnchor": "Right", "VerticalAnchor": "Bottom", "HorizontalOffset": -1070.7, "VerticalOffset": -8.0, "Hidden": False, "Reverse": False},
    {"Tag": "BtnParty", "HorizontalAnchor": "Left", "VerticalAnchor": "Top", "HorizontalOffset": 16.0, "VerticalOffset": 138.0, "Hidden": False, "Reverse": False},
    {"Tag": "CurrencyWeeklyLimit", "HorizontalAnchor": "Left", "VerticalAnchor": "Top", "HorizontalOffset": 15.0, "VerticalOffset": 59.0, "Hidden": False, "Reverse": False},
    {"Tag": "Currency", "HorizontalAnchor": "Left", "VerticalAnchor": "Top", "HorizontalOffset": 0.0, "VerticalOffset": 1.0, "Hidden": False, "Reverse": False},
    {"Tag": "MenuSubscribe", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -454.0, "VerticalOffset": 11.0, "Hidden": False, "Reverse": False},
    {"Tag": "MenuBMShop", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -380.0, "VerticalOffset": 11.0, "Hidden": False, "Reverse": False},
    {"Tag": "MenuDaevanion", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -306.0, "VerticalOffset": 11.0, "Hidden": False, "Reverse": False},
    {"Tag": "MenuInventory", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -232.0, "VerticalOffset": 11.0, "Hidden": False, "Reverse": False},
    {"Tag": "MenuSkill", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -158.0, "VerticalOffset": 11.0, "Hidden": False, "Reverse": False},
    {"Tag": "MenuJournal", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -88.0, "VerticalOffset": 11.0, "Hidden": False, "Reverse": False},
    {"Tag": "Indicator", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": 0.0, "VerticalOffset": 436.0, "Hidden": False, "Reverse": False},
    {"Tag": "Timer", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -465.0, "VerticalOffset": 112.0, "Hidden": False, "Reverse": False},
    {"Tag": "GaugeBossWideSkill", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -372.0, "Hidden": False, "Reverse": False},
    {"Tag": "AutoMove", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -394.0, "Hidden": False, "Reverse": False},
    {"Tag": "Gauge", "HorizontalAnchor": "Center", "VerticalAnchor": "Bottom", "HorizontalOffset": 0.0, "VerticalOffset": -340.0, "Hidden": False, "Reverse": False},
    {"Tag": "Chat", "HorizontalAnchor": "Left", "VerticalAnchor": "Bottom", "HorizontalOffset": 76.0, "VerticalOffset": -41.0, "Hidden": False, "Reverse": False},
    {"Tag": "ContinuousSkill", "HorizontalAnchor": "Right", "VerticalAnchor": "Center", "HorizontalOffset": -1030.7, "VerticalOffset": 221.5, "Hidden": False, "Reverse": False},
    {"Tag": "CounterAttack", "HorizontalAnchor": "Right", "VerticalAnchor": "Bottom", "HorizontalOffset": -889.7, "VerticalOffset": -493.0, "Hidden": False, "Reverse": False},
    {"Tag": "FieldEventEntrance", "HorizontalAnchor": "Right", "VerticalAnchor": "Top", "HorizontalOffset": -480.0, "VerticalOffset": 365.0, "Hidden": False, "Reverse": False},
    {"Tag": "KeyGuide", "HorizontalAnchor": "Right", "VerticalAnchor": "Bottom", "HorizontalOffset": -32.0, "VerticalOffset": -34.0, "Hidden": False, "Reverse": False},
]


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
