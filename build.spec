# -*- mode: python -*-

block_cipher = None


a = Analysis(
	['qCSF\\__main__.py'],
	pathex=['D:\\Seafile\\My Library\\qCSF2'],
	binaries=[],
	datas=[ ('qCSF/assets/*', 'qCSF/assets') ],
	hiddenimports=['psychopy', 'psychopy.visual', 'psychopy.visual.shape', 'scipy._lib.messagestream', 'scipy.optimize.minpack2'],
	hookspath=[],
	runtime_hooks=[],
	excludes=[],
	win_no_prefer_redirects=False,
	win_private_assemblies=False,
	cipher=block_cipher
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
	pyz,
	a.scripts,
	a.binaries,
	a.zipfiles,
	a.datas,
	name='qCSF',
	debug=False,
	strip=False,
	upx=True,
	runtime_tmpdir=None,
	console=False,
	icon='qCSF/assets/icon.ico'
)
'''
	# To tell the difference in frozen vs unfrozen executions
	if getattr(sys, 'frozen', False):
		bundle_dir = sys._MEIPASS
	else:
		bundle_dir = os.path.dirname(os.path.abspath(__file__))
'''
