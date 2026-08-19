import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import asyncio
import logging
import csv
import os
import json
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

PAROLA_CHIAVE = "el"
ACCESSI_FILE  = "accessi_el.csv"
USERS_FILE    = "ids.json"
CONFIG_FILE   = "config.json"

C0  = "#0d0d0f"
C1  = "#141416"
C2  = "#1c1c20"
C3  = "#26262c"
C4  = "#32323a"
C5  = "#48484f"
DIV = "#2e2e36"

BLUE      = "#4f8ef7"
BLUE_DIM  = "#2a4a8a"
GREEN     = "#34c97a"
GREEN_DIM = "#1a5c3a"
RED       = "#f25c5c"
RED_DIM   = "#7a2020"
AMBER     = "#f5c542"
PURPLE    = "#a78bfa"

T1 = "#f0f0f5"
T2 = "#a0a0b0"
T3 = "#606070"

FN  = "Helvetica Neue" if os.name != "nt" else "Segoe UI"
FM  = "Menlo"          if os.name != "nt" else "Consolas"
FB  = (FN, 10, "bold")
FT  = (FN, 13, "bold")
FC  = (FN, 9)
FMC = (FM, 9)
FL  = (FN, 10)

access_mode      = "authorized"
authorized_users: list[dict] = []


def carica_config() -> str:
    path = _fp(CONFIG_FILE)
    if not os.path.isfile(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"token": "INSERISCI_QUI_IL_TUO_TOKEN"}, f, indent=2)
        except Exception as e:
            logging.error(f"Impossibile creare config.json: {e}")
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("token", "").strip()
    except Exception as e:
        logging.error(f"Errore lettura config.json: {e}")
        return ""


def salva_config(token: str):
    path = _fp(CONFIG_FILE)
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["token"] = token.strip()
    _scrivi_json_safe(path, data)


def _app_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _fp(filename: str) -> str:
    return os.path.join(_app_dir(), filename)


def _scrivi_json_safe(path: str, data) -> bool:
    import stat
    tmp = path + ".tmp"
    try:
        if os.path.isfile(path):
            try:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        if os.name == "nt" and os.path.isfile(path):
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        os.replace(tmp, path) if os.path.isfile(path) else os.rename(tmp, path)
        return True
    except Exception as e:
        try:
            os.remove(tmp)
        except Exception:
            pass
        logging.error(f"Errore scrittura {os.path.basename(path)}: {e}")
        return False


def _popup_permesso(filename: str):
    try:
        import tkinter.messagebox as mb
        mb.showerror(
            f"Permesso negato — {filename}",
            f"Impossibile salvare {filename}.\n\n"
            "Soluzioni rapide:\n"
            "  1. Chiudi il file se aperto in un editor\n"
            "  2. Tasto destro sul file → Proprietà → deseleziona Sola lettura\n"
            "  3. Esegui VS Code come Amministratore"
        )
    except Exception:
        pass


def carica_utenti() -> list[dict]:
    path = _fp(USERS_FILE)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [{"id": int(u["id"]), "label": str(u.get("label", ""))} for u in data]
    except Exception as e:
        logging.error(f"Errore lettura {USERS_FILE}: {e}")
    return []


def salva_utenti(users: list[dict]):
    if not _scrivi_json_safe(_fp(USERS_FILE), users):
        _popup_permesso(USERS_FILE)


def registra_accesso(user_id, username, full_name, chat_id):
    import stat
    path = _fp(ACCESSI_FILE)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_esiste = os.path.isfile(path)
    try:
        if file_esiste:
            try:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not file_esiste:
                w.writerow(["timestamp", "user_id", "username", "full_name", "chat_id"])
            w.writerow([ts, user_id, username or "N/A", full_name or "N/A", chat_id])
    except Exception as e:
        logging.error(f"Errore accessi CSV: {e}")


def autorizzato(user_id: int) -> bool:
    if access_mode == "all":
        return True
    return user_id in [u["id"] for u in authorized_users]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizzato(update.effective_user.id):
        return
    await update.message.reply_text(
        f"🤖 Bot attivo ✅\n\nScrivi *{PAROLA_CHIAVE}* o usa /el.",
        parse_mode="Markdown"
    )


async def cmd_top10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not autorizzato(user.id):
        return
    registra_accesso(user.id, user.username, user.full_name, update.effective_chat.id)
    testo = context.bot_data.get("top10_text", "_(nessun contenuto)_")
    if len(testo) > 4096:
        testo = testo[:4090] + "\n…"
    await update.message.reply_text(testo, parse_mode="Markdown")


async def rispondi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not autorizzato(user.id):
        return
    if (update.message.text or "").strip().lower() != PAROLA_CHIAVE.lower():
        return
    registra_accesso(user.id, user.username, user.full_name, update.effective_chat.id)
    testo = context.bot_data.get("top10_text", "_(nessun contenuto)_")
    if len(testo) > 4096:
        testo = testo[:4090] + "\n…"
    await update.message.reply_text(testo, parse_mode="Markdown")


def _mix(hex1: str, hex2: str, t: float = 0.15) -> str:
    h1, h2 = hex1.lstrip("#"), hex2.lstrip("#")
    r = int(int(h1[0:2], 16) * (1 - t) + int(h2[0:2], 16) * t)
    g = int(int(h1[2:4], 16) * (1 - t) + int(h2[2:4], 16) * t)
    b = int(int(h1[4:6], 16) * (1 - t) + int(h2[4:6], 16) * t)
    return f"#{min(r,255):02x}{min(g,255):02x}{min(b,255):02x}"


def glow_button(parent, text, command,
                base=BLUE, hover=None, fg="#ffffff",
                font=None, padx=16, pady=7, width=None):
    hov = hover or _mix(base, "#ffffff", 0.18)
    cfg = dict(
        text=text, command=command,
        bg=base, fg=fg,
        activebackground=hov, activeforeground=fg,
        relief="flat", bd=0,
        font=font or FL,
        padx=padx, pady=pady,
        cursor="hand2"
    )
    if width:
        cfg["width"] = width
    btn = tk.Button(parent, **cfg)
    btn.bind("<Enter>", lambda e: btn.config(bg=hov))
    btn.bind("<Leave>", lambda e: btn.config(bg=base))
    return btn


def ghost_button(parent, text, command, fg=T2, font=None, padx=10, pady=5):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=C3, fg=fg,
        activebackground=C4, activeforeground=T1,
        relief="flat", bd=0,
        font=font or FC,
        padx=padx, pady=pady,
        cursor="hand2"
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=C4))
    btn.bind("<Leave>", lambda e: btn.config(bg=C3))
    return btn


def sleek_entry(parent, textvariable=None, width=20, show=None, placeholder=""):
    e = tk.Entry(
        parent,
        bg=C3, fg=T1,
        insertbackground=BLUE,
        relief="flat", bd=0,
        font=FL,
        highlightthickness=1,
        highlightbackground=DIV,
        highlightcolor=BLUE,
        width=width,
    )
    if textvariable:
        e["textvariable"] = textvariable
    if show:
        e["show"] = show
    return e


def hdiv(parent, padx=0, pady=(8, 8)):
    tk.Frame(parent, bg=DIV, height=1).pack(fill="x", padx=padx, pady=pady)


def section_label(parent, text):
    tk.Label(parent, text=text.upper(), font=(FN, 8, "bold"),
             bg=C2, fg=T3, padx=0, pady=0).pack(anchor="w", pady=(0, 6))


class TabController:
    def __init__(self, parent, tabs: list[str]):
        self._frames: dict[str, tk.Frame] = {}
        self._btns:   dict[str, tk.Button] = {}

        nav = tk.Frame(parent, bg=C1, pady=0)
        nav.pack(fill="x")

        pill_wrap = tk.Frame(nav, bg=C3, padx=2, pady=2)
        pill_wrap.pack(side="left", padx=14, pady=10)

        for tab in tabs:
            btn = tk.Button(
                pill_wrap, text=tab,
                bg=C3, fg=T3,
                activebackground=C4, activeforeground=T1,
                relief="flat", bd=0,
                font=FC, padx=18, pady=5,
                cursor="hand2",
                command=lambda t=tab: self.show(t)
            )
            btn.pack(side="left")
            self._btns[tab] = btn

        hdiv(parent, pady=(0, 0))

        self._content = tk.Frame(parent, bg=C2)
        self._content.pack(fill="both", expand=True)

        for tab in tabs:
            self._frames[tab] = tk.Frame(self._content, bg=C2)

        self.show(tabs[0])

    def frame(self, tab: str) -> tk.Frame:
        return self._frames[tab]

    def show(self, tab: str):
        for f in self._frames.values():
            f.pack_forget()
        self._frames[tab].pack(fill="both", expand=True)
        for name, btn in self._btns.items():
            if name == tab:
                btn.config(bg=C2, fg=T1, font=FB)
            else:
                btn.config(bg=C3, fg=T3, font=FC)


class BachecaTab:
    def __init__(self, parent, get_users_fn, on_invia):
        self._get_users  = get_users_fn
        self._on_invia   = on_invia
        self._allegato   = None
        self._user_vars: dict[int, tk.BooleanVar] = {}
        self._checks: list[tk.Widget] = []
        self._build(parent)

    def _build(self, parent):
        cv = tk.Canvas(parent, bg=C2, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        body = tk.Frame(cv, bg=C2)
        win  = cv.create_window((0, 0), window=body, anchor="nw")

        body.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",   lambda e: cv.itemconfig(win, width=e.width))

        def _wheel(e):
            d = -1 * (e.delta // 120) if e.delta else (1 if e.num == 5 else -1)
            cv.yview_scroll(int(d), "units")
        cv.bind_all("<MouseWheel>", _wheel)
        cv.bind_all("<Button-4>",   _wheel)
        cv.bind_all("<Button-5>",   _wheel)

        P = 18

        dest_card = tk.Frame(body, bg=C3, padx=14, pady=14)
        dest_card.pack(fill="x", padx=P, pady=(P, 6))

        row0 = tk.Frame(dest_card, bg=C3)
        row0.pack(fill="x")
        tk.Label(row0, text="Destinatari", font=FB, bg=C3, fg=T1).pack(side="left")
        self._modo_var = tk.StringVar(value="all")

        modo_row = tk.Frame(dest_card, bg=C3)
        modo_row.pack(fill="x", pady=(10, 0))
        for val, lbl, clr in [("all", "Tutti", GREEN), ("manual", "Selezione", BLUE)]:
            tk.Radiobutton(
                modo_row, text=lbl, variable=self._modo_var, value=val,
                command=self._aggiorna_modo,
                bg=C3, fg=T2, selectcolor=C4,
                activebackground=C3, activeforeground=clr,
                font=FL, cursor="hand2"
            ).pack(side="left", padx=(0, 20))

        self._utenti_frame = tk.Frame(dest_card, bg=C3)
        self._utenti_frame.pack(fill="x", pady=(8, 0), padx=(4, 0))
        self._rebuild_checks()

        msg_card = tk.Frame(body, bg=C3, padx=14, pady=14)
        msg_card.pack(fill="x", padx=P, pady=6)

        mh = tk.Frame(msg_card, bg=C3)
        mh.pack(fill="x")
        tk.Label(mh, text="Messaggio", font=FB, bg=C3, fg=T1).pack(side="left")
        ghost_button(mh, "⌘  Incolla", self._incolla, font=FC).pack(side="right")

        hdiv(msg_card, pady=(8, 10))

        self._testo = scrolledtext.ScrolledText(
            msg_card, height=5, font=FL,
            bg=C4, fg=T1, insertbackground=BLUE,
            relief="flat", bd=0, wrap="word",
            highlightthickness=1,
            highlightbackground=DIV, highlightcolor=BLUE
        )
        self._testo.pack(fill="x")

        alleg_card = tk.Frame(body, bg=C3, padx=14, pady=14)
        alleg_card.pack(fill="x", padx=P, pady=6)

        tk.Label(alleg_card, text="Allegato", font=FB, bg=C3, fg=T1).pack(anchor="w")
        hdiv(alleg_card, pady=(8, 10))

        ar = tk.Frame(alleg_card, bg=C3)
        ar.pack(fill="x")
        ghost_button(ar, "Scegli file…", self._allega).pack(side="left")
        self._alleg_lbl = tk.Label(ar, text="Nessun file", bg=C3, fg=T3, font=FC)
        self._alleg_lbl.pack(side="left", padx=12)
        self._btn_rm = ghost_button(ar, "✕", self._rimuovi_allegato, fg=RED)
        self._btn_rm.config(state="disabled")
        self._btn_rm.pack(side="left")

        ora_card = tk.Frame(body, bg=C3, padx=14, pady=14)
        ora_card.pack(fill="x", padx=P, pady=6)

        tk.Label(ora_card, text="Orario invio", font=FB, bg=C3, fg=T1).pack(anchor="w")
        hdiv(ora_card, pady=(8, 10))

        orr = tk.Frame(ora_card, bg=C3)
        orr.pack(fill="x")
        tk.Label(orr, text="HH:MM", bg=C3, fg=T3, font=FC).pack(side="left", padx=(0, 10))
        self._ora_var = tk.StringVar()
        sleek_entry(orr, textvariable=self._ora_var, width=8).pack(side="left")
        tk.Label(orr, text="  vuoto = immediato", bg=C3, fg=T3, font=(FN, 8, "italic")).pack(side="left")

        btn_row = tk.Frame(body, bg=C2)
        btn_row.pack(fill="x", padx=P, pady=(8, P))
        glow_button(btn_row, "  Invia messaggio  ", self._invia,
                    base=BLUE, font=FB, padx=20, pady=9).pack(side="left")

    def _rebuild_checks(self):
        for w in self._checks:
            w.destroy()
        self._checks.clear()
        self._user_vars.clear()
        for u in self._get_users():
            var = tk.BooleanVar(value=True)
            self._user_vars[u["id"]] = var
            stato = "normal" if self._modo_var.get() == "manual" else "disabled"
            cb = tk.Checkbutton(
                self._utenti_frame,
                text=f'{u["label"]}   {u["id"]}',
                variable=var, state=stato,
                bg=C3, fg=T2, selectcolor=C4,
                activebackground=C3, activeforeground=T1,
                font=FC, cursor="hand2"
            )
            cb.pack(anchor="w", pady=1)
            self._checks.append(cb)

    def refresh_users(self):
        self._rebuild_checks()

    def _aggiorna_modo(self):
        s = "normal" if self._modo_var.get() == "manual" else "disabled"
        for w in self._checks:
            w.config(state=s)

    def _incolla(self):
        try:
            t = self._testo.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Appunti vuoti", "Nessun testo negli appunti.")
            return
        self._testo.delete("1.0", "end")
        self._testo.insert("1.0", t)

    def _allega(self):
        p = filedialog.askopenfilename(
            filetypes=[("Immagini", "*.jpg *.jpeg *.png *.gif *.webp"), ("Tutti", "*.*")])
        if p:
            self._allegato = p
            self._alleg_lbl.config(text=os.path.basename(p), fg=GREEN)
            self._btn_rm.config(state="normal")

    def _rimuovi_allegato(self):
        self._allegato = None
        self._alleg_lbl.config(text="Nessun file", fg=T3)
        self._btn_rm.config(state="disabled")

    def _destinatari(self):
        if self._modo_var.get() == "all":
            return [u["id"] for u in self._get_users()]
        return [uid for uid, v in self._user_vars.items() if v.get()]

    def svuota(self):
        self._testo.delete("1.0", "end")
        self._rimuovi_allegato()
        self._ora_var.set("")

    def _invia(self):
        testo = self._testo.get("1.0", "end").strip()
        dest  = self._destinatari()
        ora   = self._ora_var.get().strip()
        if not testo and not self._allegato:
            messagebox.showerror("Errore", "Inserisci un messaggio o allega un file.")
            return
        if not dest:
            messagebox.showerror("Errore", "Seleziona almeno un destinatario.")
            return
        ora_obj = None
        if ora:
            try:
                ora_obj = datetime.strptime(ora, "%H:%M").time()
            except ValueError:
                messagebox.showerror("Errore", "Formato orario non valido — usa HH:MM.")
                return
        self._on_invia(dest, testo, self._allegato, ora_obj)
        self.svuota()


class UtentiTab:
    COLS = ("ID Telegram", "Etichetta")
    CW   = (180, 300)

    def __init__(self, parent, users_ref: list, on_change):
        self._users     = users_ref
        self._on_change = on_change
        self._build(parent)

    def _build(self, parent):
        P = 18

        top = tk.Frame(parent, bg=C1, padx=P, pady=14)
        top.pack(fill="x")
        tk.Label(top, text="Utenti autorizzati", font=FT, bg=C1, fg=T1).pack(side="left")

        brow = tk.Frame(top, bg=C1)
        brow.pack(side="right")
        ghost_button(brow, "Importa JSON…", self._importa, font=FC).pack(side="right", padx=(6, 0))
        glow_button(brow, "Rimuovi", self._rimuovi,
                    base=RED, fg="#fff", font=FC, padx=10, pady=5).pack(side="right")

        hdiv(parent, pady=(0, 0))

        st = ttk.Style()
        st.theme_use("default")
        st.configure("U.Treeview",
                     background=C1, foreground=T1,
                     fieldbackground=C1, rowheight=28,
                     font=FMC, borderwidth=0)
        st.configure("U.Treeview.Heading",
                     background=C2, foreground=T3,
                     font=(FN, 9, "bold"), relief="flat", borderwidth=0)
        st.map("U.Treeview",
               background=[("selected", BLUE_DIM)],
               foreground=[("selected", T1)])

        tf = tk.Frame(parent, bg=C1)
        tf.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(tf, columns=self.COLS, show="headings", style="U.Treeview")
        for col, w in zip(self.COLS, self.CW):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, minwidth=60, anchor="w")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.tag_configure("e", background=C1)
        self._tree.tag_configure("o", background=C2)

        hdiv(parent, pady=(0, 0))

        form = tk.Frame(parent, bg=C2, padx=P, pady=16)
        form.pack(fill="x")

        tk.Label(form, text="Aggiungi utente", font=FB, bg=C2, fg=T1).pack(anchor="w", pady=(0, 10))

        fr = tk.Frame(form, bg=C2)
        fr.pack(fill="x")

        for lbl, var_name, w in [("ID Telegram", "_id_var", 18), ("Etichetta", "_lbl_var", 22)]:
            tk.Label(fr, text=lbl, bg=C2, fg=T3, font=FC, width=12, anchor="w").pack(side="left")
            v = tk.StringVar()
            setattr(self, var_name, v)
            sleek_entry(fr, textvariable=v, width=w).pack(side="left", padx=(0, 18))

        glow_button(fr, "Aggiungi", self._aggiungi,
                    base=GREEN, fg="#000", font=FB, padx=12, pady=6).pack(side="left")

        self._badge = tk.Label(form, text="", bg=C2, fg=T3, font=FC)
        self._badge.pack(anchor="w", pady=(10, 0))

        self._popola()

    def _popola(self):
        for i in self._tree.get_children():
            self._tree.delete(i)
        for n, u in enumerate(self._users):
            self._tree.insert("", "end", iid=str(u["id"]),
                              values=(u["id"], u["label"]),
                              tags=("e" if n % 2 == 0 else "o",))
        c = len(self._users)
        self._badge.config(text=f"{c} utente{'i' if c != 1 else ''} in lista")

    def _aggiungi(self):
        raw = self._id_var.get().strip()
        lbl = self._lbl_var.get().strip()
        if not raw:
            messagebox.showerror("Errore", "Inserisci un ID Telegram.")
            return
        try:
            uid = int(raw)
        except ValueError:
            messagebox.showerror("Errore", "L'ID deve essere un numero intero.")
            return
        if any(u["id"] == uid for u in self._users):
            messagebox.showwarning("Duplicato", f"L'ID {uid} è già presente.")
            return
        self._users.append({"id": uid, "label": lbl or str(uid)})
        salva_utenti(self._users)
        self._id_var.set("")
        self._lbl_var.set("")
        self._popola()
        self._on_change()

    def _rimuovi(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Nessuna selezione", "Seleziona un utente dalla lista.")
            return
        uid  = int(sel[0])
        nome = next((u["label"] for u in self._users if u["id"] == uid), str(uid))
        if not messagebox.askyesno("Conferma rimozione", f"Rimuovere «{nome}» (ID {uid})?"):
            return
        self._users[:] = [u for u in self._users if u["id"] != uid]
        salva_utenti(self._users)
        self._popola()
        self._on_change()

    def _importa(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Tutti", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            n = 0
            for e in data:
                uid = int(e["id"])
                if not any(u["id"] == uid for u in self._users):
                    self._users.append({"id": uid, "label": str(e.get("label", uid))})
                    n += 1
            salva_utenti(self._users)
            self._popola()
            self._on_change()
            messagebox.showinfo("Importazione", f"{n} nuovi utenti aggiunti.")
        except Exception as ex:
            messagebox.showerror("Errore importazione", str(ex))

    def refresh(self):
        self._popola()


class ImpostazioniTab:
    def __init__(self, parent, access_var, on_access_change, log_fn, token_var):
        self._access_var       = access_var
        self._on_access_change = on_access_change
        self._log              = log_fn
        self._token_var        = token_var
        self._build(parent)

    def _build(self, parent):
        P = 18

        tk.Frame(parent, bg=C2, height=P).pack(fill="x")

        tok_card = tk.Frame(parent, bg=C3, padx=16, pady=16)
        tok_card.pack(fill="x", padx=P, pady=(0, 10))

        tk.Label(tok_card, text="Token Bot Telegram", font=FB, bg=C3, fg=T1).pack(anchor="w")
        hdiv(tok_card, pady=(8, 12))

        te = tk.Frame(tok_card, bg=C3)
        te.pack(fill="x")
        self._tok_entry = sleek_entry(te, textvariable=self._token_var, width=46, show="•")
        self._tok_entry.pack(side="left", padx=(0, 10), ipady=4)

        self._show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            te, text="Mostra", variable=self._show_var,
            command=self._toggle_show,
            bg=C3, fg=T3, selectcolor=C4,
            activebackground=C3, activeforeground=T1,
            font=FC, cursor="hand2"
        ).pack(side="left", padx=(0, 8))

        glow_button(te, "Salva", self._salva_token,
                    base=BLUE, font=FC, padx=10, pady=5).pack(side="left")

        self._tok_status = tk.Label(tok_card, text="", bg=C3, font=FC)
        self._tok_status.pack(anchor="w", pady=(8, 0))
        self._aggiorna_tok_status()

        acc_card = tk.Frame(parent, bg=C3, padx=16, pady=16)
        acc_card.pack(fill="x", padx=P, pady=(0, 10))

        tk.Label(acc_card, text="Controllo accesso", font=FB, bg=C3, fg=T1).pack(anchor="w")
        hdiv(acc_card, pady=(8, 12))

        for val, lbl, clr in [("authorized", "Solo utenti autorizzati", GREEN),
                               ("all", "Tutti gli utenti (pubblico)", AMBER)]:
            tk.Radiobutton(
                acc_card, text=lbl, variable=self._access_var, value=val,
                command=self._on_access_change,
                bg=C3, fg=T2, selectcolor=C4,
                activebackground=C3, activeforeground=clr,
                font=FL, cursor="hand2"
            ).pack(anchor="w", pady=3)

        self._acc_badge = tk.Label(acc_card, text="", bg=C3, font=FC)
        self._acc_badge.pack(anchor="w", pady=(10, 0))
        self._aggiorna_acc_badge()

        info_card = tk.Frame(parent, bg=C3, padx=16, pady=16)
        info_card.pack(fill="x", padx=P, pady=(0, 10))

        tk.Label(info_card, text="File di configurazione", font=FB, bg=C3, fg=T1).pack(anchor="w")
        hdiv(info_card, pady=(8, 12))

        for lbl, val in [("Token", CONFIG_FILE), ("Utenti", USERS_FILE), ("Accessi", ACCESSI_FILE)]:
            r = tk.Frame(info_card, bg=C3)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=lbl, bg=C3, fg=T3, font=FC, width=10, anchor="w").pack(side="left")
            tk.Label(r, text=val, bg=C3, fg=T2, font=FMC).pack(side="left")

    def _toggle_show(self):
        self._tok_entry.config(show="" if self._show_var.get() else "•")

    def _salva_token(self):
        tok = self._token_var.get().strip()
        if not tok:
            messagebox.showerror("Errore", "Il token non può essere vuoto.")
            return
        path = _fp(CONFIG_FILE)
        if os.path.isfile(path):
            import stat
            try:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
        salva_config(tok)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f).get("token", "")
                ok = saved.strip() == tok
            except Exception:
                ok = False
        else:
            ok = False
        if ok:
            self._aggiorna_tok_status()
            self._log("Token salvato in config.json.", "OK")
        else:
            self._log("Salvataggio fallito — permission denied su config.json.", "ERROR")
            messagebox.showerror(
                "Permesso negato",
                "Impossibile scrivere config.json.\n\n"
                "Soluzioni:\n"
                "1. Chiudi qualsiasi editor che ha il file aperto\n"
                "2. Tasto destro su config.json → Proprietà → togli 'Sola lettura'\n"
                "3. Oppure esegui VS Code come Amministratore"
            )

    def _aggiorna_tok_status(self):
        tok = self._token_var.get().strip()
        if tok and tok != "INSERISCI_QUI_IL_TUO_TOKEN":
            self._tok_status.config(text="✓ Token configurato", fg=GREEN)
        else:
            self._tok_status.config(text="⚠  Nessun token valido impostato", fg=AMBER)

    def _aggiorna_acc_badge(self):
        if self._access_var.get() == "authorized":
            self._acc_badge.config(text="🔒  Accesso ristretto", fg=GREEN)
        else:
            self._acc_badge.config(text="⚠   Aperto al pubblico", fg=AMBER)

    def on_access_change(self):
        self._aggiorna_acc_badge()


class StatusBar:
    def __init__(self, parent, on_start, on_stop):
        bar = tk.Frame(parent, bg=C1, pady=0)
        bar.pack(fill="x")

        left = tk.Frame(bar, bg=C1)
        left.pack(side="left", padx=16, pady=12)

        self._pulse = tk.Label(left, text="●", bg=C1, fg=RED, font=(FN, 12))
        self._pulse.pack(side="left")

        info = tk.Frame(left, bg=C1)
        info.pack(side="left", padx=(8, 0))
        tk.Label(info, text="EL Telegram Bot Manager", font=FT, bg=C1, fg=T1).pack(anchor="w")
        self._sub = tk.Label(info, text="Offline — premi Avvia per connettere", font=FC, bg=C1, fg=T3)
        self._sub.pack(anchor="w")

        right = tk.Frame(bar, bg=C1)
        right.pack(side="right", padx=16)

        self._btn_stop = glow_button(right, "  Ferma  ", on_stop,
                                      base=RED, font=FB, padx=14, pady=7)
        self._btn_stop.pack(side="right", padx=(8, 0))
        self._btn_stop.config(state="disabled")

        self._btn_start = glow_button(right, "  Avvia  ", on_start,
                                       base=GREEN, fg="#000", font=FB, padx=14, pady=7)
        self._btn_start.pack(side="right")

    def set_running(self, running: bool):
        if running:
            self._pulse.config(fg=GREEN)
            self._sub.config(text="Online — in ascolto", fg=GREEN)
            self._btn_start.config(state="disabled")
            self._btn_stop.config(state="normal")
        else:
            self._pulse.config(fg=RED)
            self._sub.config(text="Offline — premi Avvia per connettere", fg=T3)
            self._btn_start.config(state="normal")
            self._btn_stop.config(state="disabled")


class LogBar:
    MAX = 400
    CLR = {"DEBUG": T3, "INFO": T2, "OK": GREEN, "WARNING": AMBER, "ERROR": RED}

    def __init__(self, parent):
        outer = tk.Frame(parent, bg=C1)
        outer.pack(fill="x", side="bottom")

        hdiv(outer, pady=(0, 0))

        bar = tk.Frame(outer, bg=C1, padx=14, pady=6)
        bar.pack(fill="x")

        tk.Label(bar, text="LOG", font=(FN, 8, "bold"), bg=C1, fg=T3).pack(side="left")

        ghost_button(bar, "Pulisci", self._pulisci, font=FC, padx=8, pady=2).pack(side="right")
        ghost_button(bar, "Esporta", self._esporta, font=FC, padx=8, pady=2).pack(side="right", padx=(0, 6))

        self._box = scrolledtext.ScrolledText(
            outer, height=5, font=FMC,
            bg="#090909", fg=T1,
            insertbackground=BLUE,
            relief="flat", bd=0, state="disabled", wrap="word"
        )
        self._box.pack(fill="both", expand=True)

        for l, c in self.CLR.items():
            self._box.tag_config(l, foreground=c)
        self._box.tag_config("TS", foreground=T3)

        self._storico: list[dict] = []

    def scrivi(self, msg: str, livello: str = "INFO"):
        l = livello.upper()
        if l not in self.CLR:
            l = "INFO"
        ts = datetime.now().strftime("%H:%M:%S")
        self._storico.append({"ts": ts, "livello": l, "msg": msg})
        self._box.configure(state="normal")
        righe = int(self._box.index("end-1c").split(".")[0])
        if righe > self.MAX:
            self._box.delete("1.0", f"{righe - self.MAX}.0")
        self._box.insert("end", f"{ts}  ", "TS")
        self._box.insert("end", f"{l:<7}  ", l)
        self._box.insert("end", msg + "\n")
        self._box.see("end")
        self._box.configure(state="disabled")

    def _pulisci(self):
        self._box.configure(state="normal")
        self._box.delete("1.0", "end")
        self._box.configure(state="disabled")

    def _esporta(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Testo", "*.txt"), ("Tutti", "*.*")],
            initialfile=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for v in self._storico:
                    f.write(f"[{v['ts']}] [{v['livello']:<7}] {v['msg']}\n")
            self.scrivi(f"Esportato: {path}", "OK")
        except Exception as e:
            self.scrivi(f"Errore export: {e}", "ERROR")


class BotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EL Telegram Bot Manager")
        self.geometry("640x740")
        self.minsize(520, 460)
        self.configure(bg=C1)
        self.resizable(True, True)

        self._bot_thread = None
        self._loop       = None
        self._app        = None
        self._running    = False

        authorized_users.extend(carica_utenti())
        self._token_var = tk.StringVar(value=carica_config())

        self._setup_logging()
        self._build_ui()
        self.log(f"Pronto. {len(authorized_users)} utenti caricati.", "OK")
        tok = self._token_var.get().strip()
        if not tok or tok == "INSERISCI_QUI_IL_TUO_TOKEN":
            self.log("Token non configurato — vai in Impostazioni.", "WARNING")

    def _setup_logging(self):
        h = _GUILogHandler(self)
        h.setLevel(logging.INFO)
        h.setFormatter(logging.Formatter("%(message)s"))
        rl = logging.getLogger()
        rl.setLevel(logging.INFO)
        rl.addHandler(h)
        for n in ("httpx", "httpcore", "telegram"):
            logging.getLogger(n).setLevel(logging.WARNING)

    def log(self, msg: str, level: str = "INFO"):
        self._log_bar.scrivi(msg, level)

    def _build_ui(self):
        self._status_bar = StatusBar(self, self._avvia, self._ferma)
        hdiv(self, pady=(0, 0))

        self._log_bar = LogBar(self)

        self._access_var = tk.StringVar(value="authorized")
        tab_ctrl = TabController(self, ["Bacheca", "Utenti", "Impostazioni"])

        self._bacheca_tab = BachecaTab(
            tab_ctrl.frame("Bacheca"),
            get_users_fn=lambda: authorized_users,
            on_invia=self._invia_bacheca
        )
        self._utenti_tab = UtentiTab(
            tab_ctrl.frame("Utenti"),
            users_ref=authorized_users,
            on_change=self._on_users_changed
        )
        self._impostazioni_tab = ImpostazioniTab(
            tab_ctrl.frame("Impostazioni"),
            access_var=self._access_var,
            on_access_change=self._aggiorna_accesso,
            log_fn=self.log,
            token_var=self._token_var
        )

    def _on_users_changed(self):
        self._bacheca_tab.refresh_users()
        self.log(f"Utenti aggiornati: {len(authorized_users)} in lista.", "OK")

    def _aggiorna_accesso(self):
        global access_mode
        access_mode = self._access_var.get()
        self._impostazioni_tab.on_access_change()
        if access_mode == "all":
            self.log("Accesso aperto a tutti.", "WARNING")
        else:
            self.log("Accesso ristretto agli autorizzati.", "OK")

    def _invia_bacheca(self, destinatari, testo, allegato, ora_obj):
        if not self._running or self._loop is None or self._app is None:
            messagebox.showwarning("Bot offline", "Avvia il bot prima di inviare messaggi.")
            return
        self.log(f"Invio a: {', '.join(str(d) for d in destinatari)}", "INFO")
        asyncio.run_coroutine_threadsafe(
            self._async_invia(destinatari, testo, allegato, ora_obj), self._loop)

    async def _async_invia(self, destinatari, testo, allegato, ora_obj):
        if ora_obj:
            now   = datetime.now()
            tgt   = datetime.combine(now.date(), ora_obj)
            delta = (tgt - now).total_seconds()
            if delta < 0:
                delta = 0
            if delta > 0:
                self.after(0, lambda d=delta: self.log(f"Attesa {int(d)}s…", "INFO"))
                await asyncio.sleep(delta)

        for cid in destinatari:
            try:
                if allegato:
                    ext = os.path.splitext(allegato)[1].lower()
                    with open(allegato, "rb") as f:
                        if ext == ".gif":
                            await self._app.bot.send_animation(chat_id=cid, animation=f, caption=testo or None)
                        elif ext in (".jpg", ".jpeg", ".png", ".webp"):
                            await self._app.bot.send_photo(chat_id=cid, photo=f, caption=testo or None)
                        else:
                            await self._app.bot.send_document(chat_id=cid, document=f, caption=testo or None)
                else:
                    await self._app.bot.send_message(chat_id=cid, text=testo)
                self.after(0, lambda c=cid: self.log(
                    f"Inviato a {c} — {datetime.now().strftime('%H:%M:%S')}", "OK"))
            except Exception as e:
                self.after(0, lambda c=cid, err=e: self.log(f"Errore invio a {c}: {err}", "ERROR"))

    def _avvia(self):
        if self._running:
            return
        tok = self._token_var.get().strip()
        if not tok or tok == "INSERISCI_QUI_IL_TUO_TOKEN":
            messagebox.showerror("Token mancante",
                                 "Configura il token in Impostazioni prima di avviare.")
            return
        self.log("Avvio bot…", "INFO")
        self._bot_thread = threading.Thread(target=self._run_bot, daemon=True)
        self._bot_thread.start()

    def _run_bot(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_run())
        except Exception as e:
            self.after(0, lambda err=e: self.log(f"Errore bot: {err}", "ERROR"))
        finally:
            self._running = False
            self.after(0, lambda: self._status_bar.set_running(False))
            self.after(0, lambda: self.log("Bot arrestato.", "WARNING"))

    async def _async_run(self):
        tok = self._token_var.get().strip()
        self._app = ApplicationBuilder().token(tok).build()
        self._app.add_handler(CommandHandler("start", start))
        self._app.add_handler(CommandHandler("el", cmd_top10))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, rispondi))
        await self._app.initialize()
        await self._app.start()
        self._running = True
        self.after(0, lambda: self._status_bar.set_running(True))
        self.after(0, lambda: self.log("Bot online.", "OK"))
        await self._app.updater.start_polling(drop_pending_updates=True)
        while self._running:
            await asyncio.sleep(0.5)
        await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()

    def _ferma(self):
        if not self._running:
            return
        self.log("Arresto bot…", "WARNING")
        self._running = False

    def destroy(self):
        if self._running:
            self._ferma()
        super().destroy()


class _GUILogHandler(logging.Handler):
    def __init__(self, gui: BotGUI):
        super().__init__()
        self.gui = gui

    def emit(self, record):
        msg = self.format(record)
        lvl = record.levelname
        try:
            self.gui.after(0, lambda m=msg, l=lvl: self.gui.log(m, l))
        except Exception:
            pass


if __name__ == "__main__":
    app = BotGUI()
    app.mainloop()
