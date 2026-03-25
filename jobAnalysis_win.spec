# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - Windows 版
用法：pyinstaller jobAnalysis_win.spec
"""

import os

block_cipher = None
PROJECT_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['desktop.py'],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[
        ('config/skills.yaml', 'config'),
        ('config/prompt_templates.yaml', 'config'),
        ('config/llm_providers.yaml', 'config'),
        ('templates/index.html', 'templates'),
    ],
    hiddenimports=[
        'flask', 'jinja2', 'werkzeug',
        'pandas', 'openpyxl', 'yaml', 'chardet', 'jieba', 'xlsxwriter',
        'numpy', 'numpy.core._multiarray_tests', 'numpy.core._multiarray_umath',
        'services.csv_parser', 'services.skill_matcher',
        'services.smart_skill_matcher', 'services.excel_generator',
        'services.trend_analyzer', 'services.salary_analyzer',
        'services.llm_service', 'services.new_skill_manager',
        'services.cost_tracker', 'services.extractors',
        'services.extractors.jieba_extractor', 'services.extractors.llm_extractor',
        'services.extractors.hybrid_extractor', 'services.extractors.base_extractor',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'tkinter',
        'sphinx', 'black', 'pytest', 'bokeh',
        'IPython', 'notebook', 'nbconvert', 'nbformat', 'jedi', 'parso',
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SkillAnalyzer',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,  # 可替换为 .ico 图标
)
