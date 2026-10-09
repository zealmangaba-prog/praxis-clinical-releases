# Praxis Clinical: Treatment Plan & Report Generator

Welcome to **Praxis Clinical**, a private, offline desktop application designed specifically for South African mental health professionals (Clinical Psychologists, Counselling Psychologists, and Registered Counsellors) to generate compliant treatment plans, motivation letters, and clinical reports in minutes.

---

## 🔒 100% Private, Local & POPIA-Compliant

* **No Cloud Transmission:** Everything runs directly on your computer. Patient names, clinical notes, and medical aid identifiers are never sent to external servers.
* **POPIA Data Sovereignty:** Designed to comply with South African healthcare data protection standards by keeping clinical data entirely on your physical machine.
* **HPCSA Scope Alignment:** Features registration-specific scope guidance and presets tailored for major medical schemes (Discovery Health, GEMS, Medscheme, Bonitas, and more).

---

## 💻 System Prerequisites

You only need two free tools installed on your computer:

1. **Python (version 3.10 or 3.11):**  
   * Download from [python.org](https://www.python.org/downloads/).  
   * *Windows Users:* Check the box that says **"Add Python to PATH"** during installation.
2. **Ollama (for the offline AI assistant):**  
   * Download and install the free app from [ollama.com](https://ollama.com/).  
   * Open the Ollama application once so it remains active in your menu bar or system tray.
   * *Note:* You do not need to download models via the command line; the app handles the setup automatically on your first run.

---

## 🚀 How to Launch the Application

### macOS (Apple)
1. Double-click the downloaded **`Clinical_Report_Generator_macOS.zip`** to extract it.
2. Open the extracted folder and double-click **`run_app.command`**.
3. A setup terminal window will appear to prepare the environment, and your default web browser will open automatically to **`http://localhost:8501`**.

> **First-time Mac prompt:** If macOS flags the file with an *"unidentified developer"* notice:
> 1. Right-click (or hold `Control` and click) on **`run_app.command`**.
> 2. Select **Open** from the context menu.
> 3. Click **Open** on the confirmation dialog. This step is only required once.

---

### Windows (PC)
1. Right-click **`Clinical_Report_Generator_Windows.zip`**, select **Extract All**, and open the resulting folder.
2. Double-click **`run_app.bat`**.
3. The launcher will configure the environment and open **`http://localhost:8501`** in your default web browser.

---

## 🔑 Activating Your License

On first launch, you will be prompted with an activation screen:

1. Enter your **BHF Practice Number** (e.g., `0374008`).
2. Paste the **License Key** supplied in your welcome email.
3. Click **Activate License**.

Validation occurs offline against an embedded public signature. No active internet connection is required to authenticate.

---

## 🧭 How to Use the Application

1. **Configure Your Profile (Sidebar):**
   * Select your HPCSA registration category (*Registered Counsellor*, *Counselling Psychologist*, or *Clinical Psychologist*).
   * Enter your name, practice physical address, and upload a digital signature image for automated sign-offs.
2. **Select Symptoms & Clinical Parameters:**
   * Select observed symptom clusters and specify treatment targets.
   * Choose the client's medical aid scheme to apply standard tariff codes and scheme-specific templates.
3. **Synthesize & Export:**
   * Click **Synthesize Clinical Formulation**.  
     *(On the very first run, an in-app setup bar will automatically configure the private clinical model. Subsequent runs execute immediately).*
   * Review the generated formulation, adjust clinical notes as needed, and export your finalized, formatted PDF or Word report.

---

## ❓ Frequently Asked Questions

**Q: Do I need internet access after the initial setup?**  
No. Once the local AI model is installed on first use, Praxis Clinical operates completely offline.

**Q: Where are the generated reports saved?**  
Exported PDFs and documents download directly to your computer's standard **Downloads** folder.

**Q: How do I close the application?**  
Close your browser tab, then close the terminal/command window that opened when running the launch script.

---

## ⚖️ Regulatory & Professional Notice

* **HPCSA Human-in-the-Loop Standard:** Praxis Clinical is strictly an assistive documentation tool. In accordance with the ethical rules and professional conduct standards of the Health Professions Council of South Africa (HPCSA), the registered treating practitioner retains complete professional, legal, and clinical responsibility for verifying, reviewing, and signing off on all formulations, diagnoses, and medical aid submissions.
* **Copyright Notice:** © 2026 Zeal Katlego Mangaba. All Rights Reserved.