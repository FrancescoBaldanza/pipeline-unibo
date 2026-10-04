# Pipeline UniBo: Automazione Download, Obsidian Sync, OCR & NotebookLM

Sistema unificato e modulare per la gestione del materiale universitario (UniBo) progettato per mantenere costantemente sincronizzati il proprio Obsidian Vault e Google NotebookLM con download automatici e trascrizioni OCR intelligenti basate su IA.

---

## 🎯 Panoramica e Architettura

La pipeline gestisce 4 corsi attivi del semestre:
- **Architetture dei Calcolatori**
- **Basi di Dati**
- **Matematica Applicata**
- **Fisica Generale**

*(I corsi terminati come `Analisi Matematica 2` e `Reti Logiche` rimangono intatti e isolati).*

Il flusso si articola in 4 fasi principali:

1. **Download**: download del materiale tramite il comando `dlub -get all` nella cartella sorgente `~/Desktop/Materiale`.
2. **Base & Sync Obsidian**: replica strutturata nella cartella vault `~/Desktop/UniBo`, applicando regole di ridenominazione cartelle, normalizzazione nomi lezioni (`(NEW) XX - Titolo`) e filtraggio rigido su estensioni consentite (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.md`).
3. **Conversione AI (OCR/LaTeX/Diagrammi)**: per le lezioni di **Fisica Generale** e **Matematica Applicata**, trascrive i PDF manoscritti e stampati in Markdown arricchito con formule LaTeX (`$...$`), schemi estratti in `images/` e titoli semantici generati contestualmente con Gemini. Un registro SHA-256 evita qualsiasi riconversione non necessaria.
4. **Push NotebookLM**: carica automaticamente tutte le fonti nei 4 rispettivi NotebookLM ufficiali, ripulendo il prefisso `(NEW) ` dal titolo remoto e tracciando l'hash dei file caricati.

---

## 📁 Struttura del Progetto

```
pipeline-unibo/
├── config/
│   ├── settings.py           # Path, API keys, Notebook IDs, estensioni
│   └── course_rules.py       # Regole di mappatura, filtri e routing cartelle
├── core/
│   ├── base_sync.py          # Replica, filtri e migrazione note legacy
│   ├── converter.py          # Trascrizione OCR Gemini Vision & LaTeX
│   ├── notebooklm_sync.py    # Uploader verso NotebookLM con dedup SHA-256
│   ├── downloader.py         # Wrapper di download dlub
│   └── tracker.py            # Registro persistente conversioni e upload
├── scripts/
│   ├── run_pipeline.py       # Entrypoint CLI principale
│   └── manage_cron.py        # Gestore pulizia e installazione cronjob
├── tests/
│   ├── test_rules.py         # Test unitari regole corsi e naming
│   └── test_tracker.py       # Test unitari persistenza tracker
├── requirements.txt
└── README.md
```

---

## 🚀 Utilizzo CLI

### Esecuzione Completa
```bash
python scripts/run_pipeline.py --all
```

### Esecuzione per Singola Fase
- **Solo Download**: `python scripts/run_pipeline.py --download`
- **Solo Sync Cartelle & Obsidian**: `python scripts/run_pipeline.py --sync-base`
- **Solo Conversione OCR**: `python scripts/run_pipeline.py --convert`
- **Solo Push NotebookLM**: `python scripts/run_pipeline.py --push`
- **Sync + OCR + Push (senza download)**: `python scripts/run_pipeline.py --no-download`

---

## ⏰ Gestione Automazioni (Cron)

Per disattivare vecchi cronjob obsoleti:
```bash
python scripts/manage_cron.py
```

Per installare il nuovo cronjob unificato (ogni 4 ore):
```bash
python scripts/manage_cron.py --install
```
