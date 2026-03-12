from flask import Flask, render_template_string
import requests
import json

app = Flask(__name__)

# ================= 1. OneNet API 配置 =================
PRODUCT_ID = "zJsLok5Lw5"
DEVICE_NAME = "test"
# 这里的 Authorization 需要填入你在 OneNet 平台生成的 Token (建议用长期有效的 API Key)
AUTHORIZATION = "version=2018-10-31&res=products%2FzJsLok5Lw5%2Fdevices%2Ftest&et=2810373514&method=md5&sign=xDs4xNuxlZp8k32wXLpqWg%3D%3D" 

@app.route('/')
def index():
    # ================= 2. 获取设备属性 =================
    url = f"https://iot-api.heclouds.com/thingmodel/query-device-property?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"
    headers = {
        "authorization": AUTHORIZATION
    }
    
    temp_value = "--"
    error_msg = ""
    
    try:
        # 发送 GET 请求到 OneNet 平台
        response = requests.get(url, headers=headers, timeout=5)
        res_data = response.json()
        
        # 解析返回的数据
        if res_data.get("code") == 0:
            # OneNet 的返回数据通常是一个列表，里面包含各个属性的字典
            properties = res_data.get("data", [])
            for prop in properties:
                if prop.get("identifier") == "temp": # 假设你在物模型里定义的温度标识符是 temp
                    temp_value = prop.get("value")
                    break
        else:
            error_msg = f"OneNet 报错: {res_data.get('msg')}"
    except Exception as e:
        error_msg = f"网络请求异常: {str(e)}"

    # ================= 3. 极简的前端 HTML 模板 =================
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>智能设备控制台</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; width: 300px; }
            h2 { color: #333; margin-top: 0; }
            .temp-value { font-size: 64px; font-weight: bold; color: #ff6b6b; margin: 20px 0; }
            .unit { font-size: 24px; color: #888; }
            .footer { margin-top: 20px; font-size: 14px; color: #999; }
            .error { color: red; font-size: 14px; }
            button { background-color: #4caf50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; transition: 0.3s; }
            button:hover { background-color: #45a049; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>当前设备温度</h2>
            
            {% if error %}
                <p class="error">{{ error }}</p>
            {% else %}
                <div class="temp-value">{{ temp }}<span class="unit">°C</span></div>
            {% endif %}
            
            <button onclick="location.reload()">刷新数据</button>
            <div class="footer">数据来源于中国移动 OneNet</div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_template, temp=temp_value, error=error_msg)

if __name__ == '__main__':
    # 绑定 0.0.0.0 适应服务器环境，端口设置 8080
    app.run(host='0.0.0.0', port=8080)