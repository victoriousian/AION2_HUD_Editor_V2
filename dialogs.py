"""
Startup and Copy dialogs for AION2 HUD Editor.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from codec import decode_dat


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
