# BROWSOR

**A calm desktop browser for everyday browsing, searching, and your favorite AI assistant.**

BROWSOR is a desktop browser built with Python, PySide6, and Qt WebEngine. Customize your start page, save your favorite websites, and open AI services in a convenient side panel.

## Features

- Browse with tabs, an address bar, navigation history, and downloads.
- Search with DuckDuckGo, Google, or Bing.
- Save and manage your favorite websites.
- Open Gemini, ChatGPT, Claude, Microsoft Copilot, or Perplexity in the side panel.
- Personalize your start page with a display name, accent color, and preferences.
- Choose whether website sign-ins are remembered on this computer.
- Enable or disable a basic filter for known tracking domains.

## Installation
<img width="1322" height="932" alt="image" src="https://github.com/user-attachments/assets/dc395fb7-52cd-4226-ba85-754aa63dbfba" />

### Requirements

- Python 3.10 or later
- A desktop environment supported by PySide6 and Qt WebEngine

Open a terminal in the `apps/BROWSOR` directory and create a virtual environment.

**Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

**macOS or Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On first launch, you can set up your preferences. No BROWSOR account is required.

## Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+L` | Focus the address bar |
| `Ctrl+T` | Open a new tab |
| `Ctrl+W` | Close the current tab |
| `Ctrl+Shift+T` | Reopen the last closed tab |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Switch between tabs |
| `Ctrl+D` | Save the current website as a favorite |
| `Ctrl+Shift+B` | Manage favorites |
| `Ctrl+Shift+A` | Show or hide the AI side panel |
| `Ctrl+J` | Open downloads |
| `Ctrl+F` | Find text on the current page |
| `Ctrl+,` | Open settings |
| `F11` | Toggle full-screen mode |

## Privacy

- Your profile, preferences, and favorites are stored locally on your computer.
- The HTTP cache is kept in memory and is not saved after the app closes.
- Website cookies are not saved after the app closes by default. Enable **Stay signed in to websites** to keep sign-ins on this computer.
- The tracker filter blocks a limited list of known tracking domains. It is not a complete ad or tracker blocker.
- Websites can see your IP address. Search queries and AI services are handled by the search engine or service you choose.

## License

No license has been added to this project yet. Until one is added, reuse is not automatically permitted.
