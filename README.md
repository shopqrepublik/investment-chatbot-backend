# 🧠 Investment Chatbot Backend

FastAPI backend for investment analytics and portfolio forecasting.

## 🚀 Features
- Portfolio growth forecast via ML model  
- Ticker analytics and EOD data integration  
- API endpoints (Swagger UI at `/docs`)

## 🧩 Endpoints
- `POST /api/v1/forecast/portfolio` — forecast portfolio growth  
- `GET /api/v1/tickers` — list available tickers  
- `GET /api/v1/health` — system status  

## ⚙️ Installation
```bash
git clone https://github.com/shopqrepublik/investment-chatbot-backend.git
cd investment-chatbot-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
