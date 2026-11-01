# T6 perks (Lua to GSC)

Perks are written in a small subset of Lua (see `API.md`). `lua2gsc` turns them into GSC for BO2 Zombies.

## Build lua2gsc

The compiler is one header and one source file (C++17, no dependencies) in `lua2gsc\`. With the Visual Studio build tools,
from a Developer Command Prompt in this folder:

    cl /std:c++17 /EHsc /O2 lua2gsc\lua2gsc.cpp /Fe:lua2gsc.exe

With g++ or clang++:

    g++ -std=c++17 -O2 lua2gsc/lua2gsc.cpp -o lua2gsc

If it fails: check you are in this folder, and that the compiler really is in C++17 mode (an old compiler or missing `/std:c++17` is the usual cause).

The built `lua2gsc.exe` and `.obj` files are ignored by git on purpose, so build your own.

## Use it

    lua2gsc runtime\zm_workshop_perks.gsc out\zm_workshop_perks.gsc examples\vampire.lua examples\adrenaline.lua

The first file is the runtime, the second is the output, and the rest are your perks. `python tests\run_tests.py lua2gsc.exe path\to\gsc-tool.exe` runs the checks.
