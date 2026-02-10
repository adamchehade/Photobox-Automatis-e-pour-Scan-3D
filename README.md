
# 📸 Photobox Automatisée pour Scan 3D

Ce projet est une solution complète de numérisation 3D automatisée. Il combine une structure matérielle pilotée par **ESP32** (table tournante et slider) avec une interface de contrôle **Streamlit** et une reconstruction par IA via **DUSt3R**.



---

## 🚀 Fonctionnalités

* **Contrôle Matériel Synchronisé** : Pilotage d'un moteur pas-à-pas pour la rotation de l'objet et d'un slider via des requêtes HTTP envoyées à un ESP32.
* **Capture Automatisée** : Gestion intelligente de la caméra (OpenCV) avec temps de stabilisation pour des photos nettes à chaque angle.
* **Reconstruction 3D via IA** : Intégration de **DUSt3R** pour transformer les séquences d'images en nuages de points sans calibration complexe.
* **AI Enhancer** : Pipeline intégré pour améliorer la qualité des images via un serveur Flask distant avant la reconstruction.
* **Visualisation 3D** : Afficheur interactif intégré (Plotly) pour inspecter les nuages de points et export au format `.PLY`.

---

## 🛠️ Configuration Matérielle

L'application est configurée pour communiquer avec un système basé sur :
* **ESP32** : IP par défaut `192.168.221.219` gérant les moteurs.
* **Moteur** : 2048 pas par révolution avec un rapport d'engrenage de 3.0.
* **Caméra** : Caméra USB (Index 1 par défaut) supportant le mode Full HD (1920x1080).

---

## 💻 Installation

1. **Clonage du dépôt** :
   
   git clone [https://github.com/adamchehade/Photobox-Automatis-e-pour-Scan-3D.git](https://github.com/adamchehade/Photobox-Automatis-e-pour-Scan-3D.git)
   cd Photobox-Automatis-e-pour-Scan-3D



2. **Installation des dépendances** :

pip install torch torchvision numpy streamlit opencv-python requests plotly trimesh Pillow




3. **Installation de DUSt3R** :
Le code s'attend à trouver le module `dust3r` dans le répertoire courant. Clonez le dépôt officiel et téléchargez le modèle `ViTLarge_BaseDecoder_512_dpt`.



## ⚙️ Utilisation

Lancez l'interface de contrôle avec la commande suivante :


streamlit run full-app.py



### Onglets disponibles :

1. **✨ AI Enhancer** : Prenez une photo en direct et envoyez-la à un serveur Flask pour traitement (upscaling/denoising).
2. **📸 Hardware Scanner** : Configurez le nombre de photos par tour et lancez le cycle automatique. L'interface affiche la progression et les images capturées en temps réel.
3. **🧊 3D Reconstruction** : Traitez les images du dernier scan ou uploadez vos propres fichiers pour générer un nuage de points exportable.

---

## ⚠️ Notes Techniques

* **Libération de la Caméra** : Un système de "Toggle" est présent dans l'interface pour s'assurer que l'onglet IA ne verrouille pas la caméra pendant que le scanner matériel essaie de l'utiliser.
* **Traitement 3D** : La reconstruction utilise `torch` et préfère une exécution sur GPU (CUDA) pour des performances optimales.
* **Sortie** : Les fichiers sont sauvegardés dans le dossier `scans_output/` avec un horodatage unique.



## 📦 Structure du Projet

* `HardwareScanner` : Gère le threading, la rotation moteur et la capture OpenCV.
* `visualize_point_cloud` : Utilise Plotly pour le rendu 3D interactif dans le navigateur.
* `load_dust3r_model` : Charge l'architecture de modèle `AsymmetricCroCo3DStereo`.





Souhaites-tu que je génère également le code Arduino/C++ pour l'ESP32 afin qu'il réponde correctement aux requêtes du script Python ?

