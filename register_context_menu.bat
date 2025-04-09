Windows Registry Editor Version 5.00

; ===== 文件夹右键菜单 =====
[HKEY_CLASSES_ROOT\Directory\shell\文件转移工具2.0]
@="文件转移工具2.0"
"Icon"="C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe"

[HKEY_CLASSES_ROOT\Directory\shell\文件转移工具2.0\shell\organize]
@="整理此文件夹"
[HKEY_CLASSES_ROOT\Directory\shell\文件转移工具2.0\shell\organize\command]
@="\"C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe\" \"%1\" organize"

[HKEY_CLASSES_ROOT\Directory\shell\文件转移工具2.0\shell\sync]
@="同步到目标文件夹"
[HKEY_CLASSES_ROOT\Directory\shell\文件转移工具2.0\shell\sync\command]
@="\"C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe\" \"%1\" sync"

[HKEY_CLASSES_ROOT\Directory\shell\文件转移工具2.0\shell\gui]
@="作为源路径打开"
[HKEY_CLASSES_ROOT\Directory\shell\文件转移工具2.0\shell\gui\command]
@="\"C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe\" \"%1\" gui"

; ===== 空白区域右键菜单 =====
[HKEY_CLASSES_ROOT\Directory\Background\shell\文件转移工具2.0]
@="文件转移工具2.0"
"Icon"="C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe"

[HKEY_CLASSES_ROOT\Directory\Background\shell\文件转移工具2.0\shell\organize]
@="整理此文件夹"
[HKEY_CLASSES_ROOT\Directory\Background\shell\文件转移工具2.0\shell\organize\command]
@="\"C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe\" \"%V\" organize"

[HKEY_CLASSES_ROOT\Directory\Background\shell\文件转移工具2.0\shell\sync]
@="同步到目标文件夹"
[HKEY_CLASSES_ROOT\Directory\Background\shell\文件转移工具2.0\shell\sync\command]
@="\"C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe\" \"%V\" sync"

[HKEY_CLASSES_ROOT\Directory\Background\shell\文件转移工具2.0\shell\gui]
@="作为源路径打开"
[HKEY_CLASSES_ROOT\Directory\Background\shell\文件转移工具2.0\shell\gui\command]
@="\"C:\\Program Files\\文件转移工具2.0\\文件转移工具2.0.exe\" \"%V\" gui"
