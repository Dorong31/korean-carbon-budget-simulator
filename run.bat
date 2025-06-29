@echo off
echo ========================================
echo 한국 탄소중립 경로 시뮬레이터 v2.0
echo ========================================
echo.

echo Python 패키지 설치 중...
pip install -r requirements.txt

echo.
echo 서버 시작 중...
echo 브라우저에서 http://localhost:5000 으로 접속하세요.
echo.
echo 종료하려면 Ctrl+C를 누르세요.
echo.

python NetZero-Simulator_v2.0.py

pause 