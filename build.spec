appName = 'qCSF'
oneFile = False
block_cipher = None

a = Analysis(
	[f'{appName}\\__main__.py'],
	pathex=[f'D:\\Seafile\\My Library\\{appName}'],
	binaries=[],
	datas=[ (f'assets/{appName}/*', f'assets/{appName}') ],
	hiddenimports=['psychopy', 'psychopy.visual', 'psychopy.visual.shape', 'scipy._lib.messagestream', 'scipy.optimize.minpack2'],
	hookspath=[],
	runtime_hooks=[],
	excludes=[],
	win_no_prefer_redirects=False,
	win_private_assemblies=False,
	cipher=block_cipher
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if oneFile:
	exe = EXE(
		pyz,
		a.scripts,
		a.binaries,
		a.zipfiles,
		a.datas,
		name=appName,
		debug=True,
		strip=False,
		upx=True,
		runtime_tmpdir=None,
		console=True,
		icon=f'assets/{appName}/icon.ico'
	)
else:
	exe = EXE(
		pyz,
		a.scripts,
		exclude_binaries=True,
		name=appName,
		debug=False,
		strip=False,
		upx=True,
		console=False,
		icon=f'assets/{appName}/icon.ico',
	)

	coll = COLLECT(
		exe,
		a.binaries,
		a.zipfiles,
		a.datas,
		strip=False,
		upx=True,
		name=appName
	)