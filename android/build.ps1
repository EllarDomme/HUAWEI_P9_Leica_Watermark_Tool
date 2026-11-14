# Build a minimal signed APK without Gradle / Android Studio.
$ErrorActionPreference = 'Stop'
$sdk = 'E:\DeskTop\_android_sdk'
$bt  = Join-Path $sdk 'build-tools\33.0.2'
$jar = Join-Path $sdk 'platforms\android-33\android.jar'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$build = Join-Path $root 'build'
$env:JAVA_HOME = 'C:\Users\34684\.jdks\ms-17.0.19'
$env:PATH = "$env:JAVA_HOME\bin;$bt;$env:PATH"

Copy-Item (Join-Path $root '..\index.html') (Join-Path $root 'assets\index.html') -Force

# 发行版里剥掉测试钩子（源码仍保留，方便本地截图测试）
$htmlPath = Join-Path $root 'assets\index.html'
$html = [System.IO.File]::ReadAllText($htmlPath)
$shim = "function demoAuto(){ return readStore(STORE_AUTO); }`n  function demoBoot(){}`n  function demoApply(){}"
$html = [regex]::Replace($html, '(?s)/\*__DEV_START__\*/.*?/\*__DEV_END__\*/', $shim)
if ($html -match '__DEMO|__setDemo') { throw 'demo hooks still present' }

# 版本号同步：把页面里的 verText 换成 manifest 的 versionName
$verMatch = [regex]::Match($html, 'android:versionName="([^"]+)"')
if ($verMatch.Success) {
  $ver = $verMatch.Groups[1].Value
  $html = [regex]::Replace($html, '(?s)(<span id="verText">)[^<]*(</span>)', ('$1' + $ver + '$2'))
  Write-Host ("    版本号同步为 " + $ver)
}
[System.IO.File]::WriteAllText($htmlPath, $html, (New-Object System.Text.UTF8Encoding($false)))
if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Path $build, "$build\classes", "$build\dex" -Force | Out-Null

Write-Host '[1/6] aapt2 compile + link'
# 有 res/ 时先编译资源（图标等）；用 cmd 调用，避免 PowerShell 直接调 exe 时的 zip 写入问题
$resDir = "$root\res"
$resArg = ''
if (Test-Path $resDir) {
  $resZip = "$build\res.zip"
  cmd /c "`"$bt\aapt2.exe`" compile --dir `"$resDir`" -o `"$resZip`" 2>&1"
  if ($LASTEXITCODE -ne 0) { throw 'aapt2 compile failed' }
  $resArg = "`"$resZip`""
}
cmd /c "`"$bt\aapt2.exe`" link -o `"$build\base.apk`" -I `"$jar`" --manifest `"$root\AndroidManifest.xml`" -A `"$root\assets`" --min-sdk-version 21 --target-sdk-version 33 $resArg 2>&1"
if ($LASTEXITCODE -ne 0) { throw 'aapt2 link failed' }

Write-Host '[2/6] javac'
$ErrorActionPreference = 'Continue'
& javac -source 8 -target 8 -bootclasspath $jar -d "$build\classes" "$root\src\com\ellardomme\p9watermark\MainActivity.java" 2>&1 | Out-Null
$jc = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($jc -ne 0) { throw 'javac failed' }

Write-Host '[3/6] d8'
$classes = (Get-ChildItem "$build\classes" -Recurse -Filter *.class | ForEach-Object { $_.FullName })
& java -cp "$bt\lib\d8.jar" com.android.tools.r8.D8 --lib $jar --min-api 21 --output "$build\dex" $classes
if ($LASTEXITCODE -ne 0) { throw 'd8 failed' }

Write-Host '[4/6] add classes.dex'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$build\base.apk", 'Update')
$dexEntry = $zip.CreateEntry('classes.dex', [System.IO.Compression.CompressionLevel]::Optimal)
$in = [System.IO.File]::OpenRead("$build\dex\classes.dex")
$out = $dexEntry.Open()
$in.CopyTo($out)
$out.Close(); $in.Close(); $zip.Dispose()

Write-Host '[5/6] zipalign'
& "$bt\zipalign.exe" -f 4 "$build\base.apk" "$build\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw 'zipalign failed' }

Write-Host '[6/6] sign'
$ks = "$root\debug.keystore"
if (-not (Test-Path $ks)) {
  $ErrorActionPreference = 'Continue'
  & keytool -genkeypair -keystore $ks -alias androiddebugkey -storepass android -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" 2>&1 | Out-Null
  $ErrorActionPreference = 'Stop'
  if (-not (Test-Path $ks)) { throw 'keystore failed' }
}
$apk = "$root\P9Watermark.apk"
& java -jar "$bt\lib\apksigner.jar" sign --ks $ks --ks-pass pass:android --key-pass pass:android --out $apk "$build\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw 'apksigner failed' }
$ErrorActionPreference = 'Continue'
& java -jar "$bt\lib\apksigner.jar" verify --print-certs $apk 2>&1 | Out-String | Write-Host
$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host ("APK: {0}  ({1:N0} KB)" -f $apk, ((Get-Item $apk).Length / 1KB))

# 同步到官网的固定下载地址（两个位置，老页面缓存也能命中）
$site1 = Join-Path (Split-Path $root -Parent) 'download'
$site2 = Join-Path (Split-Path $root -Parent) 'welcome\download'
foreach ($d in @($site1, $site2)) {
  if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  Copy-Item $apk (Join-Path $d 'P9Watermark.apk') -Force
  Write-Host ("  已同步: {0}" -f (Join-Path $d 'P9Watermark.apk'))
}



