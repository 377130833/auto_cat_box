from flask import Flask, render_template_string, jsonify
import requests
import json
import os

app = Flask(__name__)

# ================= 1. OneNet API 配置 =================
PRODUCT_ID = "zJsLok5Lw5"
DEVICE_NAME = "test"
AUTHORIZATION = "version=2018-10-31&res=products%2FzJsLok5Lw5%2Fdevices%2Ftest&et=2810373514&method=md5&sign=xDs4xNuxlZp8k32wXLpqWg%3D%3D" 

# ================= 2. 核心数据获取逻辑 (抽离为独立函数) =================
def fetch_device_data():
    status_url = f"https://iot-api.heclouds.com/device/detail?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"
    prop_url = f"https://iot-api.heclouds.com/thingmodel/query-device-property?product_id={PRODUCT_ID}&device_name={DEVICE_NAME}"

    headers = {"authorization": AUTHORIZATION}

    # 初始化返回的数据字典
    data = {
        "temp": "--",
        "sys_state_text": "获取中...",
        "sys_state_color": "#cbd5e0",
        "cat_text": "获取中...",
        "cat_color": "#cbd5e0",
        "api_error": "",
        "hw_error": ""
    }

    is_online = False

    try:
        # 2.1 获取在线状态
        status_res = requests.get(status_url, headers=headers, timeout=5).json()
        if status_res.get("code") == 0:
            dev_status = status_res.get("data", {}).get("status")
            if dev_status == 1:
                is_online = True
                data["sys_state_text"] = "等待设备上报..."
                data["sys_state_color"] = "#ecc94b"
            else:
                is_online = False
                data["sys_state_text"] = "离线 (设备断网)"
                data["sys_state_color"] = "#a0aec0"
                data["cat_text"] = "未知 (离线)"
                data["cat_color"] = "#a0aec0"

        # 2.2 获取属性状态
        prop_res = requests.get(prop_url, headers=headers, timeout=5).json()
        if prop_res.get("code") == 0:
            properties = prop_res.get("data", [])
            for prop in properties:
                identifier = prop.get("identifier")
                val = prop.get("value")

                if identifier == "temp" and val is not None:
                    try:
                        data["temp"] = f"{float(val):.2f}"
                    except ValueError:
                        data["temp"] = str(val)

                elif identifier == "system_run_state" and val is not None and is_online:
                    if val is True or str(val).lower() == 'true' or str(val) == '1':
                        data["sys_state_text"] = "正常 (运行中)"
                        data["sys_state_color"] = "#48bb78"
                    else:
                        data["sys_state_text"] = "异常 (运行停止)"
                        data["sys_state_color"] = "#e53e3e"

                elif identifier == "cat_status" and val is not None and is_online:
                    if str(val) == "1":
                        data["cat_text"] = "检测到猫咪 (防夹保护中)"
                        data["cat_color"] = "#ed8936"
                    else:
                        data["cat_text"] = "安全 (无猫咪)"
                        data["cat_color"] = "#48bb78"

                elif identifier == "error_code" and val is not None and is_online:
                    if str(val) != "0":
                        data["hw_error"] = f"系统发生异常: {val}"
        else:
            if not data["api_error"]:
                data["api_error"] = f"属性获取失败: {prop_res.get('msg')}"

    except Exception as e:
        data["api_error"] = f"网络请求异常: {str(e)}"

    return data

# ================= 3. 路由配置 =================

# 3.1 供前端 AJAX 调用的数据接口
@app.route('/api/data')
def get_data_api():
    return jsonify(fetch_device_data())

# 3.2 首次打开网页加载的路由
@app.route('/')
def index():
    # 首次加载时同步获取一次数据，防止页面闪烁
    initial_data = fetch_device_data()

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
            .data-card { background: #f8fafc; border-radius: 16px; padding: 20px 10px; text-align: center; border: 1px solid #e2e8f0; transition: all 0.3s; }
            .data-card.full-width { grid-column: 1 / -1; padding: 15px 10px; }
            .data-label { font-size: 13px; color: var(--text-muted); margin-bottom: 10px; font-weight: 500; }
            .data-value { font-size: 32px; font-weight: 700; color: var(--text-main); }
            .data-unit { font-size: 16px; color: var(--text-muted); font-weight: normal; margin-left: 2px; }
            .status-indicator { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 15px; font-weight: 600; height: 38px; transition: color 0.3s; }
            .status-dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 8px currentColor; transition: background-color 0.3s; }
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

            <div id="api-error-banner" class="error-banner" style="display: {% if api_error %}block{% else %}none{% endif %};">
                网络错误: <span id="api-error-text">{{ api_error }}</span>
            </div>
            <div id="hw-error-banner" class="error-banner" style="display: {% if hw_error %}block{% else %}none{% endif %};">
                ⚠️ 硬件故障码: <span id="hw-error-text">{{ hw_error }}</span>
            </div>

            <div class="grid-container">
                <div class="data-card">
                    <div class="data-label">环境温度</div>
                    <div class="data-value"><span id="temp-val">{{ temp }}</span><span class="data-unit">°C</span></div>
                </div>
                <div class="data-card">
                    <div class="data-label">设备运行状态</div>
                    <div class="status-indicator" id="sys-state-container" style="color: {{ sys_state_color }};">
                        <span class="status-dot" id="sys-state-dot" style="background-color: {{ sys_state_color }};"></span>
                        <span id="sys-state-text">{{ sys_state_text }}</span>
                    </div>
                </div>

                <div class="data-card full-width">
                    <div class="data-label">内部活体感应</div>
                    <div class="status-indicator" id="cat-state-container" style="color: {{ cat_color }};">
                        <span class="status-dot" id="cat-state-dot" style="background-color: {{ cat_color }};"></span>
                        <span id="cat-text">{{ cat_text }}</span>
                    </div>
                </div>
            </div>

            <div class="controls">
                <button id="cleanBtn" class="btn-action" onclick="sendCleanCommand()">🚀 远程一键铲屎</button>
                <button id="refreshBtn" class="btn-refresh" onclick="fetchDeviceData(true)">🔄 刷新最新状态</button>
            </div>
            <div id="status-msg"></div>
        </div>

        <script>
            // ================= 核心：前端异步获取数据引擎 =================
            function fetchDeviceData(isManual = false) {
                const refreshBtn = document.getElementById('refreshBtn');

                // 如果是手动点击刷新，给按键加上动态效果
                if (isManual) {
                    refreshBtn.disabled = true;
                    refreshBtn.innerText = "🔄 刷新中...";
                }

                fetch('/api/data')
                    .then(response => response.json())
                    .then(data => {
                        // 1. 动态替换温度
                        document.getElementById('temp-val').innerText = data.temp;

                        // 2. 动态替换系统运行状态和颜色
                        document.getElementById('sys-state-text').innerText = data.sys_state_text;
                        document.getElementById('sys-state-container').style.color = data.sys_state_color;
                        document.getElementById('sys-state-dot').style.backgroundColor = data.sys_state_color;

                        // 3. 动态替换猫咪活体感应状态和颜色
                        document.getElementById('cat-text').innerText = data.cat_text;
                        document.getElementById('cat-state-container').style.color = data.cat_color;
                        document.getElementById('cat-state-dot').style.backgroundColor = data.cat_color;

                        // 4. 动态显示或隐藏 API 错误条
                        const apiBanner = document.getElementById('api-error-banner');
                        if (data.api_error) {
                            apiBanner.style.display = 'block';
                            document.getElementById('api-error-text').innerText = data.api_error;
                        } else {
                            apiBanner.style.display = 'none';
                        }

                        // 5. 动态显示或隐藏硬件故障条
                        const hwBanner = document.getElementById('hw-error-banner');
                        if (data.hw_error) {
                            hwBanner.style.display = 'block';
                            document.getElementById('hw-error-text').innerText = data.hw_error;
                        } else {
                            hwBanner.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error("后台请求失败:", error);
                        // 如果连后端服务都挂了，可以在这里加上提示
                    })
                    .finally(() => {
                        // 无论请求成功还是失败，恢复按钮状态
                        if (isManual) {
                            refreshBtn.disabled = false;
                            refreshBtn.innerText = "🔄 刷新最新状态";
                        }
                    });
            }

            // 启动定时器：每 5000 毫秒 (5秒) 后台悄悄拉取一次数据
            setInterval(() => fetchDeviceData(false), 5000);

            // ================= 指令下发逻辑 (保持不变) =================
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
                        // 既然发送了指令，设备状态肯定要变，顺便触发一次无感刷新
                        setTimeout(() => fetchDeviceData(false), 2000);
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

    # 这里的 initial_data 用双星号 ** 解包，直接把字典里的键值对传给 Jinja2 模板
    return render_template_string(html_template, **initial_data)

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