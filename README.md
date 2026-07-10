# 世界杯观赛调查系统

纯 Python 标准库实现，无任何外部依赖。

## 快速启动（本地）

```bash
python3 run_server.py
```

访问 http://127.0.0.1:8802

## 部署到公网（方法一：Railway，最简单）

1. 注册 https://railway.app （支持 GitHub 登录）
2. 安装 Railway CLI：`bash <(curl -sSL https://railway.app/install.sh)`
3. 在项目目录执行：
   ```bash
   railway login
   railway init
   railway up
   ```
4. Railway 会自动检测 Python 项目并启动 `run_server.py`
5. 部署完成后 Railway 会给你一个 `https://xxx.up.railway.app` 的链接

## 部署到公网（方法二：阿里云 ECS）

1. 购买一台阿里云轻量应用服务器（最便宜的大概 34元/月）
2. SSH 登录服务器，执行：
   ```bash
   # 安装 Python3（如果没装）
   apt update && apt install -y python3
   
   # 上传文件（在本地 Mac 上执行）
   scp -r /path/to/worldcup-survey root@你的服务器IP:/root/
   
   # 在服务器上启动
   cd /root/worldcup-survey
   python3 run_server.py
   ```
3. 在阿里云防火墙开放 8802 端口
4. 就可以用 `http://你的服务器IP:8802` 访问了

## 查看提交记录

后台地址：/admin/login
密码：worldcup2026
