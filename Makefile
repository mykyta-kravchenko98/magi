.PHONY: stage stage-no-gpu

stage:
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/deploy-stage.ps1

stage-no-gpu:
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/deploy-stage.ps1 -NoGpu
