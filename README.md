#NOTE: This is very very simple documentation and doesn't show how it fully works or what it fully does, it only shows the Key features (NOT ALL) and functions but there are many many other functions and features. Also note this is NOT how the Backend fully works, this is only the BASICS, NOT full.


Gerne:
	(RAT - Spyware - Injector - Worm)



Files;

C2 : PhantomLink

Those files are the files needed to fully control or attack a victim.

C2:
C2 is your file, (C2 is short for "Command and Control) the file you can see, connect, attack, or control the victim/s, its the Listening file that wait for connection from the victim, it works as a reverse shell; wait for connection, and when a victim or more connect you can FULLY CONTROL thier PC, attack them, use them as BOTNET, do anything and everything, all the things that user can do and things that user can't do (EXAMPLE: control the voltage of a specefic USB port). You can spy on the victim with too many ways, PhantomLink came with a large package of Malwares including Spywares, you can inject "Auto-Screenshoter" (to automaticlly capture screenshots every specific moment and send it to the Listener through Telegram), you can also inject "KeyLogger" (record every key pressed on the keyboard and send it to the Listener every 30 MINS as a text file through Telegram, "Infostealers" (Steals saved login credintals on all websites (eg. Passwords, Usernames, E-Mails), "Banking Trojans", etc ...

PhantomLink:
PhantomLink is the file of the victim, the "Malware", the file that connect to the C2. It connects to the C2 and wait for commands and controls, it can excute any (Python - script - CMD - PowerShell) command (even if it required Admin Permissions). PhantomLink can Bypass Anti-Virus, Automaticlly startup with windows, hide itself, full invasion of the PC. It can Update itself automaticlly, remove itself if VM deceted, hide from Anti-Virus, add itself to exclusive folder in "Windows Defender Anti-Virus and Firewall".





📌 Overview
This project creates a reverse shell connection from a target (victim) machine back to an attacker (listener) machine, allowing remote command execution.

It uses Python sockets to establish the connection and optionally allows sending extra commands such as screenshots, file uploads/downloads, etc.

This Malware called "PhantomLink" and it came with too many components and its considerd as,
([Reverse Shell, Trogan, Worm, Injector, Spyware, Remote Access, Loader, Screenshoter]).



🔁 How It Works
Listener (C2) (Attacker Side):

A Python socket server listens for incoming connections.

Once a client connects, the attacker can send terminal commands through a simple interface.

Extra features like:

screenshot — capture victim's screen and send to listener.

get — download file from attacker server.

send — upload file from victim to listener.
and way way more (Check "Quick Commands.txt" for more commands and informations).

Implements timeout in case of no output.


Client (PhantomLink) (Victim Side):

Connects back to the attacker's IP and port.

Waits for incoming commands, executes them, and sends back the output.

Can be auttomaticly updated if there are any new versions.

Can inject new Malwares and run it and hide it then add it to Startup Apps.



Supports:

CMD command execution.

PowerShell commands.

Python Scripts.

Continuous retry logic if the connection drops.

Can be set up to persist via Windows Registry (Run key), "Windows Sceduler", Registry, for auto startup.

Can be auttomaticly updated if there are any new versions.

Can inject new Malwares and run it and hide it then add it to Startup Apps.

Can easily Bypass Anti-Viruses by; Adding itself to exclusive folder, inject itself to legit processes, end the Anti-Virus task, Disable the Anti-Virus.




NOTE: This is very very simple documentation and doesn't show how it fully works or what it fully does, it only shows the Key features (NOT ALL) and functions but there are many many other functions and features. Also note this is NOT how the Backend fully works, this is only the BASICS, NOT full.
