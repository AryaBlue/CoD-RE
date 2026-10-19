@call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat" >nul 2>nul
@cd /d "%~dp0"
@cl /nologo /DARCH_x86 /std:c++17 /EHsc sizes.cpp > cl.log 2>&1 || (findstr /i " error " cl.log & exit /b 1)
@sizes.exe
