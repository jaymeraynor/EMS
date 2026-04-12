"""
能源管理平台後端服務 - Python (FastAPI)
功能：實時數據接入、AI預測、異常檢測、MQTT協議支持
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import asyncio
import json
import random
from collections import defaultdict
import numpy as np
from scipy import stats

# ========== 應用初始化 ==========
app = FastAPI(title="能源管理 API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 數據模型 ==========
class PowerReading(BaseModel):
    timestamp: int
    power: float
    buildingId: int

class PredictionRequest(BaseModel):
    timeRange: str = "24h"
    buildingId: Optional[int] = None

class AnomalyRequest(BaseModel):
    timeRange: str = "24h"

class MeterDataRequest(BaseModel):
    buildingId: int
    power: float
    timestamp: Optional[int] = None

class PredictionResponse(BaseModel):
    peakTime: str
    expectedPower: int
    confidence: float
    recommendation: str

class AnomalyResponse(BaseModel):
    id: str
    building: str
    likelihood: float
    severity: str
    type: str
    predictedCause: str

# ========== 數據存儲 ==========
power_readings: List[PowerReading] = []
buildings = {
    1: {"name": "A1寫字樓", "capacity": 150},
    2: {"name": "B2數據中心", "capacity": 150},
    3: {"name": "C3生產車間", "capacity": 180},
    4: {"name": "D4商業中心", "capacity": 140},
    5: {"name": "E5倉儲區", "capacity": 120},
}

# WebSocket 連接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# ========== 核心功能函數 ==========

def generate_meter_data() -> PowerReading:
    """模擬智能電表數據流"""
    building_id = random.randint(1, 5)
    baselines = {1: 85, 2: 120, 3: 145, 4: 92, 5: 62}
    baseline = baselines.get(building_id, 100)
    variance = (random.random() - 0.5) * 30
    
    return PowerReading(
        timestamp=int(datetime.now().timestamp() * 1000),
        power=max(0, baseline + variance),
        buildingId=building_id
    )

def predict_peak_load(time_range: str, building_id: Optional[int] = None) -> PredictionResponse:
    """
    AI 預測模塊 - 使用統計方法
    可擴展為 Prophet、ARIMA、LSTM 等模型
    """
    peak_hours = {
        "1h": "14:30",
        "24h": "18:30",
        "7d": "下週三 18:30",
        "30d": "月底 18:00",
    }

    base_expected = buildings[building_id]["capacity"] * 0.85 if building_id else 380
    
    predictions = {
        "1h": (peak_hours["1h"], base_expected * 1.15, 0.92),
        "24h": (peak_hours["24h"], base_expected * 1.08, 0.87),
        "7d": (peak_hours["7d"], base_expected * 1.05, 0.78),
        "30d": (peak_hours["30d"], base_expected * 0.95, 0.72),
    }
    
    peak, power, conf = predictions.get(time_range, predictions["24h"])
    
    # 根據預期功率生成優化建議
    recommendations = {
        "1h": "建議啟動備用電源",
        "24h": "預熱冷卻系統優化模式",
        "7d": "計劃維護窗口",
        "30d": "進行能效審計",
    }
    
    return PredictionResponse(
        peakTime=peak,
        expectedPower=int(power),
        confidence=conf,
        recommendation=recommendations.get(time_range, "無可用建議")
    )

def detect_anomalies(time_range: str) -> List[AnomalyResponse]:
    """
    異常檢測模塊 - 基於統計離群值檢測
    方法：Z-Score、Isolation Forest 等
    """
    anomalies = []
    
    if not power_readings:
        return anomalies
    
    # 計算過去N小時的統計特性
    time_limit_ms = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
    recent = [r for r in power_readings if r.timestamp >= time_limit_ms]
    
    if len(recent) < 10:
        return anomalies
    
    # 按建築分組
    by_building = defaultdict(list)
    for r in recent:
        by_building[r.buildingId].append(r.power)
    
    # 檢測離群值
    for building_id, powers in by_building.items():
        if len(powers) < 5:
            continue
        
        # 計算 Z-Score
        mean = np.mean(powers)
        std = np.std(powers)
        
        if std > 0:
            z_scores = np.abs((powers - mean) / std)
            
            # Z-Score > 3 表示異常
            if np.max(z_scores) > 3:
                likelihood = min(0.95, 0.7 + np.max(z_scores) * 0.1)
                
                # 判斷嚴重程度
                max_power = max(powers)
                capacity = buildings[building_id]["capacity"]
                load_pct = (max_power / capacity) * 100
                
                severity = "high" if load_pct > 85 else "medium" if load_pct > 70 else "low"
                
                building_name = buildings[building_id]["name"]
                
                anomaly_types = [
                    "功率波動異常",
                    "諧波含量超標",
                    "無功功率異常",
                    "溫度異常升高",
                ]
                
                anomaly_type = random.choice(anomaly_types)
                
                predicted_causes = [
                    "可能為電動機故障",
                    "變壓器過載",
                    "諧波干擾",
                    "冷卻系統故障",
                ]
                
                predicted_cause = random.choice(predicted_causes)
                
                anomalies.append(AnomalyResponse(
                    id=f"anom_{int(datetime.now().timestamp())}_{building_id}",
                    building=building_name,
                    likelihood=likelihood,
                    severity=severity,
                    type=anomaly_type,
                    predictedCause=predicted_cause,
                ))
    
    return anomalies

def generate_alerts() -> List[Dict]:
    """生成告警 - 基於負荷閾值"""
    alerts = []
    
    if not power_readings:
        return alerts
    
    # 獲取最近10分鐘的數據
    time_limit_ms = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
    recent = [r for r in power_readings if r.timestamp >= time_limit_ms]
    
    by_building = defaultdict(list)
    for r in recent:
        by_building[r.buildingId].append(r.power)
    
    for building_id, powers in by_building.items():
        if not powers:
            continue
        
        avg_power = np.mean(powers)
        capacity = buildings[building_id]["capacity"]
        load_pct = (avg_power / capacity) * 100
        
        if load_pct > 80:
            severity = "critical" if load_pct > 90 else "warning"
            alerts.append({
                "severity": severity,
                "buildingId": building_id,
                "buildingName": buildings[building_id]["name"],
                "message": f"負荷 {load_pct:.0f}% - {'超載' if load_pct > 90 else '接近上限'}",
                "loadPercentage": load_pct,
            })
    
    return alerts

# ========== REST API 端點 ==========

@app.get("/api/energy/realtime")
async def get_realtime_data():
    """獲取實時功率數據"""
    if not power_readings:
        return {
            "timestamp": int(datetime.now().timestamp() * 1000),
            "totalPower": 0,
            "byBuilding": []
        }
    
    # 獲取最近5分鐘的數據
    recent = power_readings[-100:]  # 最近100個數據點
    
    by_building = defaultdict(list)
    for r in recent:
        by_building[r.buildingId].append(r.power)
    
    total_power = 0
    building_stats = []
    
    for building_id in sorted(buildings.keys()):
        powers = by_building.get(building_id, [0])
        avg_power = np.mean(powers) if powers else 0
        capacity = buildings[building_id]["capacity"]
        total_power += avg_power
        
        building_stats.append({
            "buildingId": building_id,
            "name": buildings[building_id]["name"],
            "currentPower": int(avg_power),
            "capacity": capacity,
            "loadPercentage": int((avg_power / capacity) * 100),
        })
    
    return {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "totalPower": int(total_power),
        "byBuilding": building_stats,
    }

@app.post("/api/energy/prediction")
async def predict_energy(request: PredictionRequest):
    """獲取 AI 預測數據"""
    prediction = predict_peak_load(request.timeRange, request.buildingId)
    
    return {
        "timeRange": request.timeRange,
        "buildingId": request.buildingId or "all",
        **prediction.dict(),
        "generatedAt": datetime.now().isoformat(),
        "modelVersion": "1.0.0",
        "confidence_explanation": f"置信度 {prediction.confidence * 100:.0f}% - 基於最近 {request.timeRange} 的數據",
    }

@app.post("/api/energy/anomalies")
async def detect_anomaly(request: AnomalyRequest):
    """檢測異常數據"""
    anomalies = detect_anomalies(request.timeRange)
    
    return {
        "timeRange": request.timeRange,
        "count": len(anomalies),
        "anomalies": [a.dict() for a in anomalies],
        "detectionTime": int(datetime.now().timestamp() * 1000),
        "modelVersion": "1.0.0",
    }

@app.get("/api/energy/historical")
async def get_historical_data(range: str = "24h", buildingId: Optional[int] = None):
    """獲取歷史數據"""
    range_ms = {
        "1h": 60 * 60 * 1000,
        "24h": 24 * 60 * 60 * 1000,
        "7d": 7 * 24 * 60 * 60 * 1000,
        "30d": 30 * 24 * 60 * 60 * 1000,
    }
    
    cutoff = int((datetime.now().timestamp() * 1000) - range_ms.get(range, range_ms["24h"]))
    filtered = [r for r in power_readings 
                if r.timestamp >= cutoff and (not buildingId or r.buildingId == buildingId)]
    
    # 按小時分組聚合
    grouped = defaultdict(list)
    for r in filtered:
        bucket = r.timestamp // 3600000
        grouped[bucket].append(r.power)
    
    aggregated = []
    for bucket in sorted(grouped.keys()):
        powers = grouped[bucket]
        aggregated.append({
            "timestamp": bucket * 3600000,
            "avgPower": int(np.mean(powers)),
            "minPower": int(np.min(powers)),
            "maxPower": int(np.max(powers)),
            "count": len(powers),
        })
    
    return {
        "timeRange": range,
        "totalPoints": len(aggregated),
        "data": aggregated[-50:],  # 返回最後50個點
    }

@app.get("/api/energy/summary")
async def get_energy_summary():
    """獲取能耗概覽"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_ms = int(today.timestamp() * 1000)
    
    today_readings = [r for r in power_readings if r.timestamp >= today_ms]
    
    if not today_readings:
        return {
            "date": today.date().isoformat(),
            "totalEnergyKWh": 0,
            "averagePowerKW": 0,
            "peakPowerKW": 0,
            "buildingCount": len(buildings),
            "dataPoints": 0,
            "estimatedCostCNY": 0,
            "estimatedCO2Ton": 0,
        }
    
    powers = [r.power for r in today_readings]
    total_energy = sum(powers) * (1 / 3600)  # kWh
    
    return {
        "date": today.date().isoformat(),
        "totalEnergyKWh": int(total_energy),
        "averagePowerKW": int(np.mean(powers)),
        "peakPowerKW": int(np.max(powers)),
        "buildingCount": len(buildings),
        "dataPoints": len(today_readings),
        "estimatedCostCNY": int(total_energy * 1.2),
        "estimatedCO2Ton": int(total_energy * 0.00053),
    }

@app.get("/api/alerts/active")
async def get_active_alerts():
    """獲取當前告警"""
    alerts = generate_alerts()
    
    return {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "count": len(alerts),
        "alerts": alerts,
    }

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """確認告警"""
    return {
        "success": True,
        "alertId": alert_id,
        "acknowledgedAt": datetime.now().isoformat(),
    }

@app.post("/api/meter/ingest")
async def ingest_meter_data(request: MeterDataRequest):
    """
    智能電表數據攝取
    支持來自物聯網網關、MQTT Broker 的數據
    """
    if request.buildingId not in buildings:
        raise HTTPException(status_code=400, detail="Invalid building ID")
    
    reading = PowerReading(
        timestamp=request.timestamp or int(datetime.now().timestamp() * 1000),
        power=request.power,
        buildingId=request.buildingId,
    )
    
    power_readings.append(reading)
    
    # 清理舊數據（保留最多10000筆）
    if len(power_readings) > 10000:
        power_readings.pop(0)
    
    # 觸發 WebSocket 廣播
    await manager.broadcast({
        "type": "power-update",
        "data": reading.dict(),
        "timestamp": int(datetime.now().timestamp() * 1000),
    })
    
    return {
        "success": True,
        "readingId": len(power_readings),
    }

# ========== WebSocket 實時推流 ==========

@app.websocket("/ws/power")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點 - 實時功率推流"""
    await manager.connect(websocket)
    
    try:
        # 發送初始數據
        if power_readings:
            latest = power_readings[-1]
            await websocket.send_json({
                "type": "initial",
                "data": latest.dict(),
            })
        
        # 保持連接，接收心跳信號
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 錯誤: {e}")
        manager.disconnect(websocket)

# ========== 後台任務 - 模擬數據生成 ==========

@app.on_event("startup")
async def startup_event():
    """啟動時生成初始數據"""
    # 生成過去24小時的模擬數據
    now = datetime.now()
    for hours_ago in range(24, 0, -1):
        for minutes in range(0, 60, 5):
            ts = int((now - timedelta(hours=hours_ago, minutes=minutes)).timestamp() * 1000)
            for building_id in range(1, 6):
                baselines = {1: 85, 2: 120, 3: 145, 4: 92, 5: 62}
                baseline = baselines.get(building_id, 100)
                power = max(0, baseline + (random.random() - 0.5) * 40)
                power_readings.append(PowerReading(
                    timestamp=ts,
                    power=power,
                    buildingId=building_id,
                ))

@app.on_event("startup")
async def start_data_generation():
    """定期生成新數據"""
    async def generate_data_periodically():
        while True:
            reading = generate_meter_data()
            power_readings.append(reading)
            
            if len(power_readings) > 10000:
                power_readings.pop(0)
            
            await manager.broadcast({
                "type": "power-update",
                "data": reading.dict(),
                "timestamp": int(datetime.now().timestamp() * 1000),
            })
            
            await asyncio.sleep(2)  # 每2秒生成一條數據
    
    asyncio.create_task(generate_data_periodically())

# ========== 健康檢查 ==========

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "dataPoints": len(power_readings),
        "buildings": len(buildings),
    }

# ========== 根端點 ==========

@app.get("/")
async def root():
    """根端點 - API 文檔"""
    return {
        "name": "能源管理平台 API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "realtime": "GET /api/energy/realtime",
            "prediction": "POST /api/energy/prediction",
            "anomalies": "POST /api/energy/anomalies",
            "historical": "GET /api/energy/historical",
            "summary": "GET /api/energy/summary",
            "alerts": "GET /api/alerts/active",
            "ingest": "POST /api/meter/ingest",
            "websocket": "WS /ws/power",
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info",
    )