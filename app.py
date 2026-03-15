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
    status_url = f"https://iot-api.heclouds.com/device/detail?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"
    prop_url = f"https://iot-api.heclouds.com/thingmodel/query-device-property?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"

    headers = {
        "authorization": AUTHORIZATION
    }

    # 定义默认值
    temp_value = "--"
    sys_state_text = "获取中..."
    sys_state_color = "#cbd5e0" # 默认灰色

    cat_text = "获取中..."
    cat_color = "#cbd5e0"

    api_error = ""
    hw_error = ""
    is_online = False

    try:
        # ================= 2.1 核心修复：先获取设备的物理在线状态 =================
        status_res = requests.get(status_url, headers=headers, timeout=5).json()
        if status_res.get("code") == 0:
            dev_status = status_res.get("data", {}).get("status")
            if dev_status == 1:
                is_online = True
                sys_state_text = "等待设备上报..."
                sys_state_color = "#ecc94b"
            else:
                is_online = False
                sys_state_text = "离线 (设备断网)"
                sys_state_color = "#a0aec0"

                # 设备离线时，强制覆盖其他状态
                cat_text = "未知 (离线)"
                cat_color = "#a0aec0"

        # ================= 2.2 获取设备物模型属性 (温度、状态、错误码等) =================
        prop_res = requests.get(prop_url, headers=headers, timeout=5).json()
        if prop_res.get("code") == 0:
            properties = prop_res.get("data", [])
            for prop in properties:
                identifier = prop.get("identifier")
                val = prop.get("value")

                # 1. 解析温度
                if identifier == "temp" and val is not None:
                    try:
                        temp_value = f"{float(val):.2f}"
                    except ValueError:
                        temp_value = str(val)

                # 2. 解析系统运行状态 (仅在线时处理)
                elif identifier == "system_run_state" and val is not None and is_online:
                    if val is True or str(val).lower() == 'true' or str(val) == '1':
                        sys_state_text = "正常 (运行中)"
                        sys_state_color = "#48bb78" # 绿色
                    else:
                        sys_state_text = "异常 (运行停止)"
                        sys_state_color = "#e53e3e" # 红色

                # 3. 解析猫咪状态 (仅在线时处理)
                elif identifier == "cat_status" and val is not None and is_online:
                    if str(val) == "1":
                        cat_text = "检测到猫咪 (防夹保护中)"
                        cat_color = "#ed8936" # 橙色警告
                    else:
                        cat_text = "安全 (无猫咪)"
                        cat_color = "#48bb78" # 绿色安全

                # 4. 解析错误码报警
                elif identifier == "error_code" and val is not None and is_online:
                    if str(val) != "0":
                        hw_error = f"系统发生异常: {val}"

        else:
            if not api_error:
                api_error = f"属性获取失败: {prop_res.get('msg')}"

    except Exception as e:
        api_error = f"网络请求异常: {str(e)}"

    # ================= 3. 现代化前端 HTML 模板 =================
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
                --action: #ed8936; --action-hover: #dd6b20; --danger-bg: #fed7d7; --danger-text: #c53030;
            }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-color); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .dashboard { background: var(--card-bg); padding: 30px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.06); width: 100%; max-width: 380px; }
            .header { text-align: center; margin-bottom: 25px; }
            .header h2 { margin: 0; font-size: 22px; color: var(--text-main); font-weight: 700; }
            .header p { margin: 5px 0 0; font-size: 13px; color: var(--text-muted); }
            .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px; }
            .data-card { background: #f8fafc; border-radius: 16px; padding: 20px 10px; text-align: center; border: 1px solid #e2e8f0; }
            .data-card.full-width { grid-column: 1 / -1; padding: 15px 10px; } /* 满宽卡片 */
            .data-label { font-size: 13px; color: var(--text-muted); margin-bottom: 10px; font-weight: 500; }
            .data-value { font-size: 32px; font-weight: 700; color: var(--text-main); }
            .data-unit { font-size: 16px; color: var(--text-muted); font-weight: normal; margin-left: 2px; }
            .status-indicator { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 15px; font-weight: 600; height: 38px; }
            .status-dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 8px currentColor; }
            .error-banner { background: var(--danger-bg); color: var(--danger-text); padding: 12px; border-radius: 12px; text-align: center; font-size: 14px; margin-bottom: 20px; font-weight: 600; box-shadow: 0 2px 10px rgba(229, 62, 62, 0.1); }
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

            {% if api_error %} <div class="error-banner">网络错误: {{ api_error }}</div> {% endif %}
            {% if hw_error %} <div class="error-banner">⚠️ 硬件故障码: {{ hw_error }}</div> {% endif %}

            <div class="grid-container">
                <div class="data-card">
                    <div class="data-label">环境温度</div>
                    <div class="data-value">{{ temp }}<span class="data-unit">°C</span></div>
                </div>
                <div class="data-card">
                    <div class="data-label">设备运行状态</div>
                    <div class="status-indicator" style="color: {{ sys_state_color }};">
                        <span class="status-dot" style="background-color: {{ sys_state_color }};"></span>
                        {{ sys_state_text }}
                    </div>
                </div>

                <div class="data-card full-width">
                    <div class="data-label">内部活体感应</div>
                    <div class="status-indicator" style="color: {{ cat_color }};">
                        <span class="status-dot" style="background-color: {{ cat_color }};"></span>
                        {{ cat_text }}
                    </div>
                </div>
            </div>

            <div class="controls">
                <button id="cleanBtn" class="btn-action" onclick="sendCleanCommand()">🚀 远程一键铲屎</button>
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
                    btn.innerText = "🚀 远程一键铲屎";
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
                                  cat_text=cat_text,
                                  cat_color=cat_color,
                                  api_error=api_error,
                                  hw_error=hw_error)

@app.route('/clean', methods=['POST'])
def send_clean_cmd():
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