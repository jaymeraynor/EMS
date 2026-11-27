"""
企業系統集成模塊
支持：SAP、釘釘、企業微信、郵件、Slack 通知
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum
import httpx
import json
from datetime import datetime
import hashlib
import hmac
import base64

# ========== 集成配置 ==========
class IntegrationConfig:
    """集成系統配置"""
    
    # SAP 配置
    SAP_HOST = "https://sap.example.com:443"
    SAP_CLIENT = "100"
    SAP_USER = "energy_api"
    SAP_PASSWORD = "secured_password"
    
    # 釘釘配置
    DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send"
    DINGTALK_APP_KEY = "your_app_key"
    DINGTALK_APP_SECRET = "your_app_secret"
    
    # 企業微信配置
    WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    WECHAT_KEY = "your_key"
    
    # 郵件配置
    EMAIL_SMTP = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USER = "energy@company.com"
    EMAIL_PASSWORD = "email_password"
    
    # Slack 配置
    SLACK_WEBHOOK = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# ========== 數據模型 ==========

class EnergyData(BaseModel):
    """能源數據"""
    building_id: int
    power: float
    cost: float
    co2: float
    timestamp: str

class AlertMessage(BaseModel):
    """告警消息"""
    level: str  # critical, warning, info
    building: str
    message: str
    power: float
    capacity: float
    timestamp: str

class UserNotification(BaseModel):
    """用戶通知"""
    user_id: str
    channel: str  # dingtalk, wechat, email, slack
    message: str
    alert_level: str

# ========== SAP 集成 ==========

class SAPConnector:
    """SAP 系統集成"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        self.session = None
    
    async def connect(self) -> bool:
        """連接到 SAP 系統"""
        try:
            auth = (self.config.SAP_USER, self.config.SAP_PASSWORD)
            headers = {
                'X-CSRF-Token': 'Fetch',
                'Content-Type': 'application/json',
            }
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f"{self.config.SAP_HOST}/sap/opu/odata/sap/API_ENERGY",
                    auth=auth,
                    headers=headers
                )
                return response.status_code in [200, 201]
        except Exception as e:
            print(f"❌ SAP 連接失敗: {e}")
            return False
    
    async def post_energy_data(self, data: EnergyData) -> Dict:
        """發送能源數據到 SAP"""
        try:
            payload = {
                "Building": f"BLD{data.building_id:03d}",
                "Power": round(data.power, 2),
                "Cost": round(data.cost, 2),
                "CO2": round(data.co2, 2),
                "Timestamp": data.timestamp,
            }
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{self.config.SAP_HOST}/sap/opu/odata/sap/API_ENERGY/EnergyReadings",
                    json=payload,
                    auth=(self.config.SAP_USER, self.config.SAP_PASSWORD),
                )
            
            if response.status_code in [200, 201]:
                return {"success": True, "sap_id": response.json().get("ID")}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def sync_energy_report(self, report_data: Dict) -> Dict:
        """同步能源報告到 SAP"""
        try:
            payload = {
                "ReportType": report_data.get("type"),
                "Period": report_data.get("period"),
                "TotalEnergy": report_data.get("total_energy"),
                "TotalCost": report_data.get("total_cost"),
                "Data": json.dumps(report_data.get("details", [])),
            }
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{self.config.SAP_HOST}/sap/opu/odata/sap/API_ENERGY/Reports",
                    json=payload,
                    auth=(self.config.SAP_USER, self.config.SAP_PASSWORD),
                )
            
            return {
                "success": response.status_code in [200, 201],
                "report_id": response.json().get("ID") if response.status_code in [200, 201] else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# ========== 釘釘集成 ==========

class DingTalkNotifier:
    """釘釘機器人通知"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
    
    def _sign_request(self, timestamp: str) -> str:
        """計算簽名"""
        secret = self.config.DINGTALK_APP_SECRET.encode()
        msg = f"{timestamp}\n{self.config.DINGTALK_APP_SECRET}".encode()
        signature = base64.b64encode(
            hmac.new(secret, msg, digestmod='sha256').digest()
        ).decode()
        return signature
    
    async def send_alert(self, alert: AlertMessage) -> bool:
        """發送告警通知到釘釘"""
        try:
            timestamp = str(int(datetime.now().timestamp() * 1000))
            sign = self._sign_request(timestamp)
            
            # 根據嚴重程度設定顏色
            color_map = {
                'critical': '#FF0000',
                'warning': '#FFA500',
                'info': '#0099FF'
            }
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"⚠️ 能源告警 - {alert.building}",
                    "text": f"""## {alert.building} 能源告警

**等級：** {alert.level}

**內容：** {alert.message}

**當前功率：** {alert.power} kW

**容量限制：** {alert.capacity} kW

**負荷率：** {(alert.power/alert.capacity*100):.1f}%

**時間：** {alert.timestamp}

---

[查看詳情](http://energy-platform.com)
"""
                }
            }
            
            params = {
                'access_token': self.config.DINGTALK_APP_KEY,
                'timestamp': timestamp,
                'sign': sign,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.DINGTALK_WEBHOOK,
                    json=payload,
                    params=params,
                )
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 釘釘通知失敗: {e}")
            return False
    
    async def send_daily_report(self, report: Dict) -> bool:
        """發送每日報告到釘釘"""
        try:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "📊 每日能耗報告",
                    "text": f"""# 每日能耗報告 - {report['date']}

## 核心指標

| 指標 | 數值 | 目標 | 達成度 |
|------|------|------|--------|
| 日耗能 | {report['energy']} kWh | 7,500 kWh | {(report['energy']/7500*100):.0f}% |
| 成本 | ¥{report['cost']} | ¥9,000 | {(report['cost']/9000*100):.0f}% |
| 碳排 | {report['co2']} t CO₂ | 4.0 t | {(report['co2']/4.0*100):.0f}% |

## 樓宇排名

1️⃣ A1寫字樓 - 85 kW (正常)
2️⃣ B2數據中心 - 120 kW (警告)
3️⃣ C3生產車間 - 145 kW (超載)

[查看完整報告](http://energy-platform.com/reports)
"""
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.DINGTALK_WEBHOOK}?access_token={self.config.DINGTALK_APP_KEY}",
                    json=payload,
                )
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 報告發送失敗: {e}")
            return False

# ========== 企業微信集成 ==========

class WeChatNotifier:
    """企業微信機器人"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
    
    async def send_alert(self, alert: AlertMessage) -> bool:
        """發送告警到企業微信"""
        try:
            level_emoji = {
                'critical': '🔴',
                'warning': '🟠',
                'info': '🔵'
            }
            
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"""{level_emoji.get(alert.level, '❓')} 能源告警

建築：{alert.building}
內容：{alert.message}
當前功率：{alert.power} kW
容量限制：{alert.capacity} kW
負荷率：{(alert.power/alert.capacity*100):.1f}%
時間：{alert.timestamp}

👉 點擊查看詳情：http://energy-platform.com
"""
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.WECHAT_WEBHOOK}?key={self.config.WECHAT_KEY}",
                    json=payload,
                )
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 企業微信通知失敗: {e}")
            return False

# ========== Slack 集成 ==========

class SlackNotifier:
    """Slack 通知"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
    
    async def send_alert(self, alert: AlertMessage) -> bool:
        """發送告警到 Slack"""
        try:
            color_map = {
                'critical': '#FF0000',
                'warning': '#FFA500',
                'info': '#0099FF'
            }
            
            payload = {
                "attachments": [
                    {
                        "color": color_map.get(alert.level, '#CCCCCC'),
                        "title": f"⚠️ Energy Alert - {alert.building}",
                        "fields": [
                            {
                                "title": "Alert Level",
                                "value": alert.level.upper(),
                                "short": True
                            },
                            {
                                "title": "Current Power",
                                "value": f"{alert.power} kW",
                                "short": True
                            },
                            {
                                "title": "Capacity",
                                "value": f"{alert.capacity} kW",
                                "short": True
                            },
                            {
                                "title": "Load Rate",
                                "value": f"{(alert.power/alert.capacity*100):.1f}%",
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": alert.message,
                                "short": False
                            }
                        ],
                        "footer": "Energy Management Platform",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.SLACK_WEBHOOK,
                    json=payload,
                )
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Slack 通知失敗: {e}")
            return False

# ========== 郵件通知 ==========

class EmailNotifier:
    """郵件通知"""
    
    async def send_alert_email(self, alert: AlertMessage, recipients: List[str]) -> bool:
        """發送告警郵件"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.level.upper()}] 能源告警 - {alert.building}"
            msg['From'] = "energy@company.com"
            msg['To'] = ', '.join(recipients)
            
            html = f"""
<html>
  <body style="font-family: Arial, sans-serif;">
    <h2>⚠️ 能源管理平台告警</h2>
    <table cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
      <tr style="background-color: #f0f0f0;">
        <td style="border: 1px solid #ddd;"><b>建築</b></td>
        <td style="border: 1px solid #ddd;">{alert.building}</td>
      </tr>
      <tr>
        <td style="border: 1px solid #ddd;"><b>告警等級</b></td>
        <td style="border: 1px solid #ddd; color: {'red' if alert.level == 'critical' else 'orange'};">
          {alert.level.upper()}
        </td>
      </tr>
      <tr style="background-color: #f0f0f0;">
        <td style="border: 1px solid #ddd;"><b>當前功率</b></td>
        <td style="border: 1px solid #ddd;">{alert.power} kW</td>
      </tr>
      <tr>
        <td style="border: 1px solid #ddd;"><b>容量限制</b></td>
        <td style="border: 1px solid #ddd;">{alert.capacity} kW</td>
      </tr>
      <tr style="background-color: #f0f0f0;">
        <td style="border: 1px solid #ddd;"><b>負荷率</b></td>
        <td style="border: 1px solid #ddd;">{(alert.power/alert.capacity*100):.1f}%</td>
      </tr>
      <tr>
        <td style="border: 1px solid #ddd;"><b>詳情</b></td>
        <td style="border: 1px solid #ddd;">{alert.message}</td>
      </tr>
      <tr style="background-color: #f0f0f0;">
        <td style="border: 1px solid #ddd;"><b>時間</b></td>
        <td style="border: 1px solid #ddd;">{alert.timestamp}</td>
      </tr>
    </table>
    <br>
    <a href="http://energy-platform.com" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
      查看詳情
    </a>
  </body>
</html>
"""
            
            msg.attach(MIMEText(html, 'html'))
            
            # 發送郵件
            with smtplib.SMTP(IntegrationConfig.EMAIL_SMTP, IntegrationConfig.EMAIL_PORT) as server:
                server.starttls()
                server.login(IntegrationConfig.EMAIL_USER, IntegrationConfig.EMAIL_PASSWORD)
                server.sendmail(IntegrationConfig.EMAIL_USER, recipients, msg.as_string())
            
            return True
        except Exception as e:
            print(f"❌ 郵件發送失敗: {e}")
            return False

# ========== 統一集成管理器 ==========

class EnterpriseIntegrationManager:
    """企業集成管理器"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        self.sap = SAPConnector(config)
        self.dingtalk = DingTalkNotifier(config)
        self.wechat = WeChatNotifier(config)
        self.slack = SlackNotifier(config)
        self.email = EmailNotifier()
    
    async def broadcast_alert(self, alert: AlertMessage, channels: List[str]) -> Dict[str, bool]:
        """廣播告警到多個渠道"""
        results = {}
        
        if 'dingtalk' in channels:
            results['dingtalk'] = await self.dingtalk.send_alert(alert)
        
        if 'wechat' in channels:
            results['wechat'] = await self.wechat.send_alert(alert)
        
        if 'slack' in channels:
            results['slack'] = await self.slack.send_alert(alert)
        
        if 'email' in channels:
            # 需要獲取收件人列表
            results['email'] = await self.email.send_alert_email(alert, ['manager@company.com'])
        
        return results

# ========== FastAPI 路由 ==========

router = APIRouter(prefix="/api/integration", tags=["enterprise-integration"])

@router.post("/sap/post-energy")
async def post_to_sap(data: EnergyData):
    """發送能源數據到 SAP"""
    sap = SAPConnector()
    result = await sap.post_energy_data(data)
    return result

@router.post("/alert/broadcast")
async def broadcast_alert(alert: AlertMessage):
    """廣播告警"""
    manager = EnterpriseIntegrationManager()
    channels = ['dingtalk', 'wechat', 'email']  # 可配置
    results = await manager.broadcast_alert(alert, channels)
    return {"success": all(results.values()), "channels": results}

@router.get("/integration/status")
async def get_integration_status():
    """獲取集成狀態"""
    return {
        "sap": "connected",
        "dingtalk": "active",
        "wechat": "active",
        "slack": "active",
        "email": "active",
        "timestamp": datetime.now().isoformat()
    }
