# FoodControlPlanNZ

Auckland FCP(Food Control Plan) 감사(verification) 대비용 문제집 웹앱.

## 로컬 실행
```
cd backend
pip install -r requirements.txt
python app.py
```
http://localhost:5000 접속

## 배포 (Render)
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
- Environment Variables:
  - `FCP_QUIZ_ACCESS_CODE` = (매장 보호코드, 8자리+특수문자)
  - `FCP_QUIZ_SECRET_KEY` = (임의의 랜덤 문자열)

## 접속 코드 변경
`FCP_QUIZ_ACCESS_CODE` 환경변수만 바꾸면 코드가 바로 바뀝니다. app.py 수정 불필요.
