build:
    cd hk-mods/SuperFancyInteropMod && dotnet build -c Release

install_linux: build
    mkdir ~/.local/share/Steam/steamapps/common/Hollow\ Knight/hollow_knight_Data/Managed/Mods/SuperFancyInteropMod || true
    unzip hk-mods/SuperFancyInteropMod/Output/SuperFancyInteropMod.zip -d ~/.local/share/Steam/steamapps/common/Hollow\ Knight/hollow_knight_Data/Managed/Mods/SuperFancyInteropMod

