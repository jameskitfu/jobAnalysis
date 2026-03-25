"""
技能词频统计工具 - Flask Web 应用
提供 CSV 上传、技能分析、Excel 下载功能
"""

import os
import uuid
import traceback
from flask import Flask, request, jsonify, render_template, send_file, url_for
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from services.csv_parser import CSVParser
from services.skill_matcher import SkillMatcher
from services.smart_skill_matcher import SmartSkillMatcher
from services.excel_generator import ExcelGenerator
from services.trend_analyzer import TrendAnalyzer
import threading
import json
from services.llm_service import LLMService
# 新增：LLM 相关服务
from services.extractors import JiebaExtractor, LLMExtractor, HybridExtractor
from services.new_skill_manager import NewSkillManager
from services.cost_tracker import CostTracker

import sys


def get_base_dir():
    """获取应用基础目录（兼容 PyInstaller 打包环境）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，资源文件在临时目录
        return Path(sys._MEIPASS)
    return Path(__file__).parent


# 配置
BASE_DIR = get_base_dir()
TEMPLATE_DIR = BASE_DIR / 'templates'

app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

# 使用 /tmp 目录存放用户上传和输出文件（跨平台可写）
UPLOAD_FOLDER = Path('/tmp/jobAnalysis/uploads')
OUTPUT_FOLDER = Path('/tmp/jobAnalysis/outputs')
CONFIG_PATH = BASE_DIR / 'config' / 'skills.yaml'

# 确保目录存在
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# 限制
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'csv'}

# 初始化技能匹配器（全局单例）
skill_matcher = SkillMatcher(str(CONFIG_PATH))
smart_matcher = SmartSkillMatcher(str(CONFIG_PATH))
trend_analyzer = TrendAnalyzer()

# 新增：LLM 相关服务（延迟初始化，避免 API Key 未配置时报错）
jieba_extractor = None
llm_extractor = None
hybrid_extractor = None
new_skill_manager = NewSkillManager(str(CONFIG_PATH))
cost_tracker = CostTracker()

# 新增：进度状态记录存储
analysis_progress = {}

def init_llm_extractors(provider='aliyun', api_key=None):
    """初始化 LLM 提取器（延迟加载）"""
    global jieba_extractor, llm_extractor, hybrid_extractor
    
    if jieba_extractor is None:
        jieba_extractor = JiebaExtractor(str(CONFIG_PATH))
    
    # 如果提供了新的 API Key，重新初始化 LLM 提取器
    if api_key:
        try:
            config_dict = {
                'provider': provider,
                'api_key': api_key,
                'model': provider == 'xiaomi' and 'mimo-lite' or 
                         provider == 'deepseek' and 'deepseek-chat' or 'qwen-max',
                'timeout': int(os.getenv('LLM_TIMEOUT', '30')),
                'batch_size': int(os.getenv('LLM_MAX_BATCH_SIZE', '10')),
            }
            llm_extractor = LLMExtractor(str(CONFIG_PATH), llm_config=config_dict)
            hybrid_extractor = HybridExtractor(str(CONFIG_PATH), llm_config=config_dict)
        except Exception as e:
            print(f"[WARNING] LLM 初始化失败：{e}")
            llm_extractor = None
            hybrid_extractor = None
    elif llm_extractor is None:
        # 子阶段初始化，尝试从环境变量读取
        try:
            api_key_env = os.getenv('ALIYUN_API_KEY')
            if api_key_env:
                config_dict = {
                    'provider': os.getenv('LLM_PROVIDER', 'aliyun'),
                    'api_key': api_key_env,
                    'model': os.getenv('LLM_MODEL', 'qwen-max'),
                    'timeout': int(os.getenv('LLM_TIMEOUT', '30')),
                    'batch_size': int(os.getenv('LLM_MAX_BATCH_SIZE', '10')),
                }
                llm_extractor = LLMExtractor(str(CONFIG_PATH), llm_config=config_dict)
                hybrid_extractor = HybridExtractor(str(CONFIG_PATH), llm_config=config_dict)
        except Exception as e:
            print(f"[WARNING] LLM 环境初始化失败：{e}")


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def auto_add_new_skills_to_yaml(new_skills_list):
    """将 LLM 发现的新技能安全地以纯文本形式追加到 YAML 文件 hard_skills 节点下，保留原注释"""
    if not new_skills_list:
        return
        
    yaml_path = Path("config") / "skills.yaml"
    if not yaml_path.exists():
        return
        
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        skills_to_add = []
        for ns in new_skills_list:
            skill_name = ns.get('skill', '')
            # 简单的防重判定
            if f"- {skill_name}\n" not in content and f"- {skill_name}\r" not in content:
                skills_to_add.append(ns)
                
        if not skills_to_add:
            return
            
        grouped = {}
        for ns in skills_to_add:
            cat = ns.get('category', 'LLM自动发现')
            if cat not in grouped: grouped[cat] = []
            grouped[cat].append(ns['skill'])
            
        new_yaml_block = "\n  # ==================== LLM 自动发现 ====================\n"
        for cat, skills in grouped.items():
            new_yaml_block += f"  {cat}:\n"
            for s in skills:
                new_yaml_block += f"    - {s}\n"
        new_yaml_block += "\n"
        
        # 将新块插入到 soft_skills 之前
        if 'soft_skills:' in content:
            new_content = content.replace("soft_skills:", new_yaml_block + "soft_skills:")
        elif 'synonyms:' in content:
            new_content = content.replace("synonyms:", new_yaml_block + "synonyms:")
        else:
            new_content = content + new_yaml_block
            
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[LLM] 已自动将 {len(skills_to_add)} 个新技能保存到 skills.yaml")
        
        # 运行时重新加载词库到实例
        global skills_config
        with open(yaml_path, 'r', encoding='utf-8') as f:
            skills_config = yaml.safe_load(f)
            
        # 刷新所有 Extractor
        if llm_config:
            init_llm_extractors(provider=llm_config.get('provider'), api_key=llm_config.get('api_key'))
            
    except Exception as e:
        print(f"[LLM] 自动保存新技能失败: {e}")

@app.route('/test_llm', methods=['POST'])
def test_llm():
    """测试 LLM API 连接性"""
    provider = request.form.get('provider', 'xiaomi')
    api_key = request.form.get('api_key', '').strip()
    
    if not api_key:
        return jsonify({'success': False, 'message': 'API Key 不能为空'})
        
    try:
        service = LLMService(
            provider=provider,
            api_key=api_key,
            timeout=10
        )
        # 用极其简短的文本测试连通性
        res = service.recognize("熟练掌握Java编程", use_cache=False)
        return jsonify({'success': True, 'message': '连接成功！'})
    except Exception as e:
        # 截取错误信息的前 150 个字符
        err_msg = str(e)
        if len(err_msg) > 150:
            err_msg = err_msg[:150] + "..."
        return jsonify({'success': False, 'message': err_msg})

@app.route('/')
def index():
    """渲染首页"""
    return render_template('index.html')


@app.route('/progress')
def get_progress():
    task_id = request.args.get('task_id')
    if not task_id or task_id not in analysis_progress:
        return jsonify({'success': False, 'message': '任务不存在或未开始'})
    return jsonify({'success': True, 'data': analysis_progress[task_id]})


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    处理 CSV 文件上传和分析（支持模式切换：jieba/llm/both）
    """
    # 0. 获取模式与配置
    mode = request.form.get('mode', 'jieba')
    provider = request.form.get('provider', 'aliyun')
    api_key = request.form.get('api_key', '').strip() or None  # 空字符串转 None
    
    # 1. 检查文件
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件格式，请上传 CSV 文件'}), 400
    
    try:
        # 2. 保存文件
        file_id = str(uuid.uuid4())
        original_filename = file.filename
        safe_filename = f"{file_id}_{original_filename}"
        file_path = UPLOAD_FOLDER / safe_filename
        file.save(str(file_path))
        
        # 3. 解析 CSV
        parser = CSVParser(str(file_path))
        if not parser.load():
            return jsonify({'success': False, 'message': 'CSV 文件解析失败，请检查文件格式或编码'}), 400
        
        total_positions = parser.count_rows()
        if total_positions == 0:
            return jsonify({'success': False, 'message': 'CSV 文件为空'}), 400
        
        # 4. 获取职位描述和薪资
        descriptions = parser.get_job_descriptions()
        salaries = parser.get_salaries()
        if not any(descriptions):
            return jsonify({'success': False, 'message': '未找到有效职位描述'}), 400
        sampled = False
        task_id = request.form.get('task_id')
        try:
            llm_limit = int(request.form.get('llm_limit', 500))
        except (ValueError, TypeError):
            llm_limit = 500

        # 5. 模式化提取逻辑
        total_counts = defaultdict(int)
        category_counts = defaultdict(lambda: defaultdict(int))
        skill_salaries = defaultdict(list)
        new_skills = []
        
        if mode == 'jieba':
            def jieba_prog(c, t):
                if task_id: analysis_progress[task_id] = {'step': 1, 'progress': int(c/t*100), 'message': f'Jieba 扫描数据中 ({c}/{t})...'}
            
            tc, cc, css = smart_matcher.count_skills_from_texts(descriptions, use_smart=True, progress_callback=jieba_prog, salaries=salaries)
            total_counts.update(tc)
            for skill, sals in css.items():
                skill_salaries[skill].extend(sals)
            for cat, skills in cc.items():
                for s, count in skills.items():
                    category_counts[cat][s] += count
            if task_id: analysis_progress[task_id] = {'step': 1, 'progress': 100, 'message': '完成'}

        elif mode == 'llm':
            if len(descriptions) > llm_limit:
                import random
                descriptions = random.sample(descriptions, llm_limit)
                sampled = True
                
            if not api_key: return jsonify({'success': False, 'message': '使用大模型必须提供 API Key'}), 400
            init_llm_extractors(provider=provider, api_key=api_key)
            if llm_extractor is None: return jsonify({'success': False, 'message': 'LLM 初始化失败'}), 503
            
            def llm_prog(c, t):
                if task_id: analysis_progress[task_id] = {'step': 1, 'progress': int(c/t*100), 'message': f'大模型处理中 ({c}/{t})...'}
                
            try:
                results = llm_extractor.extract_batch(descriptions, progress_callback=llm_prog)
            except Exception as e:
                return jsonify({'success': False, 'message': f'大模型调用失败：{e}'}), 502
                
            for i, res in enumerate(results):
                sal_val = smart_matcher.salary_analyzer.parse_annual_salary(salaries[i]) if i < len(salaries) and salaries[i] else None
                for cat, skills in res.standard_skills.items():
                    for s in skills:
                        total_counts[s] += 1
                        category_counts[cat][s] += 1
                        if sal_val is not None:
                            skill_salaries[s].append(sal_val)
                if res.new_skills:
                    new_skills.extend(res.new_skills)
                    
        elif mode == 'both':
            # 混合模式重构（注意维持 descriptions 和 salaries 对齐）
            import random
            combined = list(zip(descriptions, salaries))
            random.shuffle(combined)
            descriptions, salaries = zip(*combined)
            descriptions = list(descriptions)
            salaries = list(salaries)
            
            llm_descs = descriptions[:llm_limit]
            llm_sals = salaries[:llm_limit]
            jieba_descs = descriptions[llm_limit:] # 剩余的
            jieba_sals = salaries[llm_limit:]
            
            if not api_key: return jsonify({'success': False, 'message': '使用大模型必须提供 API Key'}), 400
            init_llm_extractors(provider=provider, api_key=api_key)
            if llm_extractor is None: return jsonify({'success': False, 'message': 'LLM 初始化失败'}), 503
            
            def both_llm_prog(c, t):
                if task_id: analysis_progress[task_id] = {'step': 1, 'progress': int(c/t*100), 'message': f'启动大模型探索新词 ({c}/{t})...'}
                
            try:
                results = llm_extractor.extract_batch(llm_descs, progress_callback=both_llm_prog)
            except Exception as e:
                return jsonify({'success': False, 'message': f'大模型调用失败：{e}'}), 502
                
            # 收集 LLM 发现的新词和统计
            for i, res in enumerate(results):
                sal_val = smart_matcher.salary_analyzer.parse_annual_salary(llm_sals[i]) if i < len(llm_sals) and llm_sals[i] else None
                for cat, skills in res.standard_skills.items():
                    for s in skills:
                        total_counts[s] += 1
                        category_counts[cat][s] += 1
                        if sal_val is not None:
                            skill_salaries[s].append(sal_val)
                if res.new_skills:
                    new_skills.extend(res.new_skills)
                    
            # 立即写入新词并重载底层匹配器
            if new_skills:
                new_skills_map = {}
                for s in new_skills:
                    # 记录待审批
                    new_skill_manager.add_candidate(s)
                    if s.skill not in new_skills_map:
                        new_skills_map[s.skill] = s.to_dict()
                    else:
                        new_skills_map[s.skill]['frequency'] += 1
                unique_new_skills = list(new_skills_map.values())
                
                # 同步执行保存，并立即重载 Jieba 词典以确保下面的操作能匹配到
                auto_add_new_skills_to_yaml(unique_new_skills)
                smart_matcher.reload()
            
            # 使用 Jieba 提取剩余数据
            if jieba_descs:
                def both_jieba_prog(c, t):
                    if task_id: analysis_progress[task_id] = {'step': 2, 'progress': int(c/t*100), 'message': f'Jieba 扫描剩余数据 ({c}/{t})...'}
                
                jc, jcat, jss = smart_matcher.count_skills_from_texts(jieba_descs, use_smart=True, progress_callback=both_jieba_prog, salaries=jieba_sals)
                for s, count in jc.items():
                    total_counts[s] += count
                for skill, sals in jss.items():
                    skill_salaries[skill].extend(sals)
                for cat, skills in jcat.items():
                    for s, count in skills.items():
                        category_counts[cat][s] += count
                        
            if task_id: analysis_progress[task_id] = {'step': 2, 'progress': 100, 'message': '全量分析完成'}
        
        # 将 defaultdict 转换为普通 dict
        total_counts = dict(total_counts)
        category_counts = {k: dict(v) for k, v in category_counts.items()}
        
        if mode != 'both' and new_skills:
            # LLM单模式后台异步保存新技能
            for s in new_skills: new_skill_manager.add_candidate(s)
            
            new_skills_map = {}
            for s in new_skills:
                if s.skill not in new_skills_map:
                    new_skills_map[s.skill] = s.to_dict()
                else:
                    new_skills_map[s.skill]['frequency'] += 1
            unique_new_skills = list(new_skills_map.values())
            threading.Thread(target=auto_add_new_skills_to_yaml, args=(unique_new_skills,)).start()
            
            # 对于纯 LLM 模式，如果没有标准技能，借用新技能防空白
            if not total_counts:
                for ns_item in unique_new_skills:
                    total_counts[ns_item['skill']] = ns_item.get('frequency', 1)
                    cat = ns_item.get('category', '新发现技能')
                    if cat not in category_counts:
                        category_counts[cat] = {}
                    category_counts[cat][ns_item['skill']] = ns_item.get('frequency', 1)

        if not total_counts:
            return jsonify({'success': False, 'message': '未匹配到任何技能词'}), 400
            
        # 针对每个技能计算平均薪资（样本数 >= 3 才计算，避免个例干扰）
        skill_avg_salary = {}
        for skill, sals in skill_salaries.items():
            if len(sals) >= 3:
                skill_avg_salary[skill] = round(sum(sals) / len(sals), 2)

        
        # 6. 趋势分析
        dates = parser.get_dates()
        has_trend = any(d is not None for d in dates)
        trend_data = {}
        summary_data = []
        detail_data = []
        
        if has_trend:
            period_indices = trend_analyzer.group_by_period(dates, period_type='month')
            skill_counts_by_period = {}
            total_periods = len(period_indices)
            
            for idx, (period, indices) in enumerate(period_indices.items()):
                period_descs = [descriptions[i] for i in indices if i < len(descriptions)]
                
                # 为趋势分析增加进度展示 (Step 3)
                def trend_prog(c, t):
                    if task_id: 
                        p = int((idx + c/t) / max(1, total_periods) * 100)
                        analysis_progress[task_id] = {'step': 3, 'progress': p, 'message': f'生成趋势分析 ({idx+1}/{total_periods})...'}
                
                pc, _ = smart_matcher.count_skills_from_texts(period_descs, use_smart=True, progress_callback=trend_prog)
                skill_counts_by_period[period] = pc
            
            if task_id: analysis_progress[task_id] = {'step': 3, 'progress': 100, 'message': '正在生成 Excel 报表...'}
            
            trend_data = trend_analyzer.analyze_trend(skill_counts_by_period, top_n=20)
            summary_data, detail_data = trend_analyzer.prepare_excel_trend_data(skill_counts_by_period)
        
        # 7. 生成 Excel
        if task_id and not has_trend:
            analysis_progress[task_id] = {'step': 3, 'progress': 100, 'message': '正在生成 Excel 报表...'}
            
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
                skill_avg_salary=skill_avg_salary,
                output_path=str(output_path),
                source_file=original_filename,
                total_positions=total_positions
            )
        else:
            generator.generate(
                total_counts=total_counts,
                category_counts=category_counts,
                skill_avg_salary=skill_avg_salary,
                output_path=str(output_path),
                source_file=original_filename,
                total_positions=total_positions
            )
        
        # 8. 准备返回
        top_skills_sorted = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        response_data = {
            'filename': original_filename,
            'output_filename': output_filename,
            'download_url': url_for('download_file', filename=output_filename),
            'total_positions': total_positions,
            'total_skills': len(total_counts),
            'top_skills': [{'skill': s, 'count': c, 'avg_salary': skill_avg_salary.get(s)} for s, c in top_skills_sorted],
            'has_trend': has_trend,
            'mode': mode,
            'new_skills': new_skills[:20]
        }
        
        return jsonify({
            'success': True,
            'message': f'分析完成！模式：{mode}，共分析 {total_positions} 个职位' + ('（大模型限制已抽样300条）' if sampled else ''),
            'data': response_data
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'处理失败：{str(e)}'}), 500


@app.route('/download/<filename>')
def download_file(filename: str):
    """下载生成的 Excel 文件"""
    file_path = OUTPUT_FOLDER / filename
    if not file_path.exists():
        return jsonify({'success': False, 'message': '文件不存在或已过期'}), 404
    return send_file(str(file_path), as_attachment=True, download_name=filename)


@app.route('/cleanup', methods=['POST'])
def cleanup():
    """清理临时文件"""
    cleaned = 0
    now = datetime.now()
    for d in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for f in d.iterdir():
            if f.is_file():
                if d == UPLOAD_FOLDER or (now - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() > 3600:
                    f.unlink()
                    cleaned += 1
    return jsonify({'success': True, 'message': f'清理了 {cleaned} 个文件'})


@app.route('/api/new-skills', methods=['GET'])
def get_new_skills():
    """获取待审核的新技能列表"""
    status = request.args.get('status', 'pending')
    skills = new_skill_manager.get_pending_list(status)
    return jsonify({
        'success': True,
        'data': {
            'skills': skills,
            'statistics': new_skill_manager.get_statistics(),
        }
    })


@app.route('/api/new-skills/<int:skill_id>', methods=['POST'])
def review_new_skill(skill_id):
    """审核新技能"""
    data = request.get_json()
    if not data: return jsonify({'success': False, 'message': '请求数据为空'}), 400
    action = data.get('action')
    note = data.get('note', '')
    if action == 'approve':
        category = data.get('category')
        if not category: return jsonify({'success': False, 'message': '批准时必须指定类别'}), 400
        if new_skill_manager.approve_skill(skill_id, category, note):
            return jsonify({'success': True, 'message': '技能已批准'})
        return jsonify({'success': False, 'message': '技能 ID 不存在'}), 404
    elif action == 'reject':
        if new_skill_manager.reject_skill(skill_id, note):
            return jsonify({'success': True, 'message': '技能已拒绝'})
        return jsonify({'success': False, 'message': '技能 ID 不存在'}), 404
    return jsonify({'success': False, 'message': f'不支持的操作：{action}'}), 400


@app.route('/api/cost-stats', methods=['GET'])
def get_cost_stats():
    """获取成本统计信息"""
    budget = float(request.args.get('budget', '300'))
    return jsonify({
        'success': True,
        'data': {
            'stats': cost_tracker.get_statistics(),
            'budget_usage': cost_tracker.get_budget_usage(budget),
            'trend': cost_tracker.get_trend(days=7),
        }
    })


@app.route('/api/extractor-test', methods=['POST'])
def test_extractor():
    """测试提取器"""
    data = request.get_json()
    if not data: return jsonify({'success': False, 'message': '请求数据为空'}), 400
    text, mode, provider, api_key = data.get('text', ''), data.get('mode', 'jieba'), data.get('provider', 'aliyun'), data.get('api_key')
    if not text: return jsonify({'success': False, 'message': '测试文本不能为空'}), 400
    if mode in ['llm', 'both'] and not api_key:
        return jsonify({'success': False, 'message': 'LLM 模式必须提供 API Key'}), 400
    try:
        if mode == 'jieba':
            init_llm_extractors()
            result = jieba_extractor.extract(text)
        elif mode == 'llm':
            init_llm_extractors(provider=provider, api_key=api_key)
            if not llm_extractor: return jsonify({'success': False, 'message': 'LLM 初始化失败'}), 503
            result = llm_extractor.extract(text)
        elif mode == 'both':
            init_llm_extractors(provider=provider, api_key=api_key)
            if not hybrid_extractor: return jsonify({'success': False, 'message': '混合提取器初始化失败'}), 503
            result = hybrid_extractor.extract(text)
        else: return jsonify({'success': False, 'message': f'不支持的模式：{mode}'}), 400
        return jsonify({'success': True, 'data': result.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': f'测试失败：{str(e)}'}), 500


def start_server(port=5001):
    """启动 Flask 服务（供桌面模式调用）"""
    app.run(debug=False, host='127.0.0.1', port=port, use_reloader=False)


if __name__ == '__main__':
    print("=" * 50)
    print("技能词频统计工具")
    print("访问地址：http://localhost:5001")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5001)
