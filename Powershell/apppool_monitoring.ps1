if((Get-WebAppPoolState -Name ecop).Value -ne 'Started'){
    Write-Output ('Starting Application Pool: ecop')
    Start-WebAppPool -Name ecop
}