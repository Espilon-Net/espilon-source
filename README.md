# Espilon

**Framework d'agents embarqués ESP32 pour la recherche en sécurité et l'IoT**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.3.2-green.svg)](https://github.com/espressif/esp-idf)
[![Platform](https://img.shields.io/badge/Platform-ESP32-red.svg)](https://www.espressif.com/en/products/socs/esp32)

> **⚠️ IMPORTANT** : Espilon est destiné à la recherche en sécurité, aux tests d'intrusion autorisés et à l'éducation. L'utilisation non autorisée est illégale. Obtenez toujours une autorisation écrite avant tout déploiement.

---

## Documentation Complète

**[Consultez la documentation complète ici](https://docs.espilon.net)**

La documentation MkDocs inclut :

- Guide d'installation pas à pas
- Configuration WiFi et GPRS
- Référence des modules et commandes
- Guide du flasher multi-device
- Spécification du protocole C2
- Exemples et cas d'usage

---

## Quick Start

### Prérequis

- ESP-IDF v5.3.2
- Python 3.8+
- ESP32 (tout modèle compatible)
- LilyGO T-Call pour le mode GPRS (optionnel)

### Installation Rapide

```bash
# 1. Installer ESP-IDF v5.3.2
mkdir -p ~/esp
cd ~/esp
git clone -b v5.3.2 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32
. ./export.sh

# 2. Cloner Espilon
cd ~
git clone https://github.com/yourusername/epsilon.git
cd epsilon/espilon_bot

# 3. Configurer
idf.py menuconfig

# 4. Compiler et flasher
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

**Configuration minimale** (menuconfig) :
```
Espilon Bot Configuration
  ├─ Device ID: "votre_id_unique"
  ├─ Network → WiFi
  │   ├─ SSID: "VotreWiFi"
  │   └─ Password: "VotreMotDePasse"
  └─ Server
      ├─ IP: "192.168.1.100"
      └─ Port: 2626
```

---

## Qu'est-ce qu'Espilon ?

Espilon transforme des microcontrôleurs ESP32 abordables (~5€) en agents networked puissants pour :

- **Recherche en sécurité** : Tests WiFi, reconnaissance réseau, IoT pentesting
- **Éducation** : Apprentissage de l'embarqué, protocoles réseau, FreeRTOS
- **Prototypage IoT** : Communication distribuée, monitoring, capteurs

### Modes de Connectivité

| Mode | Hardware | Portée | Use Case |
|------|----------|--------|----------|
| **WiFi** | ESP32 standard | 50-100m | Labs, bâtiments |
| **GPRS** | LilyGO T-Call | National (2G) | Mobile, remote |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ESP32 Agent                       │
│  ┌───────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │  WiFi/    │→ │ ChaCha20 │→ │   C2 Protocol   │ │
│  │  GPRS     │← │  Crypto  │← │  (nanoPB/TCP)   │ │
│  └───────────┘  └──────────┘  └─────────────────┘ │
│         ↓              ↓                 ↓          │
│  ┌───────────────────────────────────────────────┐ │
│  │         Module System (FreeRTOS)              │ │
│  │  [Network] [FakeAP] [Recon] [Custom...]       │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                        ↕ Encrypted TCP
              ┌─────────────────────┐
              │   C2 Server (C3PO)  │
              │  - Device Registry  │
              │  - Group Management │
              │  - CLI Interface    │
              └─────────────────────┘
```

### Composants Clés

- **Core** : Connexion réseau, crypto ChaCha20, protocole nanoPB
- **Modules** : Système extensible (Network, FakeAP, Recon, etc.)
- **C2 (C3PO)** : Serveur Python asyncio pour contrôle multi-agents
- **Flasher** : Outil de flash multi-device automatisé

---

## Modules Disponibles

> **Note importante** : Les modules sont **mutuellement exclusifs**. Vous devez choisir **un seul module** lors de la configuration via menuconfig.

### System Module (Built-in, toujours actif)

Commandes système de base :

- `system_reboot` : Redémarrage de l'ESP32
- `system_mem` : Affichage de l'utilisation mémoire (heap free, heap min, internal free)
- `system_uptime` : Temps de fonctionnement depuis le boot

### Network Module

Module pour reconnaissance et tests réseau :

- `ping <host> [args...]` : Test de connectivité ICMP
- `arp_scan` : Découverte des hôtes sur le réseau local via ARP
- `proxy_start <ip> <port>` : Démarrer un proxy TCP
- `proxy_stop` : Arrêter le proxy en cours
- `dos_tcp <ip> <port> <count>` : Test de charge TCP (à usage autorisé uniquement)

### FakeAP Module

Module pour création de points d'accès WiFi simulés :

- `fakeap_start <ssid> [open|wpa2] [password]` : Démarrer un faux point d'accès
- `fakeap_stop` : Arrêter le faux AP
- `fakeap_status` : Afficher le statut (AP, portal, sniffer, clients)
- `fakeap_clients` : Lister les clients connectés
- `fakeap_portal_start` : Activer le portail captif
- `fakeap_portal_stop` : Désactiver le portail captif
- `fakeap_sniffer_on` : Activer la capture de trafic réseau
- `fakeap_sniffer_off` : Désactiver la capture

### Recon Module

Module de reconnaissance et collecte de données. Deux modes disponibles :

#### Mode Camera (ESP32-CAM)

- `cam_start <ip> <port>` : Démarrer le streaming vidéo UDP (~7 FPS, QQVGA)
- `cam_stop` : Arrêter le streaming

#### Mode BLE Trilateration

- `trilat start <mac> <url> <bearer>` : Démarrer la trilatération BLE avec POST HTTP
- `trilat stop` : Arrêter la trilatération

---

**Configuration** : `idf.py menuconfig` → Espilon Bot Configuration → Modules

Choisissez **un seul module** :

- `CONFIG_MODULE_NETWORK` : Active le Network Module
- `CONFIG_MODULE_FAKEAP` : Active le FakeAP Module
- `CONFIG_MODULE_RECON` : Active le Recon Module
  - Puis choisir : `Camera` ou `BLE Trilateration`

---

## Outils

### Multi-Device Flasher

Flasher automatisé pour configurer plusieurs ESP32 :

```bash
cd tools/flasher
python3 flash.py --config devices.json
```

**devices.json** :

```json
{
  "project": "/path/to/espilon_bot",
  "devices": [
    {
      "device_id": "esp001",
      "port": "/dev/ttyUSB0",
      "network_mode": "wifi",
      "wifi_ssid": "MyNetwork",
      "wifi_pass": "MyPassword",
      "srv_ip": "192.168.1.100"
    }
  ]
}
```

Voir [tools/flasher/README.md](tools/flasher/README.md) pour la documentation complète.

### C2 Server (C3PO)

Serveur de Command & Control :

```bash
cd tools/c2
pip3 install -r requirements.txt
python3 c3po.py --port 2626
```

**Commandes** :

- `list` : Lister les agents connectés
- `select <id>` : Sélectionner un agent
- `cmd <command>` : Exécuter une commande
- `group` : Gérer les groupes d'agents

---

## Sécurité

### Chiffrement

- **ChaCha20** pour les communications C2
- **Clés configurables** via menuconfig
- **Protocol Buffers (nanoPB)** pour la sérialisation

⚠️ **CHANGEZ LES CLÉS PAR DÉFAUT** pour un usage en production :

```bash
# Générer des clés aléatoires
openssl rand -hex 32  # ChaCha20 key (32 bytes)
openssl rand -hex 12  # Nonce (12 bytes)
```

### Usage Responsable

Espilon doit être utilisé uniquement pour :

- Tests d'intrusion **autorisés**
- Recherche en sécurité **éthique**
- Éducation et formation
- Prototypage IoT légitime

**Interdit** : Accès non autorisé, attaques malveillantes, violation de confidentialité.

---

## Cas d'Usage

### Pentest WiFi

- Audit de sécurité réseau
- Test de robustesse WPA2/WPA3
- Cartographie réseau

### IoT Security Research

- Test de devices IoT
- Analyse de protocoles
- Détection de vulnérabilités

### Éducation

- Labs de cybersécurité
- Cours d'embarqué
- CTF competitions

---

## Roadmap

### V2.0 (En cours)

- [ ] Mesh networking (BLE/WiFi)
- [ ] Améliorer la Documentations
- [ ] OTA updates
- [ ] Multilatération collaborative
- [ ] Optimisation mémoire

### Future

- [ ] PCB custom Espilon
- [ ] Support ESP32-S3/C3
- [ ] Module SDK pour extensions tierces
- [ ] Web UI pour C2

---

## Licence

Espilon est sous licence **MIT** avec addendum de sécurité.

Voir [LICENSE](LICENSE) pour les détails complets.

**En résumé** :

- Utilisation libre pour recherche, éducation, développement
- Modification et distribution autorisées
- **Obtenir autorisation** avant tout déploiement
- Usage malveillant strictement interdit

---

## Contributeurs

- **@Eun0us** - Core architecture, modules
- **@off-path** - C2 server, protocol
- **@itsoktocryyy** - Network features
- **@wepfen** - Documentation, tools

### Contribuer

Contributions bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md).

**Rejoignez-nous** :

- Rapporter des bugs
- Proposer des features
- Soumettre des PRs
- Améliorer la doc

---

## Liens Utiles

- **[Documentation complète](https://docs.espilon.net)**
- **[ESP-IDF Documentation](https://docs.espressif.com/projects/esp-idf/)**
- **[LilyGO T-Call](https://github.com/Xinyuan-LilyGO/LilyGO-T-Call-SIM800)**
- **English README** : [README.en.md](README.en.md)

---

## Support

- **Issues** : [GitHub Issues](https://github.com/Espilon-Net/Espilon-Source/issues)
- **Discussions** : [GitHub Discussions](https://github.com/Espilon-Net/Espilon-Source/discussions)

---

**Présenté initialement à Le Hack (Juin 2025)**

**Made with love for security research and education**
