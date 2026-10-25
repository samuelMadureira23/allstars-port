@echo off
rem Configura e compila o port nativo (allstars-ps3 + ps3recomp) com clang-cl.
rem Uso: scripts\build.bat [Release^|RelWithDebInfo^|Debug] [agente]
rem   sem agente : integracao  -> src\ps3recomp + src\allstars-ps3      -> build\
rem   com agente : worktree    -> agents\<agente>\{ps3recomp,allstars-ps3} -> build-<agente>\
rem O codigo lifted (work\recompiled_1.00, work\spu\lifted) e compartilhado.
setlocal
set ROOT=%~dp0..
set CFG=%1
if "%CFG%"=="" set CFG=Release
set AGENT=%2

if "%AGENT%"=="" (
  set SDK=%ROOT%\src\ps3recomp
  set PORT=%ROOT%\src\allstars-ps3
  set BUILD=%ROOT%\build
) else (
  set SDK=%ROOT%\agents\%AGENT%\ps3recomp
  set PORT=%ROOT%\agents\%AGENT%\allstars-ps3
  set BUILD=%ROOT%\build-%AGENT%
)
if not exist "%SDK%\CMakeLists.txt" ( echo ERRO: %SDK% nao existe & exit /b 1 )

call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set PATH=C:\Program Files\LLVM\bin;C:\Program Files\CMake\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%

cmake -B "%BUILD%" -G Ninja ^
  -DCMAKE_BUILD_TYPE=%CFG% ^
  -DCMAKE_C_COMPILER=clang-cl -DCMAKE_CXX_COMPILER=clang-cl ^
  -DPS3RECOMP_DIR="%SDK%" ^
  -DRECOMP_DIR="%ROOT%\work\recompiled_1.00" ^
  -DSPU_DIR="%ROOT%\work\spu\lifted" ^
  -DCMAKE_EXE_LINKER_FLAGS="/MAP" ^
  "%PORT%" || exit /b 1

cmake --build "%BUILD%" || exit /b 1
echo BUILD OK: %BUILD%\MyGameRecomp.exe
