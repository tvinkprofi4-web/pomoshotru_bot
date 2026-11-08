Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\user\Desktop\pomoshotru_bot"
WshShell.Run "python watchdog.py", 0, False
