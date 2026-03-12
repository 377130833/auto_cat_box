from flask import Flask, render_template_string, jsonify
import requests
import json
import os

app = Flask(__name__)

# ================= 1. OneNet API 配置 =================
PRODUCT_ID = "zJsLok5Lw5"
DEVICE_NAME = "test"
# 这里的 Authorization 需要填入你在 OneNet 平台生成的 Token (建议用长期有效的 API Key)
AUTHORIZATION = "version=2018-10-31&res=products%2FzJsLok5Lw5%2Fdevices%2Ftest&et=2810373514&method=md5&sign=xDs4xNuxlZp8k32wXLpqWg%3D%3D" 

@app.route('/')
def index():
    # ================= 2. 获取设备属性 (页面加载时) =================
    url = f"https://iot-api.heclouds.com/thingmodel/query-device-property?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"
    headers = {
        "authorization": AUTHORIZATION
    }
    
    temp_value = "--"
    error_msg = ""
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        res_data = response.json()
        
        if res_data.get("code") == 0:
            properties = res_data.get("data", [])
            for prop in properties:
                if prop.get("identifier") == "temp": 
                    temp_value = prop.get("value")
                    break
        else:
            error_msg = f"OneNet 报错: {res_data.get('msg')}"
    except Exception as e:
        error_msg = f"网络请求异常: {str(e)}"

    # ================= 3. 前端 HTML 模板 (含 JS 异步交互) =================
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>自动猫砂盆控制台</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; width: 320px; }
            h2 { color: #333; margin-top: 0; }
            .temp-value { font-size: 64px; font-weight: bold; color: #ff6b6b; margin: 20px 0; }
            .unit { font-size: 24px; color: #888; }
            .footer { margin-top: 25px; font-size: 14px; color: #999; }
            .error { color: red; font-size: 14px; }
            
            /* 按钮排版 */
            .button-group { display: flex; justify-content: space-between; gap: 10px; margin-top: 20px; }
            button { flex: 1; color: white; border: none; padding: 12px 15px; border-radius: 8px; cursor: pointer; font-size: 16px; transition: 0.3s; font-weight: bold;}
            button:disabled { background-color: #cccccc !important; cursor: not-allowed; }
            
            .btn-refresh { background-color: #008CBA; }
            .btn-refresh:hover:not(:disabled) { background-color: #007399; }
            
            .btn-action { background-color: #FF9800; }
            .btn-action:hover:not(:disabled) { background-color: #e68a00; }
            
            /* 状态反馈提示语 */
            #status-msg { margin-top: 15px; font-size: 14px; min-height: 20px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>猫砂盆环境状态</h2>
            
            {% if error %}
                <p class="error">{{ error }}</p>
            {% else %}
                <div class="temp-value">{{ temp }}<span class="unit">°C</span></div>
            {% endif %}
            
            <div class="button-group">
                <button class="btn-refresh" onclick="location.reload()">刷新状态</button>
                <button id="cleanBtn" class="btn-action" onclick="sendCleanCommand()">一键铲屎</button>
            </div>
            
            <div id="status-msg"></div>

            <div class="footer">数据来源于中国移动 OneNet</div>
        </div>

        <script>
            function sendCleanCommand() {
                const btn = document.getElementById('cleanBtn');
                const msgBox = document.getElementById('status-msg');
                
                // 1. 发送前：禁用按钮，防止连续点击，显示发送中
                btn.disabled = true;
                btn.innerText = "发送中...";
                msgBox.style.color = "#666";
                msgBox.innerText = "正在下发指令...";

                // 2. 发起异步 POST 请求到我们后端的 /clean 接口
                fetch('/clean', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    // 3. 处理后端返回的结果
                    if (data.status === 'success') {
                        msgBox.style.color = "green";
                        msgBox.innerText = "✔️ " + data.msg;
                    } else {
                        msgBox.style.color = "red";
                        msgBox.innerText = "❌ " + data.msg;
                    }
                })
                .catch(error => {
                    msgBox.style.color = "red";
                    msgBox.innerText = "❌ 发生异常，请检查网络";
                })
                .finally(() => {
                    // 4. 无论成功失败，恢复按钮状态
                    btn.disabled = false;
                    btn.innerText = "一键铲屎";
                    
                    // 3秒后自动清除提示信息
                    setTimeout(() => {
                        msgBox.innerText = "";
                    }, 3000);
                });
            }
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html_template, temp=temp_value, error=error_msg)


@app.route('/clean', methods=['POST'])
def send_clean_cmd():
    # ================= 4. 处理前端发来的下发指令请求 =================
    url = "https://iot-api.heclouds.com/thingmodel/set-device-property"
    headers = {
        "authorization": AUTHORIZATION,
        "content-type": "application/json"
    }
    
    # 构造 OneNet 要求的 JSON 格式
    payload = {
        "product_id": PRODUCT_ID,
        "device_name": DEVICE_NAME,
        "params": {
            "clean_cmd": "1"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        res_data = response.json()
        
        if res_data.get("code") == 0:
            return jsonify({"status": "success", "msg": "命令发送成功！"})
        else:
            return jsonify({"status": "error", "msg": f"云端异常: {res_data.get('msg')}"})
            
    except Exception as e:
        return jsonify({"status": "error", "msg": f"请求超时或失败"})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)