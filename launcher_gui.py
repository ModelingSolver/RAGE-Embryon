import tkinter as tk
from tkinter import messagebox
import subprocess
import psutil
import threading
import time
import os
import sys

processes = {}
clone_processes = {}  # pid -> psutil.Process clone

SCRIPTS = {
    "BOX1": "BOX1/vie.py",
    "BOX2 (avec clone)": "BOX2/survie.py",
    "BOX3": "BOX3/vie.py",
    "BOX4": "BOX4/vie.py",
    "BOX5 (vie)": "BOX5/vie.py",
    "CHECKVIE BOX5": "BOX5/checkvie.py",
    "CHECK5 (par BOX4)": "BOX4/checkvie.py",
}

def lancer_script(nom):
    if nom in processes:
        messagebox.showinfo("Info", f"{nom} déjà lancé.")
        return
    script_path = SCRIPTS.get(nom)
    if not script_path:
        messagebox.showwarning("Attention", f"{nom} est géré automatiquement et ne peut être lancé manuellement.")
        return
    try:
        full_script_path = os.path.abspath(script_path)
        proc = subprocess.Popen([sys.executable, full_script_path])
        processes[nom] = proc
        status_labels[nom].config(text=f"✅ Lancé (PID {proc.pid})", fg="green")
    except Exception as e:
        messagebox.showerror("Erreur", f"Échec lancement {nom} : {e}")

def arreter_script(nom):
    proc = processes.get(nom)
    if proc:
        try:
            p = psutil.Process(proc.pid)
            for child in p.children(recursive=True):
                child.kill()
            p.kill()
        except Exception as e:
            print(f"[STOP] Erreur arrêt {nom} : {e}")
        else:
            status_labels[nom].config(text="⛔ Arrêté", fg="red")
        del processes[nom]

def arreter_clone(pid):
    try:
        p = psutil.Process(pid)
        for child in p.children(recursive=True):
            child.kill()
        p.kill()
    except Exception as e:
        print(f"[STOP] Erreur arrêt clone PID {pid} : {e}")

def panic():
    for nom, proc in list(processes.items()):
        try:
            p = psutil.Process(proc.pid)
            for child in p.children(recursive=True):
                child.kill()
            p.kill()
        except Exception as e:
            print(f"[PANIC] Erreur arrêt {nom} : {e}")
        else:
            status_labels[nom].config(text="🛑 Tué", fg="red")
        del processes[nom]

    for pid in list(clone_processes.keys()):
        arreter_clone(pid)
        root.after(0, lambda p=pid: supprimer_clone_gui(p))

    messagebox.showwarning("PANIC", "Tous les scripts et clones ont été arrêtés !")

# --- GUI Setup ---
root = tk.Tk()
root.title("🎛️ R.A.G.E. Control Panel")

status_labels = {}
clone_labels = {}

# Affichage scripts
for idx, nom in enumerate(SCRIPTS.keys()):
    tk.Label(root, text=nom).grid(row=idx, column=0, padx=5, pady=3, sticky="w")
    tk.Button(root, text="Lancer", command=lambda n=nom: lancer_script(n)).grid(row=idx, column=1)
    tk.Button(root, text="Stop", command=lambda n=nom: arreter_script(n)).grid(row=idx, column=2)
    status = tk.Label(root, text="⏸️ Inactif", fg="gray")
    status.grid(row=idx, column=3)
    status_labels[nom] = status

# Section clones
clone_section_row = len(SCRIPTS) + 1
tk.Label(root, text="Clones actifs :").grid(row=clone_section_row, column=0, sticky="w", pady=10)

clone_frame = tk.Frame(root)
clone_frame.grid(row=clone_section_row+1, column=0, columnspan=4, sticky="we")

def extraire_nom_clone(cmdline):
    # Essaie d'extraire un --nom passé en argument dans cmdline
    for i, arg in enumerate(cmdline):
        if arg == "--nom" and i+1 < len(cmdline):
            return cmdline[i+1]
    return "Clone inconnu"

def ajouter_clone_gui(pid, cmdline):
    if pid in clone_labels:
        return
    row = len(clone_labels)

    clone_name = extraire_nom_clone(cmdline)

    frame = tk.Frame(clone_frame, relief="groove", bd=1, padx=5, pady=2)
    frame.grid(row=row, column=0, sticky="we", pady=2, padx=2)

    label_name = tk.Label(frame, text=clone_name, font=("TkDefaultFont", 10, "bold"))
    label_name.pack(side="left", padx=(0, 10))

    label_pid = tk.Label(frame, text=f"PID: {pid}", fg="blue")
    label_pid.pack(side="left")

    btn = tk.Button(frame, text="Stop Clone", command=lambda p=pid: stop_clone_gui(p))
    btn.pack(side="right")

    clone_labels[pid] = (frame, label_name, label_pid, btn)

def supprimer_clone_gui(pid):
    if pid in clone_labels:
        frame, *_ = clone_labels[pid]
        frame.destroy()
        del clone_labels[pid]

def stop_clone_gui(pid):
    arreter_clone(pid)
    supprimer_clone_gui(pid)
    if pid in clone_processes:
        del clone_processes[pid]

def maj_clones():
    # Nettoyage clones terminés
    for pid in list(clone_processes.keys()):
        if not psutil.pid_exists(pid):
            supprimer_clone_gui(pid)
            del clone_processes[pid]

    # Recherche enfants (clones) des processus lancés
    for nom, proc in processes.items():
        try:
            p = psutil.Process(proc.pid)
            enfants = p.children(recursive=True)
            for child in enfants:
                if child.pid not in clone_processes:
                    clone_processes[child.pid] = child
                    cmdline = child.cmdline() or ["?"]
                    root.after(0, lambda pid=child.pid, cmd=cmdline: ajouter_clone_gui(pid, cmd))
        except Exception as e:
            print(f"[MONITOR] Erreur surveillance clones {nom}: {e}")

    root.after(3000, maj_clones)  # relance tous les 3s

root.after(3000, maj_clones)

# PANIC bouton
tk.Button(root, text="💥 PANIC!", bg="red", fg="white", command=panic).grid(row=clone_section_row+2, column=0, columnspan=4, pady=10)

# Jauges CPU & RAM
cpu_label = tk.Label(root, text="CPU Usage:")
cpu_label.grid(row=clone_section_row+3, column=0, sticky="w", padx=5)

cpu_canvas = tk.Canvas(root, width=200, height=20, bg="white")
cpu_canvas.grid(row=clone_section_row+3, column=1, columnspan=3, sticky="w")

ram_label = tk.Label(root, text="RAM Usage:")
ram_label.grid(row=clone_section_row+4, column=0, sticky="w", padx=5)

ram_canvas = tk.Canvas(root, width=200, height=20, bg="white")
ram_canvas.grid(row=clone_section_row+4, column=1, columnspan=3, sticky="w")

def update_jauges():
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent

        cpu_canvas.delete("all")
        cpu_canvas.create_rectangle(0, 0, 2*cpu_percent, 20, fill="green")
        cpu_canvas.create_text(100, 10, text=f"{cpu_percent} %", fill="black")

        ram_canvas.delete("all")
        ram_canvas.create_rectangle(0, 0, 2*ram_percent, 20, fill="blue")
        ram_canvas.create_text(100, 10, text=f"{ram_percent} %", fill="black")

        time.sleep(1)

threading.Thread(target=update_jauges, daemon=True).start()

root.mainloop()
