# Derivation de offsets — Free Fire

Los offsets de `ff_hook.js` cambian por versión y arquitectura. Se derivan con Il2CppDumper.

## 1. Extraer libil2cpp.so y global-metadata.dat

Desde el emulador:

    adb pull /data/app/<pkg>/lib/x86_64/libil2cpp.so
    adb pull /data/app/<pkg>/lib/x86_64/global-metadata.dat

O desde el APK:

    unzip FreeFire.apk "lib/x86_64/libil2cpp.so" "assets/bin/Data/Managed/Metadata/global-metadata.dat"

## 2. Il2CppDumper

    Il2CppDumper.exe libil2cpp.so global-metadata.dat out/

Genera `out/dump.cs`, `out/dummy.dll`, `out/script.json`.

## 3. Localizar los símbolos

En `dump.cs`:

- `class GameManager` → anota el **RVA**
- dentro, campo `playerList` o `matchPlayerList` → **offset del campo**
- `class Player` (o `MatchPlayer`, `Character`) → campos:
  - `transform` / `position` (Vector3) → **offset**
  - `teamId` (int) → **offset**
  - `isDead` / `health` → **offset**
- `Camera.main` → matriz view-projection

En `script.json` los mismos símbolos aparecen con `Address` — ese es el RVA.

## 4. Rellenar OFF

    gameManagerClass: 0x<RVA de GameManager>
    playerListField:  0x<offset>
    playerPosField:   0x<offset>
    playerTeamField:  0x<offset>
    playerDeadField:  0x<offset>
    cameraMatrix:     0x<offset o puntero a matriz>

## 5. Verificar en Frida

Con el juego corriendo y frida-server activo:

    frida -H 127.0.0.1:27042 -n "Free Fire" -l ff_hook.js

En consola: `rpc.exports.getEntities()` debe devolver un array. Si es `[]`, imprime size/ptr para depurar:

    console.log("size=", size, "items=", items);

## 6. Re-derivar por versión

Cada update de Free Fire puede mover RVAs. Guarda un `.txt` con los offsets por versión y cambia `OFF` cuando el juego actualice.