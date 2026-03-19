"""
Main HUD Preview application window for AION2 HUD Editor.
"""

import os
import json
import copy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from constants import (
    DEFAULT_HUD_SIZES, CHAT_BASE_SIZE, CHAT_TAB_COLORS, get_color,
)
from codec import decode_dat, encode_dat
from dialogs import CopyDialog


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
        file_menu.add_command(label="HUD JSON 내보내기 (캐릭터별)...", command=self._export_json_per_char)
        file_menu.add_command(label="HUD JSON 내보내기 (현재 캐릭터)...", command=self._export_json_current)
        file_menu.add_separator()
        file_menu.add_command(label="HUD JSON 불러오기 (캐릭터별)...", command=self._import_json_per_char)
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
                    command=self._export_json_per_char).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar2, text="HUD JSON 불러오기",
                    command=self._import_json_per_char).pack(side=tk.LEFT, padx=5)

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

    def _export_json_per_char(self):
        """Export each character's HUD data to individual JSON files in a folder."""
        folder = filedialog.askdirectory(title="HUD JSON 내보내기 — 폴더 선택")
        if not folder:
            return
        exported = 0
        for char in self.characters:
            hud_data = self._extract_hud_data(char)
            if not hud_data:
                continue
            hex_id = char.get('CharacterID_Hex', 'unknown')
            filename = f"hud_{hex_id}.json"
            filepath = os.path.join(folder, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(hud_data, f, indent='\t', ensure_ascii=False)
            exported += 1
        messagebox.showinfo("내보내기 완료",
                            f"{exported}개 캐릭터 HUD JSON을 저장했습니다.\n{folder}")

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

    def _import_json_per_char(self):
        """Import per-character HUD JSON files from a folder (hud_0x*.json)."""
        folder = filedialog.askdirectory(title="HUD JSON 불러오기 — 폴더 선택")
        if not folder:
            return

        # Build hex_id -> character mapping
        char_map = {}
        for char in self.characters:
            hex_id = char.get('CharacterID_Hex', '')
            if hex_id:
                char_map[hex_id] = char

        updated = 0
        errors = []
        for filename in sorted(os.listdir(folder)):
            if not filename.startswith('hud_0x') or not filename.endswith('.json'):
                continue
            hex_id = filename[4:-5]  # "hud_0x00004A94.json" -> "0x00004A94"
            if hex_id not in char_map:
                continue
            filepath = os.path.join(folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                errors.append(f"{filename}: {e}")
                continue

            char = char_map[hex_id]
            if 'ChatTabs' in data:
                char['ChatTabs'] = data['ChatTabs']
            if 'HudElements' in data:
                char['HudElements'] = data['HudElements']
            if 'HudGroups' in data:
                char['HudGroups'] = data['HudGroups']
            updated += 1

        # Refresh UI
        names = [self._char_display_name(c) for c in self.characters]
        current_idx = self.char_combo.current()
        self.char_combo['values'] = names
        if current_idx >= 0:
            self.char_combo.current(current_idx)
        self._on_char_changed(None)

        msg = f"{updated}개 캐릭터 HUD 데이터를 불러왔습니다."
        if errors:
            msg += f"\n\n오류 {len(errors)}건:\n" + "\n".join(errors[:5])
        messagebox.showinfo("불러오기 완료", msg)

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
