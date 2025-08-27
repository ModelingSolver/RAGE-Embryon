import shutil
import os
import subprocess
import time

SOURCE = os.path.abspath(os.path.dirname(__file__))  # chemin absolu vers BOX2
DEST_BASE = os.path.join(SOURCE, "clones")           # clones dans BOX2
CLONE_NAME = "BOX2clone"
CLONE_PATH = os.path.join(DEST_BASE, CLONE_NAME)
MARKER_FILE = os.path.join(DEST_BASE, ".cloned")


def ignore_clones(dir, files):
    # Ignore le dossier 'clones' dans la copie
    if os.path.abspath(dir) == SOURCE:
        return ["clones"]
    return []


def auto_clone_once():
    if os.path.exists(MARKER_FILE):
        print("[CLONE] Clonage déjà effectué. Rien à faire.")
        return None

    if not os.path.exists(DEST_BASE):
        os.makedirs(DEST_BASE)

    # Supprimer ancien clone s'il existe
    if os.path.exists(CLONE_PATH):
        print(f"[CLONE] Suppression de l'ancien clone {CLONE_PATH}")
        shutil.rmtree(CLONE_PATH)

    try:
        shutil.copytree(SOURCE, CLONE_PATH, ignore=ignore_clones)
        with open(MARKER_FILE, "w") as f:
            f.write("Cloné une fois")
        print(f"[CLONE] BOX2 clonée dans {CLONE_PATH}")
        return CLONE_PATH
    except Exception as e:
        print(f"[CLONE] Erreur de clonage : {e}")
        return None


def launch_heartbeat(script_path, nom_boite):
    print(f"[HEARTBEAT] Lancement heartbeat pour {nom_boite}")
    print(f"[DEBUG] Script lancé : {script_path}")
    print(f"[DEBUG] cwd utilisé   : {os.path.dirname(script_path)}")

    subprocess.Popen(
        ["python", script_path, "--nom", nom_boite, "--interval", "5"],
        cwd=os.path.dirname(script_path)
    )


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.dirname(__file__))

    clone_path = auto_clone_once()
    if not clone_path:  # clone déjà présent ou clonage non fait cette fois
        clone_path = os.path.join(DEST_BASE, CLONE_NAME)

    current_vie_script = os.path.join(base_dir, "vie.py")
    launch_heartbeat(current_vie_script, "BOX2")

    if os.path.exists(clone_path):  # on vérifie que le clone existe
        clone_vie_script = os.path.join(clone_path, "vie.py")
        launch_heartbeat(clone_vie_script, "BOX2clone")
    else:
        print("[CLONE] Clone non trouvé, clone non lancé.")

    while True:
        time.sleep(1)
