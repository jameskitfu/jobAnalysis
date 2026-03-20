"""
技能词频统计工具 - Flask Web 应用
提供 CSV 上传、技能分析、Excel 下载功能
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template, send_file, url_for
from pathlib import Path
from datetime import datetime

from services.csv_parser import CSVParser
from services.skill_matcher import SkillMatcher
from services.smart_skill_matcher import SmartSkillMatcher
from services.excel_generator import ExcelGenerator
from services.trend_analyzer import TrendAnalyzer

app = Flask(__name__)

# 配置
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'outputs'
CONFIG_PATH = BASE_DIR / 'config' / 'skills.yaml'

# 确保目录存在
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# 限制
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'csv'}

# 初始化技能匹配器（全局单例）
skill_matcher = SkillMatcher(str(CONFIG_PATH))
smart_matcher = SmartSkillMatcher(str(CONFIG_PATH))
trend_analyzer = TrendAnalyzer()


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """渲染首页"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    处理 CSV 文件上传和分析
    
    返回：
    {
        "success": true/false,
        "message": "提示信息",
        "data": {
            "filename": "原始文件名",
            "output_filename": "输出的 Excel 文件名",
            "total_positions": 职位数，
            "total_skills": 技能词种类数，
            "top_skills": [{"skill": "Java", "count": 100}, ...]
        }
    }
    """
    # 检查文件
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': '未找到上传文件'
        }), 400
    
    file = request.files['file']
    
    print(f"[DEBUG] 收到文件：{file.filename}, 类型：{type(file.filename)}")
    
    if file.filename == '':
        print(f"[DEBUG] 文件名为空")
        return jsonify({
            'success': False,
            'message': '未选择文件'
        }), 400
    
    if not allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        print(f"[DEBUG] 不支持的扩展名：{repr(ext)}")
        return jsonify({
            'success': False,
            'message': '不支持的文件格式，请上传 CSV 文件'
        }), 400
    
    print(f"[DEBUG] 文件验证通过")
    
    try:
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        original_filename = file.filename
        safe_filename = f"{file_id}_{original_filename}"
        file_path = UPLOAD_FOLDER / safe_filename
        
        print(f"[DEBUG] 保存文件到：{file_path}")
        
        # 保存文件
        file.save(str(file_path))
        
        print(f"[DEBUG] 文件已保存，大小：{file_path.stat().st_size} bytes")
        
        # 解析 CSV
        parser = CSVParser(str(file_path))
        if not parser.load():
            print(f"[ERROR] CSV 解析失败")
            return jsonify({
                'success': False,
                'message': 'CSV 文件解析失败，请检查文件格式'
            }), 400
        
        print(f"[DEBUG] CSV 加载成功，行数：{parser.count_rows()}")
        
        # 获取信息
        columns_info = parser.get_columns_info()
        total_positions = parser.count_rows()
        
        if total_positions == 0:
            return jsonify({
                'success': False,
                'message': 'CSV 文件为空'
            }), 400
        
        # 获取职位描述文本
        descriptions = parser.get_job_descriptions()
        
        if len(descriptions) == 0:
            return jsonify({
                'success': False,
                'message': '未找到职位描述列，请确保 CSV 包含职位描述相关列'
            }), 400
        
        # 统计技能（使用智能匹配）
        total_counts, category_counts = smart_matcher.count_skills_from_texts(
            descriptions, use_smart=True
        )
        
        if len(total_counts) == 0:
            return jsonify({
                'success': False,
                'message': '未匹配到任何技能词，请检查词库配置或 CSV 内容'
            }), 400
        
        # 趋势分析（如果有日期数据）
        dates = parser.get_dates()
        has_trend = any(d is not None for d in dates)
        
        trend_data = {}
        summary_data = []
        detail_data = []
        
        if has_trend:
            # 按时间段分组统计
            period_indices = trend_analyzer.group_by_period(dates, period_type='month')
            
            skill_counts_by_period = {}
            for period, indices in period_indices.items():
                period_descs = [descriptions[i] for i in indices if i < len(descriptions)]
                period_counts, _ = smart_matcher.count_skills_from_texts(period_descs, use_smart=True)
                skill_counts_by_period[period] = period_counts
            
            # 分析趋势
            trend_data = trend_analyzer.analyze_trend(skill_counts_by_period, top_n=20)
            summary_data, detail_data = trend_analyzer.prepare_excel_trend_data(skill_counts_by_period)
        
        # 生成 Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"skill_stats_{timestamp}.xlsx"
        output_path = OUTPUT_FOLDER / output_filename
        
        generator = ExcelGenerator()
        
        if has_trend and trend_data:
            generator.generate_with_trend(
                total_counts=total_counts,
                category_counts=category_counts,
                trend_data=trend_data,
                summary_data=summary_data,
                detail_data=detail_data,
                output_path=str(output_path),
                source_file=original_filename,
                total_positions=total_positions
            )
        else:
            generator.generate(
                total_counts=total_counts,
                category_counts=category_counts,
                output_path=str(output_path),
                source_file=original_filename,
                total_positions=total_positions
            )
        
        # 准备返回数据
        top_skills = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        response_data = {
            'filename': original_filename,
            'output_filename': output_filename,
            'download_url': url_for('download_file', filename=output_filename),
            'total_positions': total_positions,
            'total_skills': len(total_counts),
            'top_skills': [{'skill': s, 'count': c} for s, c in top_skills],
            'columns_info': columns_info,
            'has_trend': has_trend
        }
        
        if has_trend and trend_data:
            response_data['trend_summary'] = {
                'periods': trend_data.get('periods', []),
                'growth_rates': trend_data.get('growth_rates', {})
            }
        
        return jsonify({
            'success': True,
            'message': f'分析完成！共分析 {total_positions} 个职位，匹配到 {len(total_counts)} 种技能' + 
                      ('，已生成趋势分析报告' if has_trend else ''),
            'data': response_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'处理失败：{str(e)}'
        }), 500


@app.route('/download/<filename>')
def download_file(filename: str):
    """下载生成的 Excel 文件"""
    file_path = OUTPUT_FOLDER / filename
    
    if not file_path.exists():
        return jsonify({
            'success': False,
            'message': '文件不存在或已过期'
        }), 404
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename
    )


@app.route('/cleanup', methods=['POST'])
def cleanup():
    """清理临时文件（可选的维护接口）"""
    cleaned = 0
    
    # 清理 uploads 目录
    for f in UPLOAD_FOLDER.iterdir():
        if f.is_file():
            f.unlink()
            cleaned += 1
    
    # 清理 outputs 目录（保留最近 1 小时的文件）
    now = datetime.now()
    for f in OUTPUT_FOLDER.iterdir():
        if f.is_file():
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            age = (now - mtime).total_seconds()
            if age > 3600:  # 超过 1 小时
                f.unlink()
                cleaned += 1
    
    return jsonify({
        'success': True,
        'message': f'清理了 {cleaned} 个临时文件'
    })


if __name__ == '__main__':
    print("=" * 50)
    print("技能词频统计工具")
    print("=" * 50)
    print(f"配置文件：{CONFIG_PATH}")
    print(f"上传目录：{UPLOAD_FOLDER}")
    print(f"输出目录：{OUTPUT_FOLDER}")
    print("=" * 50)
    print("启动服务...")
    print("访问地址：http://localhost:5001")
    print("=" * 50)
    
    app.run(debug=False, host='0.0.0.0', port=5001)
