# REMder

**REMder** — Your Ultimate Deadline Reminder is a small, local desktop reminder application written in Python using the Textual TUI framework and pygame for simple audio alerts. It lets you create deadline tasks, chooses sensible pre-deadline alerts, optionally associate an audio file per task, and persistently saves tasks on disk.

This README explains the design, installation, usage, file formats, and development notes so you can run, modify, or package REMder.

---

## Features

* Simple terminal-based interface  
* Cross-platform (assuming Python support)  
* Packaged using PyInstaller (or similar) to generate an executable or spec file  
* Modular design: separation of UI (CSS), logic (Python)  

---

## Installation

1. Clone the repository:  
   ```bash
   git clone https://github.com/MuhammadEltokhy/REMder.git
   cd REMder
   exit
   Then, download the only 2 needed packeges throught pip (assuming u have a pip version that is or higher than 3.0).
   ```bash
   pip install textual
   pip install pygame
2. Download the release:
   simply open the release section in the repository
   download the .exe file
   run it!

## How to Start?
Just open the app, press **_s_** in ur keyboard, and now it's your beginning!
* All shortcut keys found in the footer widget of the app.
* When press **_a_**, a small window would open for u to add a new deadline.
* You r able to make a new name for ur dead, choose the dead itself, and optionally choose which sound u'd like to have in ur alarms.
* Save the deadline, and congratulations! This s ur 1st deadline task!  
