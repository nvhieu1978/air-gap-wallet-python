import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
try:
    from PIL import Image, ImageTk
    HAS_IMAGETK = True
except ImportError:
    from PIL import Image
    ImageTk = None
    HAS_IMAGETK = False
import shutil
import subprocess
import re

# Local imports
from config import AppConfig
from blockfrost_api import BlockfrostAPI
from wallet_manager import WalletManager
from transaction_builder import TransactionBuilder
import gui_styles as styles

class AirGapWalletApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Cardano Air-Gap Wallet (GUI)")
        self.geometry("1100x700")
        self.configure(bg=styles.BG_MAIN)
        self.minsize(900, 600)
        
        # Load config, api, wallet manager, transaction builder
        self.config = AppConfig()
        self.api = BlockfrostAPI(
            self.config.get("blockfrost_api_key"),
            self.config.get("blockfrost_url")
        )
        self.wallet_mgr = WalletManager(self.config)
        self.tx_builder = TransactionBuilder(self.config)
        
        # Configure styles
        self.style = ttk.Style()
        styles.configure_ttk_styles(self.style)
        
        # Apply standard option database rules for non-ttk widgets (like Text/ScrolledText, Listbox popdown)
        self.option_add("*Text.background", styles.BG_INPUT)
        self.option_add("*Text.foreground", styles.TXT_PRIMARY)
        self.option_add("*Text.insertBackground", styles.TXT_PRIMARY)
        self.option_add("*Text.selectBackground", styles.COLOR_PRIMARY)
        self.option_add("*Text.selectForeground", styles.BG_MAIN)
        self.option_add("*Text.relief", "flat")
        self.option_add("*Text.borderwidth", 1)
        self.option_add("*Text.highlightBackground", styles.BORDER_COLOR)
        self.option_add("*Text.highlightColor", styles.COLOR_PRIMARY)
        
        self.option_add("*TCombobox*Listbox.background", styles.BG_INPUT)
        self.option_add("*TCombobox*Listbox.foreground", styles.TXT_PRIMARY)
        self.option_add("*TCombobox*Listbox.selectBackground", styles.COLOR_PRIMARY)
        self.option_add("*TCombobox*Listbox.selectForeground", styles.BG_MAIN)
        self.option_add("*TCombobox*Listbox.font", styles.FONT_BODY)
        
        self.option_add("*Entry.background", styles.BG_INPUT)
        self.option_add("*Entry.foreground", styles.TXT_PRIMARY)
        self.option_add("*Entry.insertBackground", styles.TXT_PRIMARY)
        self.option_add("*Entry.selectBackground", styles.COLOR_PRIMARY)
        self.option_add("*Entry.selectForeground", styles.BG_MAIN)
        
        # Main Layout
        self.create_layout()
        
        # Load initial wallet if any
        self.update_wallet_list()
        last_wallet = self.config.get("last_wallet_name")
        if last_wallet in self.wallet_mgr.list_wallets():
            self.wallet_combo.set(last_wallet)
            self.on_wallet_select()
            
        # Update settings view
        self.load_settings_into_ui()

    def create_layout(self):
        # 1. Sidebar Frame
        self.sidebar = ttk.Frame(self, style="Sidebar.TFrame")
        self.sidebar.pack(side="left", fill="y")
        
        # Title in Sidebar
        title_label = tk.Label(
            self.sidebar, text="Cardano Cold",
            font=styles.FONT_TITLE, bg=styles.BG_SIDEBAR, fg=styles.COLOR_PRIMARY
        )
        title_label.pack(padx=styles.PAD_MD, pady=(styles.PAD_XL, styles.PAD_XS))
        
        subtitle_label = tk.Label(
            self.sidebar, text="Air-Gap Wallet",
            font=styles.FONT_BODY_BOLD, bg=styles.BG_SIDEBAR, fg=styles.TXT_SECONDARY
        )
        subtitle_label.pack(padx=styles.PAD_MD, pady=(0, styles.PAD_XL))
        
        # Navigation Buttons in Sidebar
        self.nav_buttons = {}
        nav_items = [
            ("Ví của tôi", "wallet"),
            ("Giao dịch Online", "online"),
            ("Ký Ngoại Tuyến", "offline"),
            ("Cài đặt", "settings")
        ]
        
        for label, tag in nav_items:
            btn = tk.Button(
                self.sidebar, text=label, font=styles.FONT_BODY_BOLD,
                bg=styles.BG_SIDEBAR, fg=styles.TXT_SECONDARY,
                activebackground=styles.BG_INPUT, activeforeground=styles.TXT_PRIMARY,
                bd=0, relief="flat", anchor="w", padx=styles.PAD_LG, pady=styles.PAD_MD,
                command=lambda t=tag: self.switch_tab(t)
            )
            btn.pack(fill="x", pady=2)
            # Hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY))
            btn.bind("<Leave>", lambda e, b=btn, t=tag: self.restore_nav_button_bg(b, t))
            self.nav_buttons[tag] = btn
            
        # Divider in sidebar
        lbl_div = tk.Label(self.sidebar, text="", bg=styles.BG_SIDEBAR, height=1)
        lbl_div.pack(fill="x")
        
        # 2. Main Content Frame
        self.content_container = ttk.Frame(self)
        self.content_container.pack(side="right", expand=True, fill="both", padx=styles.PAD_LG, pady=styles.PAD_LG)
        
        # Create different views/pages
        self.views = {}
        self.create_wallet_view()
        self.create_online_view()
        self.create_offline_view()
        self.create_settings_view()
        
        # Switch to first view
        self.switch_tab("wallet")

    def restore_nav_button_bg(self, btn, tag):
        if self.current_tab == tag:
            btn.config(bg=styles.BG_INPUT, fg=styles.COLOR_PRIMARY)
        else:
            btn.config(bg=styles.BG_SIDEBAR, fg=styles.TXT_SECONDARY)

    def switch_tab(self, tag):
        self.current_tab = tag
        
        # Highlight active nav button
        for t, btn in self.nav_buttons.items():
            if t == tag:
                btn.config(bg=styles.BG_INPUT, fg=styles.COLOR_PRIMARY)
            else:
                btn.config(bg=styles.BG_SIDEBAR, fg=styles.TXT_SECONDARY)
                
        # Hide all views and show active one
        for t, view in self.views.items():
            if t == tag:
                view.pack(expand=True, fill="both")
            else:
                view.pack_forget()

    # =========================================================================
    # VIEW: WALLET MANAGEMENT
    # =========================================================================
    def create_wallet_view(self):
        view = ttk.Frame(self.content_container)
        self.views["wallet"] = view
        
        # Header
        header_frame = ttk.Frame(view)
        header_frame.pack(fill="x", pady=(0, styles.PAD_LG))
        
        lbl_title = ttk.Label(header_frame, text="Quản lý Ví", font=styles.FONT_TITLE)
        lbl_title.pack(side="left")
        
        # Action Buttons
        btn_action_frame = ttk.Frame(header_frame)
        btn_action_frame.pack(side="right")
        
        btn_new_wallet = ttk.Button(btn_action_frame, text="Tạo / Khôi phục ví", style="Primary.TButton", command=self.open_wallet_wizard)
        btn_new_wallet.pack(side="right", padx=styles.PAD_SM)
        
        # Body
        body_frame = ttk.Frame(view)
        body_frame.pack(expand=True, fill="both")
        
        # Wallet selector card
        select_card = ttk.Frame(body_frame, style="Card.TFrame")
        select_card.pack(fill="x", pady=(0, styles.PAD_MD), ipady=styles.PAD_SM)
        
        lbl_select = tk.Label(select_card, text="Chọn ví sử dụng:", font=styles.FONT_HEADER, bg=styles.BG_CARD, fg=styles.TXT_PRIMARY)
        lbl_select.pack(side="left", padx=styles.PAD_MD)
        
        self.wallet_combo = ttk.Combobox(select_card, state="readonly", width=30)
        self.wallet_combo.pack(side="left", padx=styles.PAD_MD, pady=styles.PAD_MD)
        self.wallet_combo.bind("<<ComboboxSelected>>", lambda e: self.on_wallet_select())
        
        # Wallet info cards container
        self.wallet_info_frame = ttk.Frame(body_frame)
        self.wallet_info_frame.pack(expand=True, fill="both")
        
        # Placeholder when no wallet is selected
        self.no_wallet_lbl = ttk.Label(
            self.wallet_info_frame, text="Vui lòng chọn hoặc tạo ví mới để bắt đầu.",
            font=styles.FONT_SUBTITLE, foreground=styles.TXT_SECONDARY
        )
        self.no_wallet_lbl.pack(pady=styles.PAD_XL)

    def update_wallet_list(self):
        wallets = self.wallet_mgr.list_wallets()
        self.wallet_combo["values"] = wallets
        if not wallets:
            self.wallet_combo.set("")

    def on_wallet_select(self):
        wallet_name = self.wallet_combo.get()
        if not wallet_name:
            return
            
        self.config.set("last_wallet_name", wallet_name)
        
        # Hide placeholder
        self.no_wallet_lbl.pack_forget()
        
        # Clear previous info elements if any
        for widget in self.wallet_info_frame.winfo_children():
            widget.destroy()
            
        # Draw Wallet Info
        wallet_dir = os.path.join("wallets", wallet_name)
        
        # Read Addresses
        pay_addr = ""
        stake_addr = ""
        
        pay_addr_path = os.path.join(wallet_dir, "payment.addr")
        if os.path.exists(pay_addr_path):
            with open(pay_addr_path, "r") as f:
                pay_addr = f.read().strip()
                
        stake_addr_path = os.path.join(wallet_dir, "stake.addr")
        if os.path.exists(stake_addr_path):
            with open(stake_addr_path, "r") as f:
                stake_addr = f.read().strip()
                
        # Card 1: Addresses
        addr_card = ttk.Frame(self.wallet_info_frame, style="Card.TFrame")
        addr_card.pack(fill="x", pady=styles.PAD_SM, ipady=styles.PAD_SM)
        
        # Address Details
        self.create_address_row(addr_card, "Tên Ví:", wallet_name, is_copyable=False)
        self.create_address_row(addr_card, "Địa chỉ ví (payment.addr):", pay_addr, is_copyable=True)
        self.create_address_row(addr_card, "Địa chỉ ủy thác (stake.addr):", stake_addr, is_copyable=True)
        
        # Card 2: Balance and UTXOs (Online queries)
        self.balance_card = ttk.Frame(self.wallet_info_frame, style="Card.TFrame")
        self.balance_card.pack(fill="both", expand=True, pady=styles.PAD_SM, ipady=styles.PAD_SM)
        
        self.lbl_balance_title = tk.Label(
            self.balance_card, text="Số dư ví (Blockfrost Preprod/Mainnet)",
            font=styles.FONT_HEADER, bg=styles.BG_CARD, fg=styles.COLOR_PRIMARY
        )
        self.lbl_balance_title.pack(anchor="w", padx=styles.PAD_MD, pady=styles.PAD_SM)
        
        self.lbl_balance_val = tk.Label(
            self.balance_card, text="Đang tải...",
            font=styles.FONT_TITLE, bg=styles.BG_CARD, fg=styles.COLOR_SUCCESS
        )
        self.lbl_balance_val.pack(anchor="w", padx=styles.PAD_MD, pady=styles.PAD_XS)
        
        # UTXOs table
        self.utxo_frame = ttk.Frame(self.balance_card)
        self.utxo_frame.pack(fill="both", expand=True, padx=styles.PAD_MD, pady=styles.PAD_SM)
        
        # Fetch balance on background thread
        if pay_addr:
            threading.Thread(target=self.fetch_wallet_balance_bg, args=(pay_addr,), daemon=True).start()

    def create_address_row(self, parent, label_text, value_text, is_copyable=True):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=styles.PAD_MD, pady=styles.PAD_SM)
        row.configure(style="Card.TFrame")
        
        lbl = tk.Label(row, text=label_text, font=styles.FONT_BODY_BOLD, bg=styles.BG_CARD, fg=styles.TXT_SECONDARY, width=25, anchor="w")
        lbl.pack(side="left")
        
        val_entry = ttk.Entry(row, font=styles.FONT_CODE, width=65)
        val_entry.insert(0, value_text)
        val_entry.configure(state="readonly")
        val_entry.pack(side="left", fill="x", expand=True, padx=styles.PAD_SM)
        
        if is_copyable:
            btn_copy = ttk.Button(row, text="Copy", width=8, command=lambda: self.copy_to_clipboard(value_text))
            btn_copy.pack(side="left")

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Đã sao chép", "Đã sao chép nội dung vào Clipboard thành công!")

    def fetch_wallet_balance_bg(self, address):
        try:
            utxos = self.api.get_utxos(address)
            
            # Sum lovelaces
            total_lovelace = 0
            for utxo in utxos:
                for amt in utxo["amount"]:
                    if amt["unit"] == "lovelace":
                        total_lovelace += int(amt["quantity"])
                        break
                        
            ada_bal = total_lovelace / 1000000.0
            
            def update_ui():
                if not hasattr(self, "lbl_balance_val") or not self.lbl_balance_val.winfo_exists():
                    return
                self.lbl_balance_val.config(text=f"{ada_bal:,.6f} ADA")
                
                # Render UTXOs list
                for widget in self.utxo_frame.winfo_children():
                    widget.destroy()
                    
                if not utxos:
                    lbl_empty = tk.Label(
                        self.utxo_frame, text="Không tìm thấy UTXO nào. Ví đang trống.",
                        font=styles.FONT_BODY, bg=styles.BG_CARD, fg=styles.TXT_SECONDARY
                    )
                    lbl_empty.pack(pady=styles.PAD_MD)
                    return
                    
                # Setup treeview
                tree = ttk.Treeview(self.utxo_frame, columns=("tx_hash", "amount"), show="headings", height=5)
                tree.heading("tx_hash", text="Tx Hash (UTXO Index)")
                tree.heading("amount", text="Số dư (ADA)")
                tree.column("tx_hash", width=500)
                tree.column("amount", width=150, anchor="e")
                tree.pack(side="left", fill="both", expand=True)
                
                sb = ttk.Scrollbar(self.utxo_frame, orient="vertical", command=tree.yview)
                sb.pack(side="right", fill="y")
                tree.configure(yscrollcommand=sb.set)
                
                for utxo in utxos:
                    tx_hash = f"{utxo['tx_hash']}#{utxo['tx_index']}"
                    # sum lovelaces in this utxo
                    lovelaces = 0
                    for amt in utxo["amount"]:
                        if amt["unit"] == "lovelace":
                            lovelaces += int(amt["quantity"])
                    tree.insert("", "end", values=(tx_hash, f"{lovelaces/1000000.0:,.6f} ADA"))
                    
            self.after(0, update_ui)
        except Exception as e:
            err_msg = str(e)
            def update_err(msg=err_msg):
                if hasattr(self, "lbl_balance_val") and self.lbl_balance_val.winfo_exists():
                    self.lbl_balance_val.config(text="Không thể tải số dư", fg=styles.COLOR_DANGER)
                    lbl_err = tk.Label(
                        self.utxo_frame, text=f"Lỗi: {msg}",
                        font=styles.FONT_BODY, bg=styles.BG_CARD, fg=styles.COLOR_DANGER
                    )
                    lbl_err.pack(pady=styles.PAD_MD)
            self.after(0, update_err)

    # =========================================================================
    # DIALOG WIZARD: CREATE / RESTORE WALLET
    # =========================================================================
    def open_wallet_wizard(self):
        wizard = tk.Toplevel(self)
        wizard.title("Trình tạo / Khôi phục ví Cardano")
        wizard.geometry("700x500")
        wizard.configure(bg=styles.BG_MAIN)
        wizard.transient(self)
        wizard.grab_set()
        
        # State
        self.wizard_state = {
            "name": "",
            "mode": "",  # "create" or "restore"
            "phrase": "",
            "password": ""
        }
        
        # Wizard Container
        container = ttk.Frame(wizard, padding=styles.PAD_LG)
        container.pack(expand=True, fill="both")
        
        self.wizard_frames = {}
        
        # 1. Step 1: Wallet Name & Mode Selection
        step1 = ttk.Frame(container)
        self.wizard_frames["step1"] = step1
        
        lbl_w_title = ttk.Label(step1, text="Tạo mới hoặc khôi phục Ví", font=styles.FONT_SUBTITLE)
        lbl_w_title.pack(pady=(0, styles.PAD_LG))
        
        row_name = ttk.Frame(step1)
        row_name.pack(fill="x", pady=styles.PAD_SM)
        lbl_name = ttk.Label(row_name, text="Tên ví:", width=15)
        lbl_name.pack(side="left")
        ent_name = ttk.Entry(row_name, width=30)
        ent_name.pack(side="left")
        ent_name.focus()
        
        # Mode buttons
        mode_frame = ttk.Frame(step1)
        mode_frame.pack(fill="x", pady=styles.PAD_LG)
        
        btn_mode_create = ttk.Button(
            mode_frame, text="Tạo ví mới hoàn toàn", style="Primary.TButton",
            command=lambda: self.to_wizard_step2(wizard, ent_name.get(), "create")
        )
        btn_mode_create.pack(side="left", padx=styles.PAD_SM, fill="x", expand=True)
        
        btn_mode_restore = ttk.Button(
            mode_frame, text="Khôi phục ví bằng cụm 24 từ",
            command=lambda: self.to_wizard_step2(wizard, ent_name.get(), "restore")
        )
        btn_mode_restore.pack(side="left", padx=styles.PAD_SM, fill="x", expand=True)
        
        step1.pack(expand=True, fill="both")

    def to_wizard_step2(self, wizard, wallet_name, mode):
        wallet_name = re.sub(r'[^a-zA-Z0-9_-]', '', wallet_name)
        if not wallet_name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên ví hợp lệ (chữ cái, số, gạch ngang, gạch dưới).")
            return
            
        if wallet_name in self.wallet_mgr.list_wallets():
            overwrite = messagebox.askyesno(
                "Ví đã tồn tại",
                f"Ví '{wallet_name}' đã tồn tại. Bạn có chắc chắn muốn ghi đè? Toàn bộ khóa cũ sẽ bị xóa vĩnh viễn!"
            )
            if not overwrite:
                return
                
        self.wizard_state["name"] = wallet_name
        self.wizard_state["mode"] = mode
        
        # Hide step 1
        self.wizard_frames["step1"].pack_forget()
        
        # Create Step 2 frame
        step2 = ttk.Frame(wizard.winfo_children()[0])
        self.wizard_frames["step2"] = step2
        
        if mode == "create":
            # Generate phrase
            try:
                phrase = self.wallet_mgr.generate_recovery_phrase()
                self.wizard_state["phrase"] = phrase
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể tạo cụm từ khôi phục: {e}")
                wizard.destroy()
                return
                
            lbl_phrase_title = ttk.Label(step2, text="Cụm từ khôi phục 24 từ của bạn", font=styles.FONT_SUBTITLE)
            lbl_phrase_title.pack(pady=(0, styles.PAD_SM))
            
            lbl_warning = tk.Label(
                step2, text="QUAN TRỌNG: Hãy viết lại 24 từ này ra giấy và lưu trữ cực kỳ an toàn!\nNếu mất cụm từ này, bạn sẽ mất toàn bộ tài sản vĩnh viễn.",
                font=styles.FONT_BODY_BOLD, fg=styles.COLOR_DANGER, bg=styles.BG_MAIN
            )
            lbl_warning.pack(pady=styles.PAD_SM)
            
            phrase_box = scrolledtext.ScrolledText(
                step2, height=4, width=60, font=styles.FONT_CODE_BOLD, wrap="word",
                bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY, insertbackground=styles.TXT_PRIMARY,
                selectbackground=styles.COLOR_PRIMARY, selectforeground=styles.BG_MAIN,
                relief="flat", borderwidth=1, highlightbackground=styles.BORDER_COLOR,
                highlightcolor=styles.COLOR_PRIMARY
            )
            phrase_box.insert("1.0", phrase)
            phrase_box.configure(state="disabled")
            phrase_box.pack(pady=styles.PAD_MD)
            
            # Checkbox confirming they wrote it down
            confirm_var = tk.BooleanVar()
            chk_confirm = ttk.Checkbutton(step2, text="Tôi đã ghi lại cụm từ khôi phục ra giấy và cất giữ an toàn.", variable=confirm_var)
            chk_confirm.pack(pady=styles.PAD_SM)
            
            # Next button
            btn_next = ttk.Button(
                step2, text="Tiếp theo", style="Primary.TButton",
                command=lambda: self.to_wizard_step3(wizard, confirm_var.get())
            )
            btn_next.pack(side="right", pady=styles.PAD_MD)
            
        else: # restore
            lbl_restore_title = ttk.Label(step2, text="Nhập cụm 24 từ khôi phục", font=styles.FONT_SUBTITLE)
            lbl_restore_title.pack(pady=(0, styles.PAD_SM))
            
            lbl_restore_desc = ttk.Label(step2, text="Nhập các từ cách nhau bởi khoảng trắng:", foreground=styles.TXT_SECONDARY)
            lbl_restore_desc.pack(anchor="w", pady=styles.PAD_XS)
            
            phrase_box = scrolledtext.ScrolledText(
                step2, height=6, width=60, font=styles.FONT_CODE, wrap="word",
                bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY, insertbackground=styles.TXT_PRIMARY,
                selectbackground=styles.COLOR_PRIMARY, selectforeground=styles.BG_MAIN,
                relief="flat", borderwidth=1, highlightbackground=styles.BORDER_COLOR,
                highlightcolor=styles.COLOR_PRIMARY
            )
            phrase_box.pack(pady=styles.PAD_MD)
            phrase_box.focus()
            
            btn_next = ttk.Button(
                step2, text="Tiếp theo", style="Primary.TButton",
                command=lambda: self.to_wizard_step3_restore(wizard, phrase_box.get("1.0", "end-1c"))
            )
            btn_next.pack(side="right", pady=styles.PAD_MD)
            
        step2.pack(expand=True, fill="both")

    def to_wizard_step3(self, wizard, confirmed):
        if not confirmed:
            messagebox.showwarning("Cảnh báo", "Bạn cần xác nhận đã lưu cụm từ khôi phục trước khi tiếp tục.")
            return
        self.show_password_step(wizard)

    def to_wizard_step3_restore(self, wizard, phrase):
        phrase = phrase.strip().lower()
        words = phrase.split()
        if len(words) != 24:
            messagebox.showerror("Lỗi cụm từ", f"Cụm từ khôi phục phải chứa đúng 24 từ. Bạn hiện nhập {len(words)} từ.")
            return
        self.wizard_state["phrase"] = phrase
        self.show_password_step(wizard)

    def show_password_step(self, wizard):
        # Hide step 2
        self.wizard_frames["step2"].pack_forget()
        
        # Create Step 3 frame
        step3 = ttk.Frame(wizard.winfo_children()[0])
        self.wizard_frames["step3"] = step3
        
        lbl_pwd_title = ttk.Label(step3, text="Thiết lập mật khẩu ví", font=styles.FONT_SUBTITLE)
        lbl_pwd_title.pack(pady=(0, styles.PAD_LG))
        
        lbl_pwd_desc = ttk.Label(step3, text="Mật khẩu này sẽ dùng để mã hóa khóa riêng tư của bạn.", foreground=styles.TXT_SECONDARY)
        lbl_pwd_desc.pack(anchor="w", pady=(0, styles.PAD_SM))
        
        row_pwd1 = ttk.Frame(step3)
        row_pwd1.pack(fill="x", pady=styles.PAD_SM)
        lbl_pwd1 = ttk.Label(row_pwd1, text="Mật khẩu mới:", width=20)
        lbl_pwd1.pack(side="left")
        ent_pwd1 = ttk.Entry(row_pwd1, show="*", width=30)
        ent_pwd1.pack(side="left")
        ent_pwd1.focus()
        
        row_pwd2 = ttk.Frame(step3)
        row_pwd2.pack(fill="x", pady=styles.PAD_SM)
        lbl_pwd2 = ttk.Label(row_pwd2, text="Xác nhận mật khẩu:", width=20)
        lbl_pwd2.pack(side="left")
        ent_pwd2 = ttk.Entry(row_pwd2, show="*", width=30)
        ent_pwd2.pack(side="left")
        
        btn_submit = ttk.Button(
            step3, text="Tạo Ví", style="Primary.TButton",
            command=lambda: self.run_wallet_generation(wizard, ent_pwd1.get(), ent_pwd2.get())
        )
        btn_submit.pack(side="right", pady=styles.PAD_MD)
        
        step3.pack(expand=True, fill="both")

    def run_wallet_generation(self, wizard, p1, p2):
        if not p1:
            messagebox.showerror("Lỗi", "Mật khẩu không được để trống.")
            return
        if p1 != p2:
            messagebox.showerror("Lỗi", "Mật khẩu xác nhận không trùng khớp.")
            return
            
        self.wizard_state["password"] = p1
        
        # Hide step 3
        self.wizard_frames["step3"].pack_forget()
        
        # Create loading frame
        loading_frame = ttk.Frame(wizard.winfo_children()[0])
        loading_frame.pack(expand=True, fill="both")
        
        lbl_status = ttk.Label(loading_frame, text="Đang tạo các khóa và địa chỉ ví...\nQuá trình này có thể mất vài giây.", font=styles.FONT_SUBTITLE, justify="center")
        lbl_status.pack(pady=styles.PAD_XL)
        
        progress = ttk.Progressbar(loading_frame, mode="indeterminate", length=400)
        progress.pack(pady=styles.PAD_MD)
        progress.start(10)
        
        # Run generation on background thread to prevent UI freezing
        def worker():
            try:
                def progress_cb(msg):
                    self.after(0, lambda: lbl_status.config(text=msg))
                    
                pay_addr, stake_addr = self.wallet_mgr.create_wallet(
                    self.wizard_state["name"],
                    self.wizard_state["password"],
                    self.wizard_state["phrase"],
                    progress_cb
                )
                
                def success_ui():
                    progress.stop()
                    loading_frame.pack_forget()
                    
                    finish_frame = ttk.Frame(wizard.winfo_children()[0])
                    finish_frame.pack(expand=True, fill="both")
                    
                    lbl_ok = tk.Label(finish_frame, text="TẠO VÍ THÀNH CÔNG!", font=styles.FONT_SUBTITLE, fg=styles.COLOR_SUCCESS, bg=styles.BG_MAIN)
                    lbl_ok.pack(pady=styles.PAD_MD)
                    
                    lbl_addr_desc = ttk.Label(finish_frame, text="Địa chỉ ví của bạn:")
                    lbl_addr_desc.pack(anchor="w")
                    
                    addr_box = ttk.Entry(finish_frame, font=styles.FONT_CODE, width=60)
                    addr_box.insert(0, pay_addr)
                    addr_box.configure(state="readonly")
                    addr_box.pack(pady=styles.PAD_SM)
                    
                    btn_close = ttk.Button(finish_frame, text="Hoàn tất", style="Primary.TButton", command=lambda: self.finish_wizard(wizard))
                    btn_close.pack(pady=styles.PAD_LG)
                    
                self.after(0, success_ui)
                
            except Exception as e:
                err_msg = str(e)
                def fail_ui(msg=err_msg):
                    progress.stop()
                    messagebox.showerror("Lỗi tạo ví", f"Quá trình sinh khóa ví thất bại:\n{msg}")
                    wizard.destroy()
                self.after(0, fail_ui)
                
        threading.Thread(target=worker, daemon=True).start()

    def finish_wizard(self, wizard):
        wizard.destroy()
        self.update_wallet_list()
        self.wallet_combo.set(self.wizard_state["name"])
        self.on_wallet_select()

    # =========================================================================
    # VIEW: ONLINE TRANSACTIONS
    # =========================================================================
    def create_online_view(self):
        view = ttk.Frame(self.content_container)
        self.views["online"] = view
        
        # Tabs for Online
        notebook = ttk.Notebook(view)
        notebook.pack(expand=True, fill="both")
        
        tab_build = ttk.Frame(notebook)
        tab_submit = ttk.Frame(notebook)
        
        notebook.add(tab_build, text="1. Xây dựng Giao dịch")
        notebook.add(tab_submit, text="2. Gửi Giao dịch đã ký")
        
        self.setup_online_build_tab(tab_build)
        self.setup_online_submit_tab(tab_submit)

    def setup_online_build_tab(self, tab):
        # Grid layout
        left_side = ttk.Frame(tab)
        left_side.pack(side="left", fill="both", expand=True, padx=styles.PAD_SM, pady=styles.PAD_SM)
        
        right_side = ttk.Frame(tab)
        right_side.pack(side="right", fill="y", padx=styles.PAD_SM, pady=styles.PAD_SM)
        
        # Left elements (inputs)
        # Select sender address
        sender_frame = ttk.LabelFrame(left_side, text=" Ví gửi tiền (Chọn từ ví offline hiện có) ", padding=styles.PAD_SM)
        sender_frame.pack(fill="x", pady=styles.PAD_SM)
        
        self.send_wallet_combo = ttk.Combobox(sender_frame, state="readonly", width=30)
        self.send_wallet_combo.pack(side="left", padx=styles.PAD_SM, pady=styles.PAD_SM)
        self.send_wallet_combo.bind("<<ComboboxSelected>>", lambda e: self.on_send_wallet_select())
        
        btn_refresh_utxos = ttk.Button(sender_frame, text="Tải số dư & UTXO", command=self.on_send_wallet_select)
        btn_refresh_utxos.pack(side="left", padx=styles.PAD_SM)
        
        self.lbl_send_bal = tk.Label(sender_frame, text="Số dư: - ADA", font=styles.FONT_BODY_BOLD, bg=styles.BG_MAIN, fg=styles.COLOR_SUCCESS)
        self.lbl_send_bal.pack(side="right", padx=styles.PAD_SM)
        
        # UTXO Selection Multi-select
        utxo_list_frame = ttk.LabelFrame(left_side, text=" Chọn UTXO đầu vào (Hoặc để trống để chọn toàn bộ) ", padding=styles.PAD_SM)
        utxo_list_frame.pack(fill="both", expand=True, pady=styles.PAD_SM)
        
        # Listbox with scrollbar
        self.utxo_listbox = tk.Listbox(
            utxo_list_frame, selectmode="multiple", bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY,
            selectbackground=styles.COLOR_PRIMARY, selectforeground=styles.BG_MAIN,
            font=styles.FONT_CODE, bd=0, highlightthickness=0
        )
        self.utxo_listbox.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(utxo_list_frame, orient="vertical", command=self.utxo_listbox.yview)
        sb.pack(side="right", fill="y")
        self.utxo_listbox.configure(yscrollcommand=sb.set)
        self.loaded_utxos_data = [] # Stores actual UTXO details matching listbox index
        
        # TX Destination & Amount
        tx_details_frame = ttk.LabelFrame(left_side, text=" Thông tin người nhận ", padding=styles.PAD_SM)
        tx_details_frame.pack(fill="x", pady=styles.PAD_SM)
        
        # Standard Transaction Inputs
        self.row_dest = ttk.Frame(tx_details_frame)
        self.row_dest.pack(fill="x", pady=styles.PAD_XS)
        ttk.Label(self.row_dest, text="Địa chỉ nhận:", width=15).pack(side="left")
        self.ent_dest = ttk.Entry(self.row_dest, width=50)
        self.ent_dest.pack(side="left", fill="x", expand=True)
        
        self.row_amount = ttk.Frame(tx_details_frame)
        self.row_amount.pack(fill="x", pady=styles.PAD_XS)
        ttk.Label(self.row_amount, text="Số lượng ADA:", width=15).pack(side="left")
        self.ent_amount = ttk.Entry(self.row_amount, width=20)
        self.ent_amount.pack(side="left")
        
        # Delegation Option Checkbox
        self.is_delegation_var = tk.BooleanVar(value=False)
        self.chk_delegation = ttk.Checkbutton(
            tx_details_frame, text="Ủy thác (Delegation) / Đăng ký Stake Pool & DRep Conway Era",
            variable=self.is_delegation_var, command=self.toggle_delegation_fields
        )
        self.chk_delegation.pack(anchor="w", pady=styles.PAD_SM)
        
        # Delegation Inputs Frame (Initially hidden)
        self.delegation_inputs_frame = ttk.Frame(tx_details_frame)
        
        # DRep Row
        row_drep = ttk.Frame(self.delegation_inputs_frame)
        row_drep.pack(fill="x", pady=styles.PAD_XS)
        ttk.Label(row_drep, text="DRep lựa chọn:", width=15).pack(side="left")
        self.drep_choice_combo = ttk.Combobox(row_drep, values=["C2VN (Mặc định)", "Bỏ phiếu trắng (Abstain)", "Luôn bất tín nhiệm", "DRep ID tự chọn"], state="readonly", width=25)
        self.drep_choice_combo.set("C2VN (Mặc định)")
        self.drep_choice_combo.pack(side="left")
        self.drep_choice_combo.bind("<<ComboboxSelected>>", lambda e: self.toggle_drep_custom_field())
        
        self.ent_drep_custom = ttk.Entry(row_drep, width=30)
        self.ent_drep_custom.pack(side="left", padx=styles.PAD_SM)
        self.ent_drep_custom.insert(0, "Nhập custom DRep ID...")
        self.ent_drep_custom.pack_forget() # Hide initially
        
        # Stake Pool Row
        row_pool = ttk.Frame(self.delegation_inputs_frame)
        row_pool.pack(fill="x", pady=styles.PAD_XS)
        ttk.Label(row_pool, text="Stake Pool ID:", width=15).pack(side="left")
        self.pool_choice_combo = ttk.Combobox(row_pool, values=["Pool HADA (Mặc định)", "Nhập Pool ID khác"], state="readonly", width=25)
        self.pool_choice_combo.set("Pool HADA (Mặc định)")
        self.pool_choice_combo.pack(side="left")
        self.pool_choice_combo.bind("<<ComboboxSelected>>", lambda e: self.toggle_pool_custom_field())
        
        self.ent_pool_custom = ttk.Entry(row_pool, width=30)
        self.ent_pool_custom.pack(side="left", padx=styles.PAD_SM)
        self.ent_pool_custom.insert(0, "18109d01af0c5c4495a64a9de061ad621156729afc699128c0ceee0e")
        self.ent_pool_custom.pack_forget() # Hide initially
        
        # Actions
        btn_build_tx = ttk.Button(left_side, text="Xây dựng giao dịch thô", style="Primary.TButton", command=self.on_build_raw_tx)
        btn_build_tx.pack(fill="x", pady=styles.PAD_MD)
        
        # Right elements (output)
        right_title = ttk.Label(right_side, text="Giao dịch thô sinh ra (tx_raw.txt)", font=styles.FONT_HEADER)
        right_title.pack(anchor="w", pady=styles.PAD_SM)
        
        self.tx_raw_textbox = scrolledtext.ScrolledText(
            right_side, width=40, height=12, font=styles.FONT_CODE, wrap="char",
            bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY, insertbackground=styles.TXT_PRIMARY,
            selectbackground=styles.COLOR_PRIMARY, selectforeground=styles.BG_MAIN,
            relief="flat", borderwidth=1, highlightbackground=styles.BORDER_COLOR,
            highlightcolor=styles.COLOR_PRIMARY
        )
        self.tx_raw_textbox.pack(fill="both", expand=True)
        
        # Copy & QR buttons row
        btn_row_right = ttk.Frame(right_side)
        btn_row_right.pack(fill="x", pady=styles.PAD_XS)
        
        btn_copy_hex = ttk.Button(btn_row_right, text="Copy Hex CBOR", command=self.copy_raw_hex)
        btn_copy_hex.pack(side="left", fill="x", expand=True, padx=(0, styles.PAD_XS))
        
        btn_gen_raw_qr = ttk.Button(btn_row_right, text="Tạo mã QR", command=self.on_generate_raw_qr)
        btn_gen_raw_qr.pack(side="right", fill="x", expand=True, padx=(styles.PAD_XS, 0))
        
        # Output QR code canvas
        self.raw_qr_lbl = tk.Label(right_side, text="Không có QR code nào.", bg=styles.BG_MAIN, fg=styles.TXT_PRIMARY)
        self.raw_qr_lbl.pack(pady=styles.PAD_SM)

    def toggle_delegation_fields(self):
        if self.is_delegation_var.get():
            self.delegation_inputs_frame.pack(fill="x", pady=styles.PAD_SM)
            # Hide destination inputs
            self.row_dest.pack_forget()
            self.row_amount.pack_forget()
        else:
            self.delegation_inputs_frame.pack_forget()
            # Show destination inputs
            self.row_dest.pack(fill="x", pady=styles.PAD_XS)
            self.row_amount.pack(fill="x", pady=styles.PAD_XS)

    def toggle_drep_custom_field(self):
        choice = self.drep_choice_combo.get()
        if "DRep ID tự chọn" in choice:
            self.ent_drep_custom.pack(side="left", padx=styles.PAD_SM)
            self.ent_drep_custom.delete(0, tk.END)
        else:
            self.ent_drep_custom.pack_forget()

    def toggle_pool_custom_field(self):
        choice = self.pool_choice_combo.get()
        if "Nhập Pool ID khác" in choice:
            self.ent_pool_custom.pack(side="left", padx=styles.PAD_SM)
        else:
            self.ent_pool_custom.pack_forget()

    def update_send_wallet_combo(self):
        wallets = self.wallet_mgr.list_wallets()
        self.send_wallet_combo["values"] = wallets

    def on_send_wallet_select(self):
        wallet_name = self.send_wallet_combo.get()
        if not wallet_name:
            return
            
        wallet_dir = os.path.join("wallets", wallet_name)
        pay_addr_path = os.path.join(wallet_dir, "payment.addr")
        if not os.path.exists(pay_addr_path):
            return
            
        with open(pay_addr_path, "r") as f:
            address = f.read().strip()
            
        self.lbl_send_bal.config(text="Đang tải...", fg=styles.TXT_SECONDARY)
        self.utxo_listbox.delete(0, tk.END)
        self.loaded_utxos_data = []
        
        def worker():
            try:
                utxos = self.api.get_utxos(address)
                total_lovelace = 0
                for utxo in utxos:
                    for amt in utxo["amount"]:
                        if amt["unit"] == "lovelace":
                            total_lovelace += int(amt["quantity"])
                            break
                            
                def update_ui():
                    self.lbl_send_bal.config(text=f"Số dư: {total_lovelace / 1000000.0:,.6f} ADA", fg=styles.COLOR_SUCCESS)
                    for utxo in utxos:
                        tx_hash = f"{utxo['tx_hash']}#{utxo['tx_index']}"
                        lovelaces = 0
                        for amt in utxo["amount"]:
                            if amt["unit"] == "lovelace":
                                lovelaces += int(amt["quantity"])
                        self.utxo_listbox.insert(tk.END, f"{tx_hash[:20]}...#{utxo['tx_index']} ({lovelaces/1000000.0:.2f} ADA)")
                        self.loaded_utxos_data.append(utxo)
                self.after(0, update_ui)
            except Exception as e:
                self.after(0, lambda: self.lbl_send_bal.config(text="Lỗi tải dữ liệu", fg=styles.COLOR_DANGER))
                
        threading.Thread(target=worker, daemon=True).start()

    def on_build_raw_tx(self):
        wallet_name = self.send_wallet_combo.get()
        if not wallet_name:
            messagebox.showerror("Lỗi", "Vui lòng chọn ví gửi tiền.")
            return
            
        # Get selected UTXOs
        selected_indices = self.utxo_listbox.curselection()
        if not selected_indices:
            # If nothing is selected, use all UTXOs
            selected_utxos = self.loaded_utxos_data
        else:
            selected_utxos = [self.loaded_utxos_data[i] for i in selected_indices]
            
        if not selected_utxos:
            messagebox.showerror("Lỗi", "Ví gửi không có UTXO nào hoặc chưa tải UTXO.")
            return
            
        # Common parameters
        wallet_dir = os.path.join("wallets", wallet_name)
        pay_addr_path = os.path.join(wallet_dir, "payment.addr")
        with open(pay_addr_path, "r") as f:
            sender_address = f.read().strip()
            
        # Create temp dir
        temp_dir = self.wallet_mgr.get_secure_temp_dir()
        
        # Output paths
        pparams_path = os.path.join(temp_dir, "pparams.json")
        output_raw_path = os.path.join(temp_dir, "tx.raw")
        
        # Build logic in background
        def worker():
            try:
                # 1. Fetch parameters
                self.after(0, lambda: self.tx_raw_textbox.delete("1.0", tk.END))
                self.after(0, lambda: self.tx_raw_textbox.insert(tk.END, "Đang tải tham số mạng lưới (Protocol Parameters)..."))
                
                self.api.get_pparams(pparams_path)
                latest_slot = self.api.get_latest_slot()
                
                # Check mode
                if not self.is_delegation_var.get():
                    # Standard Transaction
                    dest = self.ent_dest.get().strip()
                    amount_ada = self.ent_amount.get().strip()
                    if not dest or not amount_ada:
                        raise ValueError("Vui lòng điền đầy đủ địa chỉ nhận và số lượng ADA.")
                    try:
                        amount_lovelace = int(float(amount_ada) * 1000000)
                    except:
                        raise ValueError("Số lượng ADA không hợp lệ.")
                        
                    res = self.tx_builder.build_standard_tx(
                        sender_address, dest, amount_lovelace, selected_utxos,
                        pparams_path, latest_slot, output_raw_path, temp_dir, dust_action="raise"
                    )
                else:
                    # Delegation Transaction
                    # Get stake key vkey path
                    stake_vkey_path = os.path.join(wallet_dir, "stake.vkey")
                    stake_addr_path = os.path.join(wallet_dir, "stake.addr")
                    if not os.path.exists(stake_vkey_path) or not os.path.exists(stake_addr_path):
                        raise FileNotFoundError("Không tìm thấy khóa stake.vkey hoặc stake.addr trong ví.")
                        
                    with open(stake_addr_path, "r") as f:
                        stake_address = f.read().strip()
                        
                    # Check stake registration on-chain
                    is_registered = self.api.check_stake_registered(stake_address)
                    deposit = 2000000 if not is_registered else 0
                    
                    # Gather pool ID
                    pool_choice = self.pool_choice_combo.get()
                    if "Nhập Pool ID khác" in pool_choice:
                        pool_id = self.ent_pool_custom.get().strip()
                    else:
                        pool_id = "18109d01af0c5c4495a64a9de061ad621156729afc699128c0ceee0e" # HADA
                        
                    if not pool_id:
                        raise ValueError("Stake Pool ID không được để trống.")
                        
                    # DRep options
                    drep_choice_label = self.drep_choice_combo.get()
                    drep_custom_id = ""
                    if "C2VN" in drep_choice_label:
                        drep_choice = "c2vn"
                    elif "Abstain" in drep_choice_label:
                        drep_choice = "abstain"
                    elif "Luôn bất tín nhiệm" in drep_choice_label:
                        drep_choice = "no_confidence"
                    else:
                        drep_choice = "custom"
                        drep_custom_id = self.ent_drep_custom.get().strip()
                        if not drep_custom_id:
                            raise ValueError("Custom DRep ID không được để trống.")
                            
                    res = self.tx_builder.build_delegation_tx(
                        sender_address, stake_vkey_path, pool_id, drep_choice, drep_custom_id,
                        is_registered, deposit, selected_utxos, pparams_path, latest_slot,
                        output_raw_path, temp_dir, dust_action="raise"
                    )

                # Check if we hit a dust warning
                if res.get("status") == "dust_warning":
                    # Prompt user on UI thread
                    def prompt_user():
                        opt = messagebox.askyesno(
                            "Bụi giao dịch (Dust Warning)",
                            f"Tiền thừa lẻ ({res['change']/1000000.0:.6f} ADA) quá thấp để trả về ví (cardano tối thiểu là 1 ADA).\n"
                            f"Bạn có muốn tăng thêm phí giao dịch để quyên góp luôn số tiền thừa lẻ này không?\n"
                            f"Nếu chọn No, giao dịch sẽ bị hủy."
                        )
                        if opt:
                            # Re-run build on background with donate option
                            threading.Thread(target=self.run_final_build_bg, args=(
                                sender_address, wallet_dir, selected_utxos, pparams_path, latest_slot, output_raw_path, temp_dir, "donate"
                            ), daemon=True).start()
                        else:
                            self.tx_raw_textbox.delete("1.0", tk.END)
                            self.tx_raw_textbox.insert(tk.END, "Giao dịch đã bị hủy do tiền thừa nhỏ hơn mức tối thiểu 1 ADA.")
                    self.after(0, prompt_user)
                    return

                # Success
                self.after(0, lambda: self.display_built_tx(res, wallet_dir))
                
            except Exception as e:
                err_msg = str(e)
                def show_err(msg=err_msg):
                    self.tx_raw_textbox.delete("1.0", tk.END)
                    self.tx_raw_textbox.insert(tk.END, f"Lỗi xây dựng giao dịch:\n{msg}")
                    messagebox.showerror("Lỗi", f"Xây dựng giao dịch thất bại:\n{msg}")
                self.after(0, show_err)
            finally:
                # We do not clean up temp_dir yet if we need to re-run for dust, 
                # but in regular success/fail we should clean it up eventually
                # Let's clean up after displaying or on error
                if 'res' in locals() and res.get("status") != "dust_warning":
                    self.wallet_mgr.cleanup_temp_dir(temp_dir)
                elif 'res' not in locals():
                    self.wallet_mgr.cleanup_temp_dir(temp_dir)

        threading.Thread(target=worker, daemon=True).start()

    def run_final_build_bg(self, sender_address, wallet_dir, selected_utxos, pparams_path, latest_slot, output_raw_path, temp_dir, action):
        try:
            if not self.is_delegation_var.get():
                dest = self.ent_dest.get().strip()
                amount_ada = self.ent_amount.get().strip()
                amount_lovelace = int(float(amount_ada) * 1000000)
                res = self.tx_builder.build_standard_tx(
                    sender_address, dest, amount_lovelace, selected_utxos,
                    pparams_path, latest_slot, output_raw_path, temp_dir, dust_action=action
                )
            else:
                stake_vkey_path = os.path.join(wallet_dir, "stake.vkey")
                stake_addr_path = os.path.join(wallet_dir, "stake.addr")
                with open(stake_addr_path, "r") as f:
                    stake_address = f.read().strip()
                is_registered = self.api.check_stake_registered(stake_address)
                deposit = 2000000 if not is_registered else 0
                
                pool_choice = self.pool_choice_combo.get()
                if "Nhập Pool ID khác" in pool_choice:
                    pool_id = self.ent_pool_custom.get().strip()
                else:
                    pool_id = "18109d01af0c5c4495a64a9de061ad621156729afc699128c0ceee0e"
                    
                drep_choice_label = self.drep_choice_combo.get()
                drep_custom_id = ""
                if "C2VN" in drep_choice_label:
                    drep_choice = "c2vn"
                elif "Abstain" in drep_choice_label:
                    drep_choice = "abstain"
                elif "Luôn bất tín nhiệm" in drep_choice_label:
                    drep_choice = "no_confidence"
                else:
                    drep_choice = "custom"
                    drep_custom_id = self.ent_drep_custom.get().strip()
                    
                res = self.tx_builder.build_delegation_tx(
                    sender_address, stake_vkey_path, pool_id, drep_choice, drep_custom_id,
                    is_registered, deposit, selected_utxos, pparams_path, latest_slot,
                    output_raw_path, temp_dir, dust_action=action
                )
                
            self.after(0, lambda: self.display_built_tx(res, wallet_dir))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: messagebox.showerror("Lỗi", f"Xây dựng giao dịch thất bại:\n{msg}"))
        finally:
            self.wallet_mgr.cleanup_temp_dir(temp_dir)

    def display_built_tx(self, res, wallet_dir):
        cbor = res["cbor_hex"]
        fee = res["fee"]
        change = res["change"]
        
        prefix = "TxBodyConwayDelegation:" if self.is_delegation_var.get() else "TxBodyConway:"
        full_text = f"{prefix}{cbor}"
        
        self.tx_raw_textbox.delete("1.0", tk.END)
        self.tx_raw_textbox.insert(tk.END, full_text)
        
        # Save to wallets tx_raw.txt
        raw_txt_path = os.path.join(wallet_dir, "tx_raw.txt")
        with open(raw_txt_path, "w") as f:
            f.write(full_text)
            
        info_msg = f"Đã xuất giao dịch thô thành công!\n- Phí ước tính: {fee/1000000.0:.6f} ADA\n- Trả lại change: {change/1000000.0:.6f} ADA\n"
        if "deposit" in res:
            info_msg += f"- Tiền đặt cọc key deposit: {res['deposit']/1000000.0:.6f} ADA\n"
        info_msg += f"Đã lưu tệp tại: {raw_txt_path}"
        messagebox.showinfo("Thành công", info_msg)
        
        # Generate QR code
        qr_path = os.path.join(wallet_dir, "tx_raw_qr.png")
        if self.generate_qr_code_file(full_text, qr_path):
            self.display_qr_code(qr_path, self.raw_qr_lbl)
        else:
            self.raw_qr_lbl.config(text="Không thể tạo QR (Cài đặt 'qrencode'.)")

    def generate_qr_code_file(self, text, output_path):
        try:
            if shutil.which("qrencode"):
                # Use level L (lowest error correction) to handle long hex strings
                subprocess.run(["qrencode", "-l", "L", "-o", output_path, text], check=True)
                return True
        except Exception as e:
            print(f"Error calling qrencode: {e}")
        return False

    def display_qr_code(self, qr_path, label_widget):
        if not HAS_IMAGETK:
            label_widget.config(
                text="Không hiển thị được QR do thiếu ImageTk.\n"
                     "Khắc phục: sudo apt-get install python3-pil.imagetk",
                foreground=styles.COLOR_WARNING
            )
            return
        try:
            img = Image.open(qr_path)
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize((200, 200), resample_filter)
            photo = ImageTk.PhotoImage(img)
            label_widget.config(image=photo, text="")
            label_widget.image = photo  # keep reference
        except Exception as e:
            label_widget.config(text=f"Không thể hiển thị ảnh QR: {e}")

    def read_qr_from_file(self, textbox):
        if not shutil.which("zbarimg"):
            messagebox.showerror(
                "Thiếu dependency",
                "Chương trình cần công cụ 'zbarimg' để quét mã QR từ ảnh.\n"
                "Hãy cài đặt bằng lệnh:\nsudo apt-get install zbar-tools"
            )
            return

        path = filedialog.askopenfilename(
            title="Chọn ảnh chứa mã QR",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        try:
            res = subprocess.run(
                ["zbarimg", "-q", "--raw", "--nodbus", path],
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode == 0:
                decoded = res.stdout.strip()
                if decoded:
                    textbox.delete("1.0", tk.END)
                    textbox.insert(tk.END, decoded)
                    messagebox.showinfo("Thành công", "Đã đọc mã QR thành công!")
                else:
                    messagebox.showwarning("Cảnh báo", "Mã QR rỗng (không chứa dữ liệu).")
            elif res.returncode == 4:
                messagebox.showerror("Lỗi", "Không tìm thấy mã QR nào trong ảnh được chọn.")
            else:
                err_msg = res.stderr.strip() or res.stdout.strip() or f"Exit code {res.returncode}"
                messagebox.showerror("Lỗi", f"Quá trình quét mã QR thất bại:\n{err_msg}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể quét mã QR từ file: {e}")

    def read_qr_from_webcam(self, textbox):
        if not shutil.which("zbarcam"):
            messagebox.showerror(
                "Thiếu dependency",
                "Chương trình cần công cụ 'zbarcam' để quét mã QR qua camera.\n"
                "Hãy cài đặt bằng lệnh:\nsudo apt-get install zbar-tools"
            )
            return

        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title("Đang quét mã QR qua Webcam")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
        
        lbl_status = ttk.Label(
            dialog, 
            text="Đang kết nối với Camera...\n\nHãy đưa mã QR vào trước ống kính camera.\nCửa sổ camera sẽ tự đóng sau khi quét thành công.",
            justify="center",
            font=styles.FONT_BODY,
            wraplength=360
        )
        lbl_status.pack(pady=styles.PAD_MD, padx=styles.PAD_MD)
        
        proc = None
        cancelled = False
        
        def cancel_scan():
            nonlocal cancelled
            cancelled = True
            if proc:
                try:
                    proc.terminate()
                except:
                    pass
            dialog.destroy()
            
        btn_cancel = ttk.Button(dialog, text="Hủy bỏ", command=cancel_scan)
        btn_cancel.pack(pady=styles.PAD_SM)
        
        def run_camera():
            nonlocal proc
            try:
                # Use --raw to get only the decoded data
                proc = subprocess.Popen(
                    ["zbarcam", "-1", "--nodbus", "--raw"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Wait for the output or process completion
                stdout_data, stderr_data = proc.communicate()
                
                if cancelled:
                    return
                    
                if proc.returncode == 0:
                    decoded = stdout_data.strip()
                    if decoded:
                        def update_ui():
                            textbox.delete("1.0", tk.END)
                            textbox.insert(tk.END, decoded)
                            dialog.destroy()
                            messagebox.showinfo("Thành công", "Đã quét mã QR thành công từ camera!")
                        self.after(0, update_ui)
                    else:
                        def update_ui():
                            dialog.destroy()
                            messagebox.showwarning("Cảnh báo", "Không nhận được dữ liệu từ camera.")
                        self.after(0, update_ui)
                else:
                    err_msg = stderr_data.strip() or "Không tìm thấy thiết bị camera hoặc camera đang bị ứng dụng khác chiếm dụng."
                    def update_ui():
                        dialog.destroy()
                        messagebox.showerror("Lỗi Camera", f"Không thể mở camera quét mã:\n{err_msg}")
                    self.after(0, update_ui)
                    
            except Exception as e:
                if not cancelled:
                    def update_ui():
                        dialog.destroy()
                        messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {e}")
                    self.after(0, update_ui)
                    
        threading.Thread(target=run_camera, daemon=True).start()

    def on_generate_raw_qr(self):
        text = self.tx_raw_textbox.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("Lỗi", "Không có nội dung giao dịch thô để tạo mã QR.")
            return
        
        wallet_name = self.send_wallet_combo.get()
        wallet_dir = os.path.join("wallets", wallet_name) if wallet_name else "wallets"
        os.makedirs(wallet_dir, exist_ok=True)
        
        qr_path = os.path.join(wallet_dir, "tx_raw_qr_manual.png")
        if self.generate_qr_code_file(text, qr_path):
            self.display_qr_code(qr_path, self.raw_qr_lbl)
            messagebox.showinfo("Thành công", f"Đã tạo mã QR thành công!\nẢnh được lưu tại: {qr_path}")
        else:
            self.raw_qr_lbl.config(text="Không thể tạo QR (Cài đặt 'qrencode'.)")

    def on_generate_signed_qr(self):
        text = self.sign_out_textbox.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("Lỗi", "Không có nội dung giao dịch đã ký để tạo mã QR.")
            return
        
        wallet_name = self.sign_wallet_combo.get()
        wallet_dir = os.path.join("wallets", wallet_name) if wallet_name else "wallets"
        os.makedirs(wallet_dir, exist_ok=True)
        
        qr_path = os.path.join(wallet_dir, "tx_signed_qr_manual.png")
        if self.generate_qr_code_file(text, qr_path):
            self.display_qr_code(qr_path, self.signed_qr_lbl)
            messagebox.showinfo("Thành công", f"Đã tạo mã QR thành công!\nẢnh được lưu tại: {qr_path}")
        else:
            self.signed_qr_lbl.config(text="Không thể tạo QR (Cài đặt 'qrencode'.)")

    def on_generate_submit_qr(self):
        text = self.submit_textbox.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("Lỗi", "Không có nội dung giao dịch để tạo mã QR.")
            return
        
        os.makedirs("wallets", exist_ok=True)
        qr_path = os.path.join("wallets", "tx_submit_qr.png")
        if self.generate_qr_code_file(text, qr_path):
            self.display_qr_code(qr_path, self.submit_qr_lbl)
            messagebox.showinfo("Thành công", f"Đã tạo mã QR thành công!\nẢnh được lưu tại: {qr_path}")
        else:
            self.submit_qr_lbl.config(text="Không thể tạo QR (Cài đặt 'qrencode'.)")

    def copy_raw_hex(self):
        c = self.tx_raw_textbox.get("1.0", tk.END).strip()
        if c:
            self.copy_to_clipboard(c)

    def setup_online_submit_tab(self, tab):
        top_frame = ttk.Frame(tab, padding=styles.PAD_SM)
        top_frame.pack(fill="x")
        
        ttk.Label(top_frame, text="Nhập hoặc dán giao dịch đã ký (Bắt đầu bằng TxConway:):").pack(anchor="w", pady=styles.PAD_XS)
        
        self.submit_textbox = scrolledtext.ScrolledText(
            tab, height=12, font=styles.FONT_CODE, wrap="char",
            bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY, insertbackground=styles.TXT_PRIMARY,
            selectbackground=styles.COLOR_PRIMARY, selectforeground=styles.BG_MAIN,
            relief="flat", borderwidth=1, highlightbackground=styles.BORDER_COLOR,
            highlightcolor=styles.COLOR_PRIMARY
        )
        self.submit_textbox.pack(fill="both", expand=True, padx=styles.PAD_SM, pady=styles.PAD_SM)
        
        btn_row = ttk.Frame(tab)
        btn_row.pack(fill="x", padx=styles.PAD_SM, pady=styles.PAD_SM)
        
        btn_load = ttk.Button(btn_row, text="Đọc từ file tx_signed.txt", command=self.on_load_signed_file)
        btn_load.pack(side="left", padx=(0, styles.PAD_XS))
        
        btn_read_img = ttk.Button(btn_row, text="Đọc QR từ ảnh", command=lambda: self.read_qr_from_file(self.submit_textbox))
        btn_read_img.pack(side="left", padx=styles.PAD_XS)
        
        btn_scan_cam = ttk.Button(btn_row, text="Quét QR Camera", command=lambda: self.read_qr_from_webcam(self.submit_textbox))
        btn_scan_cam.pack(side="left", padx=styles.PAD_XS)
        
        btn_gen_submit_qr = ttk.Button(btn_row, text="Tạo mã QR", command=self.on_generate_submit_qr)
        btn_gen_submit_qr.pack(side="left", padx=(styles.PAD_XS, 0))
        
        btn_submit = ttk.Button(btn_row, text="Gửi giao dịch (Submit)", style="Primary.TButton", command=self.on_submit_signed_tx)
        btn_submit.pack(side="right")
        
        # QR Code Display for Submit Tab (Center/Bottom)
        self.submit_qr_lbl = tk.Label(tab, text="Không có QR code nào.", bg=styles.BG_MAIN, fg=styles.TXT_PRIMARY)
        self.submit_qr_lbl.pack(pady=styles.PAD_MD)

    def on_load_signed_file(self):
        path = filedialog.askopenfilename(
            title="Chọn tệp tin giao dịch đã ký",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            try:
                with open(path, "r") as f:
                    content = f.read().strip()
                self.submit_textbox.delete("1.0", tk.END)
                self.submit_textbox.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")

    def on_submit_signed_tx(self):
        raw_text = self.submit_textbox.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showerror("Lỗi", "Vui lòng nhập chuỗi giao dịch đã ký.")
            return
            
        if raw_text.startswith("TxConway:"):
            cbor_hex = raw_text.replace("TxConway:", "")
        else:
            cbor_hex = raw_text
            
        cbor_hex = re.sub(r'\s+', '', cbor_hex)
        
        def worker():
            try:
                self.after(0, lambda: self.submit_textbox.insert(tk.END, "\n\nĐang gửi giao dịch lên blockchain...\n"))
                tx_id = self.api.submit_tx(cbor_hex)
                
                # Check status
                if isinstance(tx_id, dict) and ("error" in tx_id or "status_code" in tx_id):
                    err_msg = tx_id.get("message") or str(tx_id)
                    raise Exception(f"API Blockfrost trả lỗi: {err_msg}")
                    
                def success():
                    self.submit_textbox.insert(tk.END, f"\nThành công! ID giao dịch (TxID):\n{tx_id}\n")
                    opt = messagebox.askyesno(
                        "Giao dịch thành công",
                        f"Giao dịch đã được gửi thành công!\nTxID: {tx_id}\n\nBạn có muốn copy TxID này không?"
                    )
                    if opt:
                        self.copy_to_clipboard(tx_id)
                self.after(0, success)
                
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: messagebox.showerror("Gửi thất bại", f"Lỗi submit giao dịch:\n{msg}"))
                
        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # VIEW: OFFLINE SIGNING
    # =========================================================================
    def create_offline_view(self):
        view = ttk.Frame(self.content_container)
        self.views["offline"] = view
        
        # Title
        lbl_title = ttk.Label(view, text="Ký Giao Dịch Ngoại Tuyến (Offline Cold)", font=styles.FONT_TITLE)
        lbl_title.pack(anchor="w", pady=(0, styles.PAD_LG))
        
        # Grid layout
        left_side = ttk.Frame(view)
        left_side.pack(side="left", fill="both", expand=True, padx=styles.PAD_SM, pady=styles.PAD_SM)
        
        right_side = ttk.Frame(view)
        right_side.pack(side="right", fill="y", padx=styles.PAD_SM, pady=styles.PAD_SM)
        
        # Form
        row_w = ttk.Frame(left_side)
        row_w.pack(fill="x", pady=styles.PAD_SM)
        ttk.Label(row_w, text="Chọn ví ký:", width=18).pack(side="left")
        self.sign_wallet_combo = ttk.Combobox(row_w, state="readonly", width=30)
        self.sign_wallet_combo.pack(side="left")
        
        row_pw = ttk.Frame(left_side)
        row_pw.pack(fill="x", pady=styles.PAD_SM)
        ttk.Label(row_pw, text="Mật khẩu ví:", width=18).pack(side="left")
        self.ent_sign_pwd = ttk.Entry(row_pw, show="*", width=30)
        self.ent_sign_pwd.pack(side="left")
        
        # Input raw TX area
        ttk.Label(left_side, text="Dán hoặc tải chuỗi giao dịch thô (TxBodyConway:):").pack(anchor="w", pady=(styles.PAD_MD, styles.PAD_XS))
        self.sign_raw_textbox = scrolledtext.ScrolledText(
            left_side, height=8, font=styles.FONT_CODE, wrap="char",
            bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY, insertbackground=styles.TXT_PRIMARY,
            selectbackground=styles.COLOR_PRIMARY, selectforeground=styles.BG_MAIN,
            relief="flat", borderwidth=1, highlightbackground=styles.BORDER_COLOR,
            highlightcolor=styles.COLOR_PRIMARY
        )
        self.sign_raw_textbox.pack(fill="both", expand=True, pady=styles.PAD_SM)
        
        btn_row_left = ttk.Frame(left_side)
        btn_row_left.pack(fill="x", pady=styles.PAD_SM)
        
        btn_load_raw = ttk.Button(btn_row_left, text="Đọc từ file tx_raw.txt", command=self.on_load_raw_tx_file)
        btn_load_raw.pack(side="left", padx=(0, styles.PAD_XS))
        
        btn_read_img = ttk.Button(btn_row_left, text="Đọc QR từ ảnh", command=lambda: self.read_qr_from_file(self.sign_raw_textbox))
        btn_read_img.pack(side="left", padx=styles.PAD_XS)
        
        btn_scan_cam = ttk.Button(btn_row_left, text="Quét QR Camera", command=lambda: self.read_qr_from_webcam(self.sign_raw_textbox))
        btn_scan_cam.pack(side="left", padx=styles.PAD_XS)
        
        btn_sign = ttk.Button(btn_row_left, text="Ký Giao Dịch", style="Primary.TButton", command=self.on_sign_transaction)
        btn_sign.pack(side="right", padx=(styles.PAD_XS, 0))
        
        # Right output side
        right_title = ttk.Label(right_side, text="Giao dịch đã ký (tx_signed.txt)", font=styles.FONT_HEADER)
        right_title.pack(anchor="w", pady=styles.PAD_SM)
        
        self.sign_out_textbox = scrolledtext.ScrolledText(
            right_side, width=40, height=12, font=styles.FONT_CODE, wrap="char",
            bg=styles.BG_INPUT, fg=styles.TXT_PRIMARY, insertbackground=styles.TXT_PRIMARY,
            selectbackground=styles.COLOR_PRIMARY, selectforeground=styles.BG_MAIN,
            relief="flat", borderwidth=1, highlightbackground=styles.BORDER_COLOR,
            highlightcolor=styles.COLOR_PRIMARY
        )
        self.sign_out_textbox.pack(fill="both", expand=True)
        
        btn_row_right = ttk.Frame(right_side)
        btn_row_right.pack(fill="x", pady=styles.PAD_XS)
        
        btn_copy_signed = ttk.Button(btn_row_right, text="Copy Signed Hex", command=self.copy_signed_hex)
        btn_copy_signed.pack(side="left", fill="x", expand=True, padx=(0, styles.PAD_XS))
        
        btn_gen_signed_qr = ttk.Button(btn_row_right, text="Tạo mã QR", command=self.on_generate_signed_qr)
        btn_gen_signed_qr.pack(side="right", fill="x", expand=True, padx=(styles.PAD_XS, 0))
        
        self.signed_qr_lbl = tk.Label(right_side, text="Không có QR code nào.", bg=styles.BG_MAIN, fg=styles.TXT_PRIMARY)
        self.signed_qr_lbl.pack(pady=styles.PAD_SM)

    def update_sign_wallet_combo(self):
        wallets = self.wallet_mgr.list_wallets()
        self.sign_wallet_combo["values"] = wallets

    def on_load_raw_tx_file(self):
        path = filedialog.askopenfilename(
            title="Chọn tệp tin giao dịch thô",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            try:
                with open(path, "r") as f:
                    content = f.read().strip()
                self.sign_raw_textbox.delete("1.0", tk.END)
                self.sign_raw_textbox.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")

    def on_sign_transaction(self):
        wallet_name = self.sign_wallet_combo.get()
        password = self.ent_sign_pwd.get()
        raw_text = self.sign_raw_textbox.get("1.0", tk.END).strip()
        
        if not wallet_name:
            messagebox.showerror("Lỗi", "Vui lòng chọn ví thực hiện ký.")
            return
        if not password:
            messagebox.showerror("Lỗi", "Vui lòng nhập mật khẩu ví.")
            return
        if not raw_text:
            messagebox.showerror("Lỗi", "Vui lòng nhập dữ liệu giao dịch thô.")
            return
            
        # Detect transaction type
        is_delegation = False
        if raw_text.startswith("TxBodyConwayDelegation:"):
            is_delegation = True
            cbor_hex = raw_text.replace("TxBodyConwayDelegation:", "")
        elif raw_text.startswith("TxBodyConway:"):
            cbor_hex = raw_text.replace("TxBodyConway:", "")
        else:
            cbor_hex = raw_text
            
        cbor_hex = re.sub(r'\s+', '', cbor_hex)
        
        self.sign_out_textbox.delete("1.0", tk.END)
        self.sign_out_textbox.insert(tk.END, "Đang ký giao dịch ngoại tuyến...")
        
        def worker():
            try:
                def progress(msg):
                    self.after(0, lambda: self.sign_out_textbox.insert(tk.END, f"\n{msg}"))
                    
                signed_cbor = self.wallet_mgr.sign_transaction(
                    wallet_name, password, cbor_hex, is_delegation, progress
                )
                
                def success():
                    # Clear password
                    self.ent_sign_pwd.delete(0, tk.END)
                    
                    full_signed_text = f"TxConway:{signed_cbor}"
                    self.sign_out_textbox.delete("1.0", tk.END)
                    self.sign_out_textbox.insert(tk.END, full_signed_text)
                    
                    # Generate QR
                    wallet_dir = os.path.join("wallets", wallet_name)
                    qr_path = os.path.join(wallet_dir, "tx_signed_qr.png")
                    if self.generate_qr_code_file(full_signed_text, qr_path):
                        self.display_qr_code(qr_path, self.signed_qr_lbl)
                    else:
                        self.signed_qr_lbl.config(text="Không thể tạo QR (Cài đặt 'qrencode'.)")
                        
                    messagebox.showinfo(
                        "Thành công",
                        f"Giao dịch đã được ký thành công!\nFile đã lưu tại:\n{wallet_dir}/tx_signed.txt"
                    )
                self.after(0, success)
                
            except Exception as e:
                err_msg = str(e)
                def fail(msg=err_msg):
                    self.sign_out_textbox.delete("1.0", tk.END)
                    self.sign_out_textbox.insert(tk.END, f"Lỗi ký giao dịch:\n{msg}")
                    messagebox.showerror("Ký thất bại", f"Lỗi khi ký giao dịch:\n{msg}")
                self.after(0, fail)
                
        threading.Thread(target=worker, daemon=True).start()

    def copy_signed_hex(self):
        c = self.sign_out_textbox.get("1.0", tk.END).strip()
        if c:
            self.copy_to_clipboard(c)

    # =========================================================================
    # VIEW: SETTINGS
    # =========================================================================
    def create_settings_view(self):
        view = ttk.Frame(self.content_container)
        self.views["settings"] = view
        
        lbl_title = ttk.Label(view, text="Cài Đặt Hệ Thống", font=styles.FONT_TITLE)
        lbl_title.pack(anchor="w", pady=(0, styles.PAD_LG))
        
        card = ttk.Frame(view, style="Card.TFrame")
        card.pack(fill="x", pady=styles.PAD_SM, ipady=styles.PAD_MD)
        
        # Blockfrost Settings
        lbl_section = tk.Label(card, text="Blockfrost API", font=styles.FONT_HEADER, bg=styles.BG_CARD, fg=styles.COLOR_PRIMARY)
        lbl_section.pack(anchor="w", padx=styles.PAD_MD, pady=styles.PAD_SM)
        
        # Blockfrost Key
        row_key = ttk.Frame(card)
        row_key.pack(fill="x", padx=styles.PAD_MD, pady=styles.PAD_XS)
        row_key.configure(style="Card.TFrame")
        ttk.Label(row_key, text="Blockfrost API Key:", width=20).pack(side="left")
        self.ent_bf_key = ttk.Entry(row_key, width=45)
        self.ent_bf_key.pack(side="left")
        
        # Blockfrost URL
        row_url = ttk.Frame(card)
        row_url.pack(fill="x", padx=styles.PAD_MD, pady=styles.PAD_XS)
        row_url.configure(style="Card.TFrame")
        ttk.Label(row_url, text="Blockfrost Base URL:", width=20).pack(side="left")
        self.ent_bf_url = ttk.Combobox(row_url, width=43, values=[
            "https://cardano-mainnet.blockfrost.io/api/v0",
            "https://cardano-preprod.blockfrost.io/api/v0",
            "https://cardano-preview.blockfrost.io/api/v0"
        ])
        self.ent_bf_url.pack(side="left")
        self.ent_bf_url.bind("<<ComboboxSelected>>", self.on_bf_url_selected)
        
        # Network Magic
        row_magic = ttk.Frame(card)
        row_magic.pack(fill="x", padx=styles.PAD_MD, pady=styles.PAD_XS)
        row_magic.configure(style="Card.TFrame")
        ttk.Label(row_magic, text="Mạng / Network:", width=20).pack(side="left")
        self.ent_magic = ttk.Combobox(row_magic, width=15, values=["Mainnet", "Preprod", "Preview"])
        self.ent_magic.pack(side="left")
        self.ent_magic.bind("<<ComboboxSelected>>", self.on_network_selected)
        
        # Path to Cardano cli / address
        lbl_binaries = tk.Label(card, text="Đường dẫn Cardano Binaries", font=styles.FONT_HEADER, bg=styles.BG_CARD, fg=styles.COLOR_PRIMARY)
        lbl_binaries.pack(anchor="w", padx=styles.PAD_MD, pady=(styles.PAD_MD, styles.PAD_SM))
        
        # CLI path
        row_cli = ttk.Frame(card)
        row_cli.pack(fill="x", padx=styles.PAD_MD, pady=styles.PAD_XS)
        row_cli.configure(style="Card.TFrame")
        ttk.Label(row_cli, text="cardano-cli path:", width=20).pack(side="left")
        self.ent_cli_path = ttk.Entry(row_cli, width=45)
        self.ent_cli_path.pack(side="left")
        btn_browse_cli = ttk.Button(row_cli, text="Browse", width=8, command=self.browse_cardano_cli)
        btn_browse_cli.pack(side="left", padx=styles.PAD_SM)
        
        # Address path
        row_addr = ttk.Frame(card)
        row_addr.pack(fill="x", padx=styles.PAD_MD, pady=styles.PAD_XS)
        row_addr.configure(style="Card.TFrame")
        ttk.Label(row_addr, text="cardano-address path:", width=20).pack(side="left")
        self.ent_addr_path = ttk.Entry(row_addr, width=45)
        self.ent_addr_path.pack(side="left")
        btn_browse_addr = ttk.Button(row_addr, text="Browse", width=8, command=self.browse_cardano_address)
        btn_browse_addr.pack(side="left", padx=styles.PAD_SM)
        
        # Save settings button
        btn_save = ttk.Button(view, text="Lưu Cài Đặt", style="Primary.TButton", command=self.on_save_settings)
        btn_save.pack(anchor="e", pady=styles.PAD_LG)

    def browse_cardano_cli(self):
        filename = filedialog.askopenfilename(title="Chọn file thực thi cardano-cli")
        if filename:
            self.ent_cli_path.delete(0, tk.END)
            self.ent_cli_path.insert(0, filename)

    def browse_cardano_address(self):
        filename = filedialog.askopenfilename(title="Chọn file thực thi cardano-address")
        if filename:
            self.ent_addr_path.delete(0, tk.END)
            self.ent_addr_path.insert(0, filename)

    def load_settings_into_ui(self):
        self.ent_bf_key.delete(0, tk.END)
        self.ent_bf_key.insert(0, self.config.get("blockfrost_api_key") or "")
        
        self.ent_bf_url.delete(0, tk.END)
        self.ent_bf_url.insert(0, self.config.get("blockfrost_url") or "")
        
        self.ent_magic.delete(0, tk.END)
        magic = self.config.get("network_magic")
        if magic == 1:
            self.ent_magic.set("Mainnet")
        elif magic == 2:
            url = self.config.get("blockfrost_url") or ""
            if "preview" in url:
                self.ent_magic.set("Preview")
            else:
                self.ent_magic.set("Preprod")
        else:
            self.ent_magic.insert(0, str(magic) if magic is not None else "")
        
        self.ent_cli_path.delete(0, tk.END)
        self.ent_cli_path.insert(0, self.config.get("cardano_cli_path") or "")
        
        self.ent_addr_path.delete(0, tk.END)
        self.ent_addr_path.insert(0, self.config.get("cardano_address_path") or "")

    def on_save_settings(self):
        try:
            magic_val = self.ent_magic.get().strip()
            try:
                if magic_val == "Mainnet":
                    magic = 1
                elif magic_val in ("Preprod", "Preview"):
                    magic = 2
                elif magic_val == "":
                    magic = None
                else:
                    magic = int(magic_val)
            except ValueError:
                messagebox.showerror("Lỗi", "Network Magic phải là số nguyên hoặc chọn từ danh sách.")
                return
                
            self.config.set("blockfrost_api_key", self.ent_bf_key.get().strip())
            self.config.set("blockfrost_url", self.ent_bf_url.get().strip())
            self.config.set("network_magic", magic)
            self.config.set("cardano_cli_path", self.ent_cli_path.get().strip())
            self.config.set("cardano_address_path", self.ent_addr_path.get().strip())
            
            # Re-init blockfrost API settings
            self.api.api_key = self.config.get("blockfrost_api_key")
            self.api.base_url = self.config.get("blockfrost_url").rstrip('/')
            
            messagebox.showinfo("Thành công", "Đã lưu cài đặt hệ thống thành công!")
            
            # Update listings and views
            self.update_wallet_list()
            self.update_send_wallet_combo()
            self.update_sign_wallet_combo()
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu cài đặt:\n{e}")

    def update_wallet_list(self):
        wallets = self.wallet_mgr.list_wallets()
        
        # Wallet management tab combobox
        self.wallet_combo["values"] = wallets
        
        # Transaction builder tab combo
        self.send_wallet_combo["values"] = wallets
        
        # Offline signing tab combo
        self.sign_wallet_combo["values"] = wallets

    def on_bf_url_selected(self, event=None):
        url = self.ent_bf_url.get().strip()
        if "mainnet" in url:
            self.ent_magic.set("Mainnet")
        elif "preprod" in url:
            self.ent_magic.set("Preprod")
        elif "preview" in url:
            self.ent_magic.set("Preview")

    def on_network_selected(self, event=None):
        net = self.ent_magic.get().strip()
        if net == "Mainnet":
            self.ent_bf_url.set("https://cardano-mainnet.blockfrost.io/api/v0")
        elif net == "Preprod":
            self.ent_bf_url.set("https://cardano-preprod.blockfrost.io/api/v0")
        elif net == "Preview":
            self.ent_bf_url.set("https://cardano-preview.blockfrost.io/api/v0")
