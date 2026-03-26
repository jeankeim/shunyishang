# Week 6 - Task 03: 生产部署

## 任务概述
完成生产环境的完整部署，包括云服务器配置、域名与HTTPS、监控告警、自动化备份等，确保系统可以对外提供服务。

## 背景与目标
经过前5周的开发和Week 6的优化，系统已具备生产环境运行的条件。本任务将完成最后一步：将系统部署到生产环境，让用户可以访问使用。

## 技术要求

### 基础设施
- 云服务器 (推荐 4核8G+)
- 域名与 DNS 配置
- HTTPS 证书
- 对象存储 (可选，用于图片)

### 监控告警
- 应用性能监控 (APM)
- 日志集中管理
- 告警通知
- 健康检查

### 运维自动化
- 自动化部署
- 数据库备份
- 日志轮转
- 故障恢复

## 实现步骤

### 1. 云服务器准备

#### 1.1 服务器配置
推荐配置:
- CPU: 4核+
- 内存: 8GB+
- 磁盘: 100GB SSD
- 带宽: 5Mbps+
- 系统: Ubuntu 22.04 LTS

#### 1.2 系统初始化
```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker

# 安装 Docker Compose
apt install docker-compose-plugin -y

# 配置防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 2. 域名与 HTTPS

#### 2.1 域名配置
- 购买域名 (如: wuxing-ai.com)
- 配置 DNS A 记录指向服务器 IP
- 等待 DNS 生效

#### 2.2 HTTPS 证书
使用 Let's Encrypt + Certbot:

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 申请证书
certbot certonly --standalone -d wuxing-ai.com -d www.wuxing-ai.com

# 自动续期
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

#### 2.3 Nginx 反向代理
文件: `/etc/nginx/sites-available/wuxing`

```nginx
server {
    listen 80;
    server_name wuxing-ai.com www.wuxing-ai.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name wuxing-ai.com www.wuxing-ai.com;

    ssl_certificate /etc/letsencrypt/live/wuxing-ai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wuxing-ai.com/privkey.pem;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. 监控告警

#### 3.1 Prometheus + Grafana
文件: `monitoring/docker-compose.yml`

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
```

#### 3.2 告警规则
文件: `monitoring/prometheus.yml`

```yaml
groups:
  - name: wuxing_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time"
```

#### 3.3 告警通知
配置钉钉/企业微信 webhook:

```yaml
# alertmanager.yml
receivers:
  - name: 'dingtalk'
    webhook_configs:
      - url: 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
        send_resolved: true
```

### 4. 自动化备份

#### 4.1 数据库备份脚本
文件: `scripts/backup.sh`

```bash
#!/bin/bash

BACKUP_DIR="/backup/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="wuxing_backup_$DATE.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker exec wuxing_postgres_prod pg_dump -U wuxing wuxing > $BACKUP_DIR/$BACKUP_FILE

# 压缩备份
gzip $BACKUP_DIR/$BACKUP_FILE

# 删除7天前的备份
find $BACKUP_DIR -name "wuxing_backup_*.sql.gz" -mtime +7 -delete

# 上传到云存储（可选）
# aws s3 cp $BACKUP_DIR/${BACKUP_FILE}.gz s3://wuxing-backups/

echo "Backup completed: $BACKUP_FILE.gz"
```

#### 4.2 定时任务
```bash
# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh >> /var/log/wuxing_backup.log 2>&1
```

### 5. 日志管理

#### 5.1 日志轮转
文件: `/etc/logrotate.d/wuxing`

```
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
```

#### 5.2 日志收集 (可选)
使用 ELK 或 Loki:
```yaml
# loki/docker-compose.yml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
```

### 6. CI/CD 配置

#### 6.1 GitHub Actions
文件: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/wuxing
            git pull origin main
            docker-compose -f docker-compose.prod.yml up -d --build
```

## 验收标准

### 功能验收
- [ ] 域名可正常访问
- [ ] HTTPS 证书有效
- [ ] 所有功能正常工作
- [ ] 移动端可访问

### 性能验收
- [ ] 首屏加载 < 3秒
- [ ] API 响应 < 200ms
- [ ] 支持 100+ 并发

### 安全验收
- [ ] HTTPS 强制跳转
- [ ] 安全头配置
- [ ] 无敏感信息泄露

### 运维验收
- [ ] 监控面板正常
- [ ] 告警通知正常
- [ ] 自动备份正常
- [ ] 日志可查看

## 交付物

### 配置文件
- `nginx/nginx.conf` - Nginx 生产配置
- `monitoring/docker-compose.yml` - 监控配置
- `monitoring/prometheus.yml` - Prometheus 配置
- `.github/workflows/deploy.yml` - CI/CD 配置

### 脚本文件
- `scripts/backup.sh` - 数据库备份脚本
- `scripts/deploy.sh` - 部署脚本
- `scripts/health_check.sh` - 健康检查脚本
- `scripts/setup_server.sh` - 服务器初始化脚本

### 文档
- `docs/DEPLOYMENT.md` - 部署文档
- `docs/OPERATIONS.md` - 运维手册
- `docs/TROUBLESHOOTING.md` - 故障排查

## 预估工时
- 服务器配置: 2小时
- 域名与 HTTPS: 2小时
- 监控告警: 3小时
- 自动化备份: 2小时
- CI/CD 配置: 2小时
- 测试验证: 2小时
- **总计: 13小时**

## 依赖任务
- Week 6-02: Docker Compose 生产配置

## 注意事项
1. 生产环境密钥必须安全存储
2. 定期更新系统和依赖
3. 监控资源使用情况
4. 制定故障恢复预案
5. 保留部署和回滚记录
