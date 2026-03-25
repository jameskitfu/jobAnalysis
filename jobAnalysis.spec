# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - 技能词频统计工具
用法：pyinstaller jobAnalysis.spec
"""

import os
import sys

block_cipher = None

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['desktop.py'],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[
        # 配置文件
        ('config/skills.yaml', 'config'),
        ('config/prompt_templates.yaml', 'config'),
        ('config/llm_providers.yaml', 'config'),
        # 前端模板
        ('templates/index.html', 'templates'),
    ],
    hiddenimports=[
        'flask',
        'jinja2',
        'werkzeug',

        'pandas',
        'openpyxl',
        'yaml',
        'chardet',
        'jieba',
        'xlsxwriter',
        'services.csv_parser',
        'services.skill_matcher',
        'services.smart_skill_matcher',
        'services.excel_generator',
        'services.trend_analyzer',
        'services.salary_analyzer',
        'services.llm_service',
        'services.new_skill_manager',
        'services.cost_tracker',
        'services.extractors',
        'services.extractors.jieba_extractor',
        'services.extractors.llm_extractor',
        'services.extractors.hybrid_extractor',
        'services.extractors.base_extractor',
        'numpy',
        'numpy.core._multiarray_tests',
        'numpy.core._multiarray_umath',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'numpy.testing',
        'tkinter',
        'sphinx',
        'black',
        'pytest',
        'bokeh',
        'IPython',
        'notebook',
        'nbconvert',
        'nbformat',
        'jedi',
        'parso',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebChannel',
        'PyQt5.QtNetwork',
        'PyQt5.QtPrintSupport',
        'PyQt5.QtWebEngineCore',
        'webview',
        'pyobjc',
        'objc',
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SkillAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 显示控制台窗口（提示用户服务运行中）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SkillAnalyzer',
)

# macOS .app 打包
app = BUNDLE(
    coll,
    name='技能词频统计工具.app',
    icon=None,  # 可替换为 .icns 图标文件
    bundle_identifier='com.jobanalysis.skilltool',
    info_plist={
        'CFBundleDisplayName': '技能词频统计工具',
        'CFBundleShortVersionString': '1.2.0',
        'NSHighResolutionCapable': True,
    },
)
