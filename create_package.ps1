$excludeDirs = @('node_modules', 'dist', '.git', '.trae', '__pycache__', 'data', 'uploads')
$excludeFiles = @('.env', '.gitignore', '*.pyc', 'node.msi', 'test.db', 'exercise.db')

$packageName = 'fuxi-deploy.zip'

if (Test-Path $packageName) {
    Remove-Item $packageName -Force
}

$zip = [IO.Compression.ZipFile]::Open($packageName, [IO.Compression.ZipArchiveMode]::Create)

function Add-Files {
    param($sourceDir, $zipDir)
    
    Get-ChildItem -Path $sourceDir -File | ForEach-Object {
        $fileName = $_.Name
        
        $shouldExclude = $false
        foreach ($pattern in $excludeFiles) {
            if ($fileName -like $pattern) {
                $shouldExclude = $true
                break
            }
        }
        
        if (-not $shouldExclude) {
            $entryPath = if ($zipDir) { "$zipDir/$fileName" } else { $fileName }
            Write-Host "  添加: $entryPath"
            $entry = $zip.CreateEntry($entryPath)
            $stream = $entry.Open()
            $fileBytes = [IO.File]::ReadAllBytes($_.FullName)
            $stream.Write($fileBytes, 0, $fileBytes.Length)
            $stream.Dispose()
        }
    }
    
    Get-ChildItem -Path $sourceDir -Directory | ForEach-Object {
        $dirName = $_.Name
        
        $shouldExclude = $false
        foreach ($exclude in $excludeDirs) {
            if ($dirName -eq $exclude) {
                $shouldExclude = $true
                break
            }
        }
        
        if (-not $shouldExclude) {
            $newZipDir = if ($zipDir) { "$zipDir/$dirName" } else { $dirName }
            Add-Files -sourceDir $_.FullName -zipDir $newZipDir
        }
    }
}

Write-Host "创建部署包: $packageName"
Add-Files -sourceDir '.' -zipDir $null
$zip.Dispose()

$size = (Get-Item $packageName).Length / 1KB
Write-Host "`n部署包已创建: $packageName ($($size -as [int]) KB)"
