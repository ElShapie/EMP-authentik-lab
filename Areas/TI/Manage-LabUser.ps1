<# Operaciones Graph en un tenant de laboratorio autorizado. No guardar contraseñas en archivos. #>
[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Create','Update','ResetPassword','Block','Delete','AssignLicense','Audit')][string]$Action,
    [Parameter(Mandatory=$true)][string]$TenantId,
    [Parameter(Mandatory=$true)][string]$UserPrincipalName,
    [string]$DisplayName='Lab Account',
    [string]$Department='TI',
    [string]$UsageLocation,
    [string]$SkuId,
    [switch]$ConfirmLabDeletion
)
$ErrorActionPreference='Stop'
$scopes = if ($Action -eq 'Audit') { @('User.Read.All','AuditLog.Read.All') } elseif ($Action -eq 'Block') { @('User.ReadWrite.All','User.RevokeSessions.All') } elseif ($Action -eq 'AssignLicense') { @('User.ReadWrite.All','LicenseAssignment.ReadWrite.All') } else { @('User.ReadWrite.All') }
Connect-MgGraph -TenantId $TenantId -Scopes $scopes -NoWelcome
try {
    if (-not $PSCmdlet.ShouldProcess($UserPrincipalName,$Action)) { return }
    if ($Action -eq 'Delete' -and -not $ConfirmLabDeletion) { throw 'Eliminar requiere -ConfirmLabDeletion y confirmar que es una cuenta de práctica.' }
    $user = if ($Action -eq 'Create') { $null } else { Get-MgUser -UserId $UserPrincipalName }
    switch ($Action) {
        'Create' {
            $secure = Read-Host 'Contraseña temporal robusta' -AsSecureString
            $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
            try {
                $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
                $body = @{ accountEnabled=$true;displayName=$DisplayName;mailNickname=$UserPrincipalName.Split('@')[0];userPrincipalName=$UserPrincipalName;department=$Department;passwordProfile=@{password=$password;forceChangePasswordNextSignIn=$true} }
                New-MgUser -BodyParameter $body | Select-Object Id,UserPrincipalName
            } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer);$password=$null;$body=$null }
        }
        'Update' { Update-MgUser -UserId $user.Id -Department $Department -DisplayName $DisplayName }
        'ResetPassword' {
            $secure = Read-Host 'Nueva contraseña temporal robusta' -AsSecureString
            $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
            try {
                $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
                Update-MgUser -UserId $user.Id -PasswordProfile @{password=$password;forceChangePasswordNextSignIn=$true}
            } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer);$password=$null }
        }
        'Block' {
            Update-MgUser -UserId $user.Id -AccountEnabled:$false
            Revoke-MgUserSignInSession -UserId $user.Id | Out-Null
        }
        'Delete' { Remove-MgUser -UserId $user.Id -Confirm }
        'AssignLicense' {
            if (-not $UsageLocation -or -not $SkuId) { throw 'Indicar UsageLocation de dos letras y SkuId de una licencia disponible.' }
            Update-MgUser -UserId $user.Id -UsageLocation $UsageLocation
            Set-MgUserLicense -UserId $user.Id -AddLicenses @(@{SkuId=[Guid]$SkuId}) -RemoveLicenses @() | Select-Object Id
        }
        'Audit' {
            Get-MgAuditLogSignIn -Filter "userId eq '$($user.Id)'" -Top 20 | Select-Object CreatedDateTime,AppDisplayName,Status
            Get-MgAuditLogDirectoryAudit -Top 20 | Select-Object ActivityDateTime,ActivityDisplayName,Result
        }
    }
} finally { Disconnect-MgGraph | Out-Null }
