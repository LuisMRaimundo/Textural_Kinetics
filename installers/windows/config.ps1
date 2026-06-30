# Temporal_Granularity - Windows installer constants
$script:TemporalGranularityConfig = @{
    GitHubRepoUrl      = 'https://github.com/LuisMRaimundo/Temporal_Granularity'
    AppName            = 'Temporal_Granularity'
    PythonVersion      = '3.11'
    PythonMinMinor     = 10
    PythonMaxMinor     = 12
    PythonInstallerUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    RequirementsFile   = 'requirements-app.txt'
    LaunchModule       = 'granular_v2.gui'
    VenvFolder         = '.venv'
    StartBatName       = 'START-Temporal_Granularity.bat'
}
