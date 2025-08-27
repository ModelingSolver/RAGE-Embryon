import socket
import json
import time
import shutil
import os
import subprocess
import threading

HEARTBEAT_TIMEOUT = 30  # délai avant considération boîte morte
BOX5_ALERT_TIMEOUT = 10  # délai avant alerte box5 ne reçoit plus heartbeat
LISTEN_IP = "127.0.0.5"
LISTEN_PORT = 9999

# Dernier heartbeat reçu par le serveur de chaque boîte
last_heartbeats = {
    "BOX1": None,
    "BOX2": None,
    "BOX2clone": None,
    "BOX3": None,
    "BOX4": None,
}

# Pour éviter de cloner plusieurs fois la même boîte
already_cloned = set()

# Dernier heartbeat reçu PAR BOX5 de chaque boîte surveillée
last_hb_received_by_box5 = {
    "BOX1": None,
    "BOX2": None,
    "BOX3": None,
    "BOX4": None,
}

boxes_surveillees_par_box5 = ["BOX1", "BOX2", "BOX3", "BOX4"]

# Dictionnaire pour garder trace des processus de clones lancés
clone_processes = {}


def clone_boite(boite_name):
    source = os.path.abspath(boite_name)
    clones_dir = os.path.abspath("clones_surveillance")
    clone_name = f"{boite_name}_clone"
    dest = os.path.join(clones_dir, clone_name)

    if not os.path.exists(source):
        print(f"[CLONE] Source introuvable : {source}")
        return

    if not os.path.exists(clones_dir):
        os.makedirs(clones_dir)

    if os.path.exists(dest):
        print(f"[CLONE] Suppression ancien clone : {dest}")
        # Tenter de fermer le process avant suppression
        proc = clone_processes.get(clone_name)
        if proc:
            print(f"[CLONE] Fermeture du processus du clone {clone_name} avant suppression")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"[CLONE] Processus {clone_name} ne répond pas, kill forcé")
                proc.kill()
                proc.wait()
            del clone_processes[clone_name]

        try:
            shutil.rmtree(dest)
        except Exception as e:
            print(f"[CLONE] Erreur suppression ancien clone : {e}")

    try:
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns("clones*"))
        print(f"[CLONE] ✅ {boite_name} clonée dans {dest}")

        vie_path = os.path.join(dest, "vie.py")
        if os.path.exists(vie_path):
            proc = subprocess.Popen(["python", vie_path, "--nom", clone_name], cwd=dest)
            clone_processes[clone_name] = proc
            print(f"[CLONE] ▶️ Lancement vie.py du clone de {boite_name}")
        else:
            print(f"[CLONE] ⚠️ vie.py manquant dans {dest}")
    except Exception as e:
        print(f"[CLONE] ❌ Erreur lors du clonage de {boite_name} : {e}")


def supprimer_clone(boite_name):
    clones_dir = os.path.abspath("clones_surveillance")
    clone_name = f"{boite_name}_clone"
    dest = os.path.join(clones_dir, clone_name)

    # Tuer le process si existant
    proc = clone_processes.get(clone_name)
    if proc:
        print(f"[SUPPRESSION] Fermeture du processus du clone {clone_name}")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print(f"[SUPPRESSION] Processus {clone_name} ne répond pas, kill forcé")
            proc.kill()
            proc.wait()
        del clone_processes[clone_name]

    if os.path.exists(dest):
        print(f"[SUPPRESSION] Suppression du clone : {dest}")
        try:
            shutil.rmtree(dest)
        except Exception as e:
            print(f"[SUPPRESSION] Erreur lors de la suppression du clone {dest} : {e}")
    else:
        print(f"[SUPPRESSION] Aucun clone trouvé à supprimer pour {boite_name}")


def check_boites_alive():
    start_time = time.time()
    while True:
        now = time.time()
        for boite, last_time in last_heartbeats.items():
            if last_time is None:
                if (now - start_time) < HEARTBEAT_TIMEOUT:
                    continue
                is_dead = True
            else:
                is_dead = (now - last_time) > HEARTBEAT_TIMEOUT

            if is_dead:
                if boite not in already_cloned:
                    print(f"[CHECK] ⚠️ {boite} ne répond plus (dernier heartbeat à {last_time}), clonage déclenché")
                    clone_boite(boite)
                    already_cloned.add(boite)
            else:
                if boite in already_cloned:
                    print(f"[CHECK] ✅ {boite} est revenu en vie, suppression du clone")
                    supprimer_clone(boite)
                    already_cloned.remove(boite)
        time.sleep(5)


def listen_heartbeats():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    sock.settimeout(5)

    print(f"[CHECKVIE] 🛰️ Écoute des heartbeats sur {LISTEN_IP}:{LISTEN_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = json.loads(data.decode())
            boite = message.get("boite")
            if boite in last_heartbeats:
                last_heartbeats[boite] = time.time()
                print(f"[HEARTBEAT] ❤️ Reçu de {boite}")

                # Mise à jour du dernier heartbeat reçu PAR BOX5
                if boite in boxes_surveillees_par_box5:
                    last_hb_received_by_box5[boite] = time.time()
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[ERROR] Erreur réception heartbeat : {e}")


def check_box5_reception():
    while True:
        now = time.time()
        for boite in boxes_surveillees_par_box5:
            # Ne pas alerter si boîte clonée
            if boite in already_cloned:
                continue
            last_time = last_hb_received_by_box5.get(boite)
            if last_time is None:
                continue
            elapsed = now - last_time
            if elapsed > BOX5_ALERT_TIMEOUT:
                print(f"[ALERTE BOX5] ⚠️ box5 ne reçoit plus de heartbeat de {boite} depuis {int(elapsed)}s")
        time.sleep(5)


if __name__ == "__main__":
    print("[CHECKVIE] ⏳ Démarrage dans 10 secondes pour laisser les boîtes se lancer...")
    time.sleep(10)

    threading.Thread(target=check_boites_alive, daemon=True).start()
    threading.Thread(target=check_box5_reception, daemon=True).start()
    listen_heartbeats()
