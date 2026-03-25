#!/bin/bash
# 一键构建桌面应用
# 用法: bash build.sh [mac|win]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "技能词频统计工具 - 桌面版构建"
echo "========================================"

# 清理旧构建
echo "🧹 清理旧构建产物..."
rm -rf build/ dist/

# 检查依赖
echo "🔍 检查打包依赖..."
python -c "import webview" 2>/dev/null || { echo "❌ 请先安装 pywebview: pip install pywebview"; exit 1; }
python -c "import PyInstaller" 2>/dev/null || { echo "❌ 请先安装 pyinstaller: pip install pyinstaller"; exit 1; }

# 执行打包
echo "📦 开始打包（这可能需要几分钟）..."
BUILD_TMP="/tmp/jobAnalysis_build"
DIST_TMP="/tmp/jobAnalysis_dist"
PYI_CONFIG="/tmp/pyinstaller_config"
rm -rf "$BUILD_TMP" "$DIST_TMP" "$PYI_CONFIG"
mkdir -p "$BUILD_TMP" "$DIST_TMP" "$PYI_CONFIG"

export PYINSTALLER_CONFIG_DIR="$PYI_CONFIG"
pyinstaller jobAnalysis.spec --noconfirm --workpath "$BUILD_TMP" --distpath "$DIST_TMP"

# 检查输出并拷贝
if [ -d "$DIST_TMP/技能词频统计工具.app" ]; then
    echo "🚚 正在将应用考回项目目录..."
    mkdir -p dist/
    rm -rf "dist/技能词频统计工具.app"
    cp -R "$DIST_TMP/技能词频统计工具.app" dist/
    
    echo ""
    echo "✅ macOS 应用打包成功！"
    echo "📍 路径: dist/技能词频统计工具.app"
    echo ""
    echo "📏 应用大小:"
    du -sh "dist/技能词频统计工具.app"
    echo ""
    echo "🚀 运行方式: open dist/技能词频统计工具.app"
elif [ -d "$DIST_TMP/技能词频统计工具" ]; then
    echo "🚚 正在将应用考回项目目录..."
    mkdir -p dist/
    rm -rf "dist/技能词频统计工具"
    cp -R "$DIST_TMP/技能词频统计工具" dist/
    
    echo ""
    echo "✅ 打包成功！"
    echo "📍 路径: dist/技能词频统计工具/"
    echo ""
    echo "📏 应用大小:"
    du -sh "dist/技能词频统计工具"
else
    echo "❌ 打包失败，请检查上方错误信息。"
    exit 1
fi
