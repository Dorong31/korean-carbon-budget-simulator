from flask import Flask, render_template, request, jsonify
import plotly.graph_objects as go
import plotly.utils
import json
import numpy as np
from datetime import datetime
import os
import glob

app = Flask(__name__)

# 버전 정보
VERSION = "2.0"
APP_NAME = "한국 탄소중립 경로 시뮬레이터"

# 기본 데이터
FIXED_DATA = {
    2018: 6.591, 2019: 6.361, 2020: 5.874, 2021: 6.131,
    2022: 5.974, 2023: 5.995, 2024: 5.912, 2025: 5.841,
    2026: 5.702, 2027: 5.533, 2028: 5.302, 2029: 5.008, 2030: 4.129
}

BASE_EMISSION = 6.591  # 2018년 기준 배출량

def calculate_scenario(budget, target_year, r35, r40, r45):
    """시나리오 계산 함수"""
    targets = {
        2030: FIXED_DATA[2030],
        2035: BASE_EMISSION * (1 - r35 / 100),
        2040: BASE_EMISSION * (1 - r40 / 100),
        2045: BASE_EMISSION * (1 - r45 / 100),
        target_year: 0
    }
    
    scenario = []
    for year in range(2030, target_year + 1):
        if year <= 2035:
            value = targets[2030] + (targets[2035] - targets[2030]) * ((year - 2030) / 5)
        elif year <= 2040:
            value = targets[2035] + (targets[2040] - targets[2035]) * ((year - 2035) / 5)
        elif year <= 2045:
            value = targets[2040] + (targets[2045] - targets[2040]) * ((year - 2040) / 5)
        else:
            value = targets[2045] * (1 - ((year - 2045) / (target_year - 2045)))
        scenario.append({'year': year, 'value': value})
    
    return scenario

def create_chart(fixed_data, scenario_data, saved_scenarios=None):
    """Plotly 차트 생성"""
    fig = go.Figure()
    
    # 고정 데이터 (2018-2030)
    fixed_years = list(fixed_data.keys())
    fixed_values = list(fixed_data.values())
    
    fig.add_trace(go.Scatter(
        x=fixed_years,
        y=fixed_values,
        mode='lines+markers',
        name='실제 배출량 (2018-2030)',
        line=dict(color='#2E86AB', width=4),
        marker=dict(size=8),
        hovertemplate='<b>%{x}년</b><br>배출량: %{y:.3f} 억tCO₂<extra></extra>'
    ))
    
    # 사용자 시나리오
    if scenario_data:
        scenario_years = [d['year'] for d in scenario_data]
        scenario_values = [d['value'] for d in scenario_data]
        
        fig.add_trace(go.Scatter(
            x=scenario_years,
            y=scenario_values,
            mode='lines+markers',
            name='탄소중립 경로',
            line=dict(color='#A23B72', width=4),
            marker=dict(size=8),
            hovertemplate='<b>%{x}년</b><br>배출량: %{y:.3f} 억tCO₂<extra></extra>'
        ))
    
    # 저장된 시나리오들
    if saved_scenarios:
        colors = ['#F18F01', '#C73E1D', '#8B5A3C', '#4A90A4', '#7B68EE']
        for i, scenario in enumerate(saved_scenarios):
            years = [d['year'] for d in scenario['data']]
            values = [d['value'] for d in scenario['data']]
            
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                name=scenario['name'],
                line=dict(color=colors[i % len(colors)], width=2, dash='dash'),
                hovertemplate='<b>%{x}년</b><br>배출량: %{y:.3f} 억tCO₂<extra></extra>'
            ))
    
    # 레이아웃 설정
    fig.update_layout(
        title={
            'text': f'{APP_NAME} v{VERSION}',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': '#2C3E50'}
        },
        xaxis_title='연도',
        yaxis_title='배출량 (억tCO₂)',
        plot_bgcolor='white',
        paper_bgcolor='#F8F9FA',
        font=dict(family='Arial, sans-serif', size=14),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=80, r=80, t=100, b=80)
    )
    
    # 그리드 설정
    fig.update_xaxes(
        gridcolor='#E0E0E0',
        gridwidth=1,
        showgrid=True,
        zeroline=False
    )
    fig.update_yaxes(
        gridcolor='#E0E0E0',
        gridwidth=1,
        showgrid=True,
        zeroline=False
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def get_next_scenario_number():
    """다음 시나리오 번호를 가져오는 함수"""
    saved_scenarios_dir = 'saved_scenarios'
    if not os.path.exists(saved_scenarios_dir):
        return 1
    
    # 기존 시나리오 파일들을 확인하여 다음 번호 결정
    existing_files = glob.glob(os.path.join(saved_scenarios_dir, 'scenario_*.json'))
    if not existing_files:
        return 1
    
    # 파일명에서 번호 추출
    numbers = []
    for file in existing_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'scenario_number' in data:
                    numbers.append(data['scenario_number'])
        except:
            continue
    
    return max(numbers) + 1 if numbers else 1

def get_next_scenario_name():
    """다음 시나리오 이름을 가져오는 함수"""
    saved_scenarios_dir = 'saved_scenarios'
    if not os.path.exists(saved_scenarios_dir):
        return "시나리오 1"
    
    # 기존 시나리오 파일들을 확인하여 다음 번호 결정
    existing_files = glob.glob(os.path.join(saved_scenarios_dir, 'scenario_*.json'))
    if not existing_files:
        return "시나리오 1"
    
    # 기존 시나리오 이름들에서 번호 추출
    existing_numbers = []
    for file in existing_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                name = data.get('name', '')
                if name.startswith('시나리오 '):
                    try:
                        number = int(name.split(' ')[1])
                        existing_numbers.append(number)
                    except:
                        continue
        except:
            continue
    
    # 다음 번호 결정
    next_number = max(existing_numbers) + 1 if existing_numbers else 1
    return f"시나리오 {next_number}"

@app.route('/')
def index():
    return render_template('index.html', version=VERSION, app_name=APP_NAME)

@app.route('/get_next_scenario_name', methods=['GET'])
def get_next_scenario_name_api():
    """다음 시나리오 이름을 가져오는 API"""
    next_name = get_next_scenario_name()
    return jsonify({'next_name': next_name})

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    budget = float(data.get('budget', 87.4))
    target_year = int(data.get('target_year', 2050))
    r35 = float(data.get('r35', 50))
    r40 = float(data.get('r40', 70))
    r45 = float(data.get('r45', 85))
    
    # 시나리오 계산
    scenario = calculate_scenario(budget, target_year, r35, r40, r45)
    
    # 전체 데이터 생성 (2018-2050)
    all_data = []
    for year in range(2018, target_year + 1):
        if year in FIXED_DATA:
            all_data.append({'year': year, 'value': FIXED_DATA[year]})
        else:
            scenario_item = next((item for item in scenario if item['year'] == year), None)
            if scenario_item:
                all_data.append(scenario_item)
    
    # 누적 배출량 계산 (2020년부터)
    total_emission = sum(item['value'] for item in all_data if item['year'] >= 2020)
    over_emission = total_emission - budget
    
    # 차트 생성
    chart_json = create_chart(FIXED_DATA, scenario)
    
    return jsonify({
        'scenario': scenario,
        'all_data': all_data,
        'total_emission': round(total_emission, 1),
        'over_emission': round(over_emission, 1),
        'chart': chart_json
    })

@app.route('/save_scenario', methods=['POST'])
def save_scenario():
    data = request.get_json()
    scenario = data.get('scenario', [])
    scenario_name = data.get('name', '').strip()
    
    # saved_scenarios 폴더가 없으면 생성
    saved_scenarios_dir = 'saved_scenarios'
    if not os.path.exists(saved_scenarios_dir):
        os.makedirs(saved_scenarios_dir)
    
    # 시나리오 이름이 없으면 기본값 설정
    if not scenario_name:
        scenario_name = get_next_scenario_name()
    
    # 시나리오 번호 가져오기
    scenario_number = get_next_scenario_number()
    
    # 저장할 데이터 구성
    save_data = {
        'name': scenario_name,
        'scenario_number': scenario_number,
        'created_at': datetime.now().isoformat(),
        'version': VERSION,
        'data': scenario,
        'settings': {
            'budget': data.get('budget', 87.4),
            'target_year': data.get('target_year', 2050),
            'r35': data.get('r35', 50),
            'r40': data.get('r40', 70),
            'r45': data.get('r45', 85)
        }
    }
    
    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scenario_{timestamp}.json"
    filepath = os.path.join(saved_scenarios_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True, 
            'filename': filename,
            'name': scenario_name,
            'scenario_number': scenario_number
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/load_scenarios', methods=['GET'])
def load_scenarios():
    """저장된 시나리오 목록을 가져오는 함수"""
    saved_scenarios_dir = 'saved_scenarios'
    scenarios = []
    
    if not os.path.exists(saved_scenarios_dir):
        return jsonify(scenarios)
    
    # 저장된 시나리오 파일들을 읽어오기
    scenario_files = glob.glob(os.path.join(saved_scenarios_dir, 'scenario_*.json'))
    
    for file in scenario_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                scenarios.append({
                    'filename': os.path.basename(file),
                    'name': data.get('name', 'Unknown'),
                    'created_at': data.get('created_at', ''),
                    'scenario_number': data.get('scenario_number', 0),
                    'version': data.get('version', 'Unknown')
                })
        except Exception as e:
            print(f"Error loading scenario {file}: {e}")
            continue
    
    # 생성일 기준으로 정렬 (최신순)
    scenarios.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify(scenarios)

@app.route('/load_scenario/<filename>', methods=['GET'])
def load_scenario(filename):
    """특정 시나리오를 불러오는 함수"""
    saved_scenarios_dir = 'saved_scenarios'
    filepath = os.path.join(saved_scenarios_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_scenario/<filename>', methods=['DELETE'])
def delete_scenario(filename):
    """시나리오를 삭제하는 함수"""
    saved_scenarios_dir = 'saved_scenarios'
    filepath = os.path.join(saved_scenarios_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    
    try:
        os.remove(filepath)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/version', methods=['GET'])
def get_version():
    """버전 정보를 반환하는 API"""
    return jsonify({
        'version': VERSION,
        'app_name': APP_NAME,
        'description': '한국 탄소중립 경로 시뮬레이터'
    })

if __name__ == '__main__':
    print(f"🚀 {APP_NAME} v{VERSION} 시작 중...")
    print(f"📁 작업 디렉토리: {os.getcwd()}")
    print(f"🌐 서버 주소: http://localhost:5000")
    print(f"📊 저장된 시나리오 폴더: {os.path.join(os.getcwd(), 'saved_scenarios')}")
    print("=" * 50)
    app.run(debug=True, port=5000) 