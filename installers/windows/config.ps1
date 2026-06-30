# Textural_Kinetics - Windows installer constants
$script:TexturalKineticsConfig = @{
    GitHubRepoUrl      = 'https://github.com/LuisMRaimundo/Temporal_Granularity'
    AppName            = 'Textural_Kinetics'
    PythonVersion      = '3.11'
    PythonMinMinor     = 10
    PythonMaxMinor     = 12
    PythonInstallerUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    RequirementsFile   = 'requirements-app.txt'
    LaunchModule       = 'granular_v2.gui'
    VenvFolder         = '.venv'
    StartBatName       = 'START-Textural_Kinetics.bat'
}
