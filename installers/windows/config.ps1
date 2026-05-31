# Granularity Analyser - Windows installer constants
$script:GranularityConfig = @{
    GitHubRepoUrl      = 'https://github.com/LuisMRaimundo/Granularity-Analyser'
    AppName            = 'Granularity Analyser'
    PythonVersion      = '3.11'
    PythonMinMinor     = 10
    PythonMaxMinor     = 12
    PythonInstallerUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    RequirementsFile   = 'requirements-app.txt'
    LaunchModule       = 'granular_v2.gui'
    VenvFolder         = '.venv'
    StartBatName       = 'START-Granularity.bat'
}
