import os
# 항상 app.py가 있는 폴더에서 실행되도록 현재 작업 디렉토리 변경
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import json
from datetime import datetime, date
import math

app = Flask(__name__, static_folder='static')
app.secret_key = 'your-secret-key-change-this-in-production'  # 세션을 위한 시크릿 키

# 통계 파일 경로
STATS_FILE = 'stats.json'

def load_stats():
    """통계 데이터 로드"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_stats(stats):
    """통계 데이터 저장"""
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def increment_visit_count():
    """오늘 방문자 수 증가"""
    stats = load_stats()
    today = date.today().isoformat()
    
    # 디버깅을 위한 로그 추가
    print(f"DEBUG: Today's date: {today}")
    print(f"DEBUG: Current stats: {stats}")
    
    if today not in stats:
        stats[today] = {'visits': 0}
    
    stats[today]['visits'] += 1
    print(f"DEBUG: Updated stats: {stats}")
    save_stats(stats)

@app.route('/')
def index():
    """메인 페이지 - 방문자 수 증가"""
    increment_visit_count()
    return render_template('index.html', app_name='한국 탄소중립 경로 시뮬레이터', version='2.0')

@app.route('/admin')
def admin():
    """관리자 페이지"""
    if 'admin_logged_in' not in session:
        return render_template('admin_login.html')
    
    stats = load_stats()
    today = date.today().isoformat()
    
    # 최대 방문자 수 계산 (비율 표시용)
    max_visits = 0
    if stats:
        max_visits = max(data['visits'] for data in stats.values())
    
    return render_template('admin_stats.html', stats=stats, today=today, max_visits=max_visits)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """관리자 로그인"""
    password = request.form.get('password')
    # 간단한 비밀번호 (실제 운영 시에는 더 안전한 방법 사용)
    if password == 'turntable2025':
        session['admin_logged_in'] = True
        return redirect(url_for('admin'))
    else:
        return render_template('admin_login.html', error='비밀번호가 올바르지 않습니다.')

@app.route('/admin/logout')
def admin_logout():
    """관리자 로그아웃"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin'))

@app.route('/calculate', methods=['POST'])
def calculate():
    """시나리오 계산"""
    try:
        data = request.get_json()
        
        budget = float(data['budget'])
        target_year = int(data['target_year'])
        r35 = float(data['r35'])
        r40 = float(data['r40'])
        r45 = float(data['r45'])
        
        # 고정 데이터 (2018-2030)
        fixed_data = {
            2018: 6.591, 2019: 6.361, 2020: 5.874, 2021: 6.131,
            2022: 5.974, 2023: 5.995, 2024: 5.912, 2025: 5.841,
            2026: 5.702, 2027: 5.533, 2028: 5.302, 2029: 5.008, 2030: 4.129
        }
        
        base_emission = 6.591  # 2018년 기준 배출량
        
        # 목표값 설정
        targets = {
            2030: fixed_data[2030],
            2035: base_emission * (1 - r35 / 100),
            2040: base_emission * (1 - r40 / 100),
            2045: base_emission * (1 - r45 / 100),
            target_year: 0
        }
        
        # 시나리오 계산 (2030년부터)
        scenario_data = []
        for year in range(2030, target_year + 1):
            if year <= 2035:
                # 2030-2035: 선형 보간
                value = targets[2030] + (targets[2035] - targets[2030]) * ((year - 2030) / 5)
            elif year <= 2040:
                # 2035-2040: 선형 보간
                value = targets[2035] + (targets[2040] - targets[2035]) * ((year - 2035) / 5)
            elif year <= 2045:
                # 2040-2045: 선형 보간
                value = targets[2040] + (targets[2045] - targets[2040]) * ((year - 2040) / 5)
            else:
                # 2045-목표연도: 선형 감소
                value = targets[2045] * (1 - ((year - 2045) / (target_year - 2045)))
            
            # 사용자가 조절하는 해의 점 크기 결정
            key_years = [2035, 2040, 2045, target_year]
            marker_size = 9 if year in key_years else 6  # 1.5배 크기
            
            scenario_data.append({'year': year, 'value': value, 'marker_size': marker_size})
        
        # 전체 데이터 생성 (2018-목표연도)
        all_data = []
        
        # 고정 데이터 추가 (2018-2030)
        for year in range(2018, 2030):
            all_data.append({'year': year, 'value': fixed_data[year]})
        
        # 시나리오 데이터 추가 (2030-목표연도)
        all_data.extend(scenario_data)
        
        # 누적 배출량 계산 (2020-목표연도)
        emissions_from_2020 = [d['value'] for d in all_data if d['year'] >= 2020]
        total_emission = sum(emissions_from_2020)
        over_emission = max(0, total_emission - budget)
        
        # 차트 데이터 생성
        chart_data = {
            'data': [
                {
                    'x': [d['year'] for d in all_data if d['year'] <= 2030],
                    'y': [d['value'] for d in all_data if d['year'] <= 2030],
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': '과거 배출량 및 2030 NDC',
                    'line': {'color': '#2E86AB', 'width': 3},
                    'marker': {'size': 6}
                },
                {
                    'x': [d['year'] for d in all_data if d['year'] >= 2030],
                    'y': [d['value'] for d in all_data if d['year'] >= 2030],
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': '탄소예산 경로',
                    'line': {'color': '#A23B72', 'width': 3},
                    'marker': {
                        'size': [d.get('marker_size', 6) for d in all_data if d['year'] >= 2030],
                        'color': '#A23B72'
                    }
                }
            ],
            'layout': {
                'xaxis': {'title': '연도'},
                'yaxis': {'title': '배출량 (억tCO₂)'},
                'hovermode': 'closest',
                'showlegend': True,
                'legend': {
                    'x': 0.95,
                    'y': 0.95,
                    'xanchor': 'right',
                    'yanchor': 'top',
                    'bgcolor': 'rgba(255,255,255,0.8)',
                    'bordercolor': 'rgba(0,0,0,0.2)',
                    'borderwidth': 1
                },
                'plot_bgcolor': 'rgba(0,0,0,0)',
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'margin': {'l': 60, 'r': 40, 't': 40, 'b': 60}
            }
        }
        
        result = {
            'scenario': {
                'budget': budget,
                'target_year': target_year,
                'r35': r35,
                'r40': r40,
                'r45': r45
            },
            'total_emission': round(total_emission, 3),
            'over_emission': round(over_emission, 3),
            'chart': json.dumps(chart_data),
            'all_data': all_data
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/save_scenario', methods=['POST'])
def save_scenario():
    """시나리오 저장"""
    try:
        data = request.get_json()
        scenario = data['scenario']
        name = data['name'].strip()
        
        if not name:
            # 이름이 없으면 자동 생성
            name = get_next_scenario_name_util()
        
        # 저장 디렉토리 생성
        os.makedirs('saved_scenarios', exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{name.replace(' ', '_')}.json"
        filepath = os.path.join('saved_scenarios', filename)
        
        # 시나리오 데이터 저장
        scenario_data = {
            'name': name,
            'created_at': datetime.now().isoformat(),
            'settings': scenario
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scenario_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'name': name})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/load_scenarios')
def load_scenarios():
    """저장된 시나리오 목록"""
    try:
        scenarios = []
        if os.path.exists('saved_scenarios'):
            for filename in os.listdir('saved_scenarios'):
                if filename.endswith('.json'):
                    filepath = os.path.join('saved_scenarios', filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        scenarios.append({
                            'filename': filename,
                            'name': data['name'],
                            'created_at': data['created_at']
                        })
        
        # 생성일 기준 내림차순 정렬
        scenarios.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify(scenarios)
        
    except Exception as e:
        return jsonify([])

@app.route('/load_scenario/<filename>')
def load_scenario(filename):
    """특정 시나리오 불러오기"""
    try:
        filepath = os.path.join('saved_scenarios', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({'success': True, 'data': data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_scenario/<filename>', methods=['DELETE'])
def delete_scenario(filename):
    """시나리오 삭제"""
    try:
        filepath = os.path.join('saved_scenarios', filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '파일을 찾을 수 없습니다.'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_next_scenario_name')
def get_next_scenario_name():
    """다음 시나리오 이름 생성"""
    try:
        next_name = get_next_scenario_name_util()
        return jsonify({'next_name': next_name})
    except Exception as e:
        return jsonify({'next_name': '시나리오 1'})

# --- 유틸 함수 추가 ---
def get_next_scenario_name_util():
    scenarios = []
    if os.path.exists('saved_scenarios'):
        for filename in os.listdir('saved_scenarios'):
            if filename.endswith('.json'):
                filepath = os.path.join('saved_scenarios', filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        scenarios.append(data['name'])
                except Exception as e:
                    print(f"파일 읽기 오류: {filepath} - {e}")
    print('현재 시나리오 이름 목록:', scenarios)
    existing_numbers = []
    for name in scenarios:
        if name.startswith('시나리오 '):
            try:
                num = int(name.split(' ')[1])
                existing_numbers.append(num)
            except:
                pass
    if existing_numbers:
        next_num = max(existing_numbers) + 1
    else:
        next_num = 1
    print('다음 시나리오 번호:', next_num)
    return f'시나리오 {next_num}'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 