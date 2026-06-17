# 摔倒检测系统

基于 YOLO 的实时摔倒检测系统，支持多摄像头管理、实时视频预览、检测框叠加、WebSocket 推送告警。

## 架构

```
front (Vue 3) ──HTTP──> FastAPI (:9500) ──> YOLO 检测线程
    │                        │
    │                  SharedCapture
    │                   (单一视频源连接,
    │                    MJPEG 流 & 检测共享)
    │                        │
    └──WebSocket──> bbox_update / fall_alert
```

- **后端** FastAPI + SQLite + OpenCV + Ultralytics YOLO
- **前端** Vue 3 + Vite
- **共享视频捕获** `SharedCapture`：多个消费者（MJPEG 流、检测 runner）共享一个 `cv2.VideoCapture`，引用计数管理生命周期
- **实时推送** WebSocket 推送检测框 (`bbox_update`) 和摔倒告警 (`fall_alert`)

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- FFmpeg（用于测试视频流）
- CUDA（可选，加速 YOLO 推理）

### 安装

```bash
# 后端
pip install -r requirements.txt
# 或使用 uv
uv sync

# 前端
cd front
npm install
```

### 配置

编辑 `config.yaml`：

```yaml
server:
  host: "127.0.0.1"
  port: 9500

detection:
  model_path: "models/out/best.pt"  # YOLO 模型路径
  default_fps: 2.0                   # 默认检测帧率
  default_conf_threshold: 0.25       # 默认置信度阈值
  alert_cooldown_seconds: 30         # 同一摄像头告警间隔（秒）

stream:
  open_timeout_ms: 5000
  read_timeout_ms: 5000
  mjpeg_fps: 20                      # MJPEG 流帧率
  jpeg_quality: 80

auth:
  jwt_secret: "change-me-to-a-random-string"
  jwt_expire_hours: 24
  project_id: "001"
```

### 启动

```bash
# 后端
python main.py

# 前端开发服务器
cd front && npm run dev
```

启动后测试视频流会自动在 `http://127.0.0.1:9999` 循环播放 `data/fall.mp4`。

### 首次使用

系统首次启动时没有任何用户，访问注册接口创建管理员账户：

```bash
curl -X POST http://127.0.0.1:9500/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
```

## API 概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册（仅无用户时可用） |
| POST | `/auth/login` | 登录，返回 JWT |

### 摄像头管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/cameras` | 摄像头列表 |
| POST | `/cameras` | 新增摄像头 |
| PATCH | `/cameras/{id}` | 更新摄像头 |

### 检测任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/tasks/{camera_id}` | 获取任务状态 |
| POST | `/tasks/{camera_id}/detection` | 开关摔倒检测 |
| POST | `/tasks/{camera_id}/boxes` | 开关检测框显示 |
| PUT | `/tasks/{camera_id}/params` | 更新检测参数（FPS、置信度） |

### 告警

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/alerts` | 告警列表（支持 camera_id、unread_only、limit） |
| POST | `/alerts/{id}/read` | 标记已读 |
| DELETE | `/alerts/{id}` | 删除告警 |

### 视频流

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/streams/mjpeg` | MJPEG 视频流（source_url 参数） |
| POST | `/streams/probe` | 探测视频源是否可用 |
| POST | `/streams/resolve` | 解析视频源 URL |
| POST | `/streams/snapshot` | 截图 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/fall` | 实时推送，参数：project_id、camera_id、token、clientid |

WebSocket 消息类型：

| type | 说明 |
|------|------|
| `bbox_update` | 检测框数据（image_width、image_height、detections） |
| `fall_alert` | 摔倒告警 |
| `task_status` | 任务状态变更 |
| `error` | 检测异常 |

## 前端功能

- **视频预览** MJPEG 实时流播放，支持手动输入视频源 URL
- **摄像头管理** 新增、编辑摄像头（名称、视频源、后缀）
- **摔倒检测开关** 控制是否生成摔倒告警
- **显示人物框开关** 独立控制检测框叠加层，开启后自动启动 YOLO 推理
- **检测参数** 检测频率（FPS）和置信度阈值，改动后自动持久化
- **实时框叠加** SVG 叠加层，绿色边界框
- **告警列表** 实时推送摔倒告警，支持标记已读、删除
- **视频探测** 测试 OpenCV 是否能打开指定视频源

## 检测框与告警的独立性

两个开关独立工作：

- **摔倒检测** 控制是否生成摔倒告警
- **显示人物框** 控制是否在前端显示 YOLO 检测框

- 仅开启显示框 → YOLO 运行，推送检测框，不产生告警
- 仅开启检测 → YOLO 运行，产生告警，不推送检测框
- 两开关都开 → 完整功能
- 两开关都关 → 停止 YOLO 推理

## 项目结构

```
fall_down_yolo/
├── main.py                  # 应用入口
├── config.yaml              # 配置文件
├── app/
│   ├── config.py            # 配置加载
│   ├── db.py                # 数据库连接
│   ├── models.py            # SQLAlchemy 模型
│   ├── schemas.py           # Pydantic 模型
│   ├── detector.py          # YOLO 检测器封装
│   ├── detection_runner.py  # 检测任务线程
│   ├── stream_reader.py     # 视频流读取 & URL 解析
│   ├── shared_capture.py    # 共享视频捕获 & 引用计数管理
│   ├── ws_manager.py        # WebSocket 发布管理
│   ├── test_stream.py       # FFmpeg 测试视频流
│   └── routers/
│       ├── auth.py          # 认证接口
│       ├── cameras.py       # 摄像头 CRUD
│       ├── tasks.py         # 检测任务控制
│       ├── alerts.py        # 告警接口
│       ├── streams.py       # 视频流接口
│       ├── ws.py            # WebSocket 端点
│       └── health.py        # 健康检查
├── front/                   # Vue 3 前端
├── data/
│   ├── fall.mp4             # 测试视频
│   └── fall_down.db         # SQLite 数据库
├── models/
│   └── out/
│       └── best.pt          # YOLO 模型权重
```
