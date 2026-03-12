from flask import Flask, render_template_string, jsonify
import requests
import json
import os

app = Flask(__name__)

# ================= 1. OneNet API 配置 =================
PRODUCT_ID = "zJsLok5Lw5"
DEVICE_NAME = "test"
AUTHORIZATION = "version=2018-10-31&res=products%2FzJsLok5Lw5%2Fdevices%2Ftest&et=2810373514&method=md5&sign=xDs4xNuxlZp8k32wXLpqWg%3D%3D" 

@app.route('/')
def index():
    # 我们现在需要请求两个不同的 API
    status_url = f"https://iot-api.heclouds.com/device/detail?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"
    prop_url = f"https://iot-api.heclouds.com/thingmodel/query-device-property?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"
    
    headers = {
        "authorization": AUTHORIZATION
    }
    
    # 定义默认值
    temp_value = "--"
    sys_state_text = "获取中..."
    sys_state_color = "#cbd5e0" # 默认灰色
    error_msg = ""
    is_online = False
    
    try:
        # ================= 2.1 核心修复：先获取设备的物理在线状态 =================
        status_res = requests.get(status_url, headers=headers, timeout=5).json()
        if status_res.get("code") == 0:
            # OneNet 返回的 status 字段：1 代表在线，2 代表离线
            dev_status = status_res.get("data", {}).get("status")
            if dev_status == 1:
                is_online = True
                sys_state_text = "等待设备上报..." # 在线，但 STM32 还没发数据时的默认提示
                sys_state_color = "#ecc94b" # 橙黄色警告
            else:
                is_online = False
                sys_state_text = "离线 (设备断网)"
                sys_state_color = "#a0aec0" # 灰色
        
        # ================= 2.2 获取设备物模型属性 (温度等数据) =================
        prop_res = requests.get(prop_url, headers=headers, timeout=5).json()
        if prop_res.get("code") == 0:
            properties = prop_res.get("data", [])
            for prop in properties:
                identifier = prop.get("identifier")
                val = prop.get("value")
                
                # 读取温度 (无论离线在线，都可以显示最后一次的缓存温度)
                if identifier == "temp" and val is not None:
                    try:
                        temp_value = f"{float(val):.1f}"
                    except ValueError:
                        temp_value = str(val)
                        
                # 只有在设备【在线】时，我们才去解析它上报的系统状态
                elif identifier == "system_run_state" and val is not None and is_online:
                    # 兼容 true/1/"true" 各种格式
                    if val is True or str(val).lower() == 'true' or str(val) == '1':
                        sys_state_text = "正常 (运行中)"
                        sys_state_color = "#48bb78"
                    else:
                        sys_state_text = "异常 (运行超时)"
                        sys_state_color = "#e53e3e"
        else:
            if not error_msg: 
                error_msg = f"属性获取失败: {prop_res.get('msg')}"

    except Exception as e:
        error_msg = f"网络请求异常: {str(e)}"

    # ================= 3. 现代化前端 HTML 模板 (与之前完全相同) =================
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>智能猫砂盆控制中心</title>
        <style>
            :root {
                --bg-color: #f4f7f6; --card-bg: #ffffff; --text-main: #2d3748;
                --text-muted: #718096; --primary: #4299e1; --primary-hover: #3182ce;
                --action: #ed8936; --action-hover: #dd6b20;
            }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-color); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .dashboard { background: var(--card-bg); padding: 30px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.06); width: 100%; max-width: 380px; }
            .header { text-align: center; margin-bottom: 25px; }
            .header h2 { margin: 0; font-size: 22px; color: var(--text-main); font-weight: 700; }
            .header p { margin: 5px 0 0; font-size: 13px; color: var(--text-muted); }
            .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px; }
            .data-card { background: #f8fafc; border-radius: 16px; padding: 20px 10px; text-align: center; border: 1px solid #e2e8f0; }
            .data-label { font-size: 13px; color: var(--text-muted); margin-bottom: 10px; font-weight: 500; }
            .data-value { font-size: 32px; font-weight: 700; color: var(--text-main); }
            .data-unit { font-size: 16px; color: var(--text-muted); font-weight: normal; margin-left: 2px; }
            .status-indicator { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 15px; font-weight: 600; height: 38px; }
            .status-dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 8px currentColor; }
            .error-banner { background: #fed7d7; color: #c53030; padding: 12px; border-radius: 12px; text-align: center; font-size: 14px; margin-bottom: 20px; font-weight: 500; }
            .controls { display: flex; flex-direction: column; gap: 12px; }
            button { width: 100%; padding: 16px; border: none; border-radius: 14px; font-size: 16px; font-weight: 600; color: white; cursor: pointer; transition: all 0.2s; }
            button:disabled { opacity: 0.6; cursor: not-allowed; }
            .btn-refresh { background-color: var(--primary); }
            .btn-refresh:hover:not(:disabled) { background-color: var(--primary-hover); }
            .btn-action { background-color: var(--action); }
            .btn-action:hover:not(:disabled) { background-color: var(--action-hover); }
            #status-msg { text-align: center; margin-top: 15px; font-size: 14px; min-height: 20px; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <h2>智能设备管理</h2>
                <p>实时监控与远程控制</p>
            </div>
            {% if error %} <div class="error-banner">{{ error }}</div> {% endif %}
            <div class="grid-container">
                <div class="data-card">
                    <div class="data-label">环境温度</div>
                    <div class="data-value">{{ temp }}<span class="data-unit">°C</span></div>
                </div>
                <div class="data-card">
                    <div class="data-label">设备状态</div>
                    <div class="status-indicator" style="color: {{ sys_state_color }};">
                        <span class="status-dot" style="background-color: {{ sys_state_color }};"></span>
                        {{ sys_state_text }}
                    </div>
                </div>
            </div>
            <div class="controls">
                <button id="cleanBtn" class="btn-action" onclick="sendCleanCommand()">🚀 一键铲屎</button>
                <button class="btn-refresh" onclick="location.reload()">🔄 刷新最新状态</button>
            </div>
            <div id="status-msg"></div>
        </div>

        <script>
            function sendCleanCommand() {
                const btn = document.getElementById('cleanBtn');
                const msgBox = document.getElementById('status-msg');
                btn.disabled = true;
                btn.innerText = "指令下发中...";
                msgBox.style.color = "#718096";
                msgBox.innerText = "正在通过 OneNet 发送请求...";

                fetch('/clean', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        msgBox.style.color = "#48bb78";
                        msgBox.innerText = "✔️ " + data.msg;
                    } else {
                        msgBox.style.color = "#e53e3e";
                        msgBox.innerText = "❌ " + data.msg;
                    }
                })
                .catch(error => {
                    msgBox.style.color = "#e53e3e";
                    msgBox.innerText = "❌ 网络异常，请检查服务器连接";
                })
                .finally(() => {
                    btn.disabled = false;
                    btn.innerText = "🚀 一键铲屎";
                    setTimeout(() => { msgBox.innerText = ""; }, 3500);
                });
            }
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html_template, 
                                  temp=temp_value, 
                                  sys_state_text=sys_state_text,
                                  sys_state_color=sys_state_color,
                                  error=error_msg)

@app.route('/clean', methods=['POST'])
def send_clean_cmd():
    # 保持不变
    url = "https://iot-api.heclouds.com/thingmodel/set-device-property"
    headers = {
        "authorization": AUTHORIZATION,
        "content-type": "application/json"
    }
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
            return jsonify({"status": "success", "msg": "设备已成功接收并确认指令！"})
        else:
            return jsonify({"status": "error", "msg": f"平台拦截: {res_data.get('msg')}"})
    except Exception as e:
        return jsonify({"status": "error", "msg": f"请求超时，设备可能未在线"})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)