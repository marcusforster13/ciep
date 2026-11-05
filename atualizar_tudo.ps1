# A mensagem - ocorrencia em uma escola (CIEP) - regenera todas as versoes a partir da cena principal.
#   01_Cena_Render_Cycles\ciep.py  ->  ciep.blend  (FONTE: o script; o .blend e refeito a cada "recriar")
#     -> 02_Cena_VR_Otimizada  (Unity / Unreal: .blend, .glb, .fbx, colisao)
#     -> 04_ThreeJS\web         (WebXR: cena.glb, lightmaps, cena.json)
#   07_Personagens (Rocketbox, em Desktop\leiseca\07_Personagens\rocketbox) -> 04_ThreeJS\web\personagens
#
# Uso:  .\atualizar_tudo.ps1 recriar alta      (o normal: refaz a cena do zero e assa a luz em qualidade alta)
#       .\atualizar_tudo.ps1 recriar rapido    (teste)
$ErrorActionPreference = "Stop"
$B = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$D = $PSScriptRoot

Push-Location "$D\01_Cena_Render_Cycles"
if ($args -contains "recriar" -or -not (Test-Path "ciep.blend")) {
    Write-Host "0/3  Criando a cena principal do zero (ciep.py)..."
    & $B -b --factory-startup --python "ciep.py" 2>&1 | Select-String -Pattern '^\[CIEP\]' | ForEach-Object { $_.Line }
}
Write-Host "0/3  Aplicando texturas CC0 na cena principal..."
& $B -b "ciep.blend" --python "aplicar_texturas_cc0.py" 2>&1 | Select-String -Pattern '^\[CC0\]' | ForEach-Object { $_.Line }
Pop-Location

Write-Host "1/3  Gerando versao VR (Unity/Unreal) e colisao..."
Push-Location "$D\02_Cena_VR_Otimizada"
& $B -b "$D\01_Cena_Render_Cycles\ciep.blend" --python "otimizar_para_vr.py" *> vr_log.txt
Pop-Location
Select-String -Path "$D\02_Cena_VR_Otimizada\vr_log.txt" -Pattern '^\[VR\] (TOTAL|Colisao)' | ForEach-Object { $_.Line }

Write-Host "2/3  Gerando versao three.js (bake de lightmaps)..."
Push-Location "$D\04_ThreeJS"
$nivel = $args | Where-Object { $_ -in "rapido", "alta" }
& $B -b "$D\02_Cena_VR_Otimizada\ciep_VR.blend" --python "pipeline_threejs.py" -- $nivel *> pipeline_log.txt
Pop-Location
Select-String -Path "$D\04_ThreeJS\pipeline_log.txt" -Pattern '^\[THREE\]' | ForEach-Object { $_.Line }

Write-Host "3/3  Personagens (Rocketbox -> 04_ThreeJS\web\personagens; so refaz o que mudou)..."
if ((Test-Path "$D\07_Personagens\rocketbox") -or (Test-Path "$D\..\leiseca\07_Personagens\rocketbox")) {
    & $B -b --factory-startup --python "$D\07_Personagens\converter_personagens.py" 2>&1 | Select-String -Pattern '^\[PERSONAGENS\]' | ForEach-Object { $_.Line }
} else { Write-Host "     (pasta rocketbox nao encontrada; mantidos os .glb atuais - ver 07_Personagens\LEIA-ME.md)" }
Write-Host "Pronto. Para ver no navegador: 04_ThreeJS\web\iniciar_servidor.bat"
