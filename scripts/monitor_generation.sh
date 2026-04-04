#!/bin/bash
# 监控图片生成脚本，如果 2 分钟没有进展就自动重启

TARGET=100
OUTPUT_DIR="/Users/mingyang/Desktop/shunyishang/data/generated_images/seed_data_100"
SCRIPT_PATH="/Users/mingyang/Desktop/shunyishang/scripts/generate_seed_data_100.py"
VENV_PYTHON="/Users/mingyang/Desktop/shunyishang/.venv/bin/python"
LOG_FILE="/tmp/generate_seed_100_monitor.log"

echo "=== 开始监控图片生成任务 ===" | tee -a $LOG_FILE
echo "目标：$TARGET 张图片" | tee -a $LOG_FILE
echo "输出目录：$OUTPUT_DIR" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

last_count=0
last_change_time=$(date +%s)
attempt=1

while true; do
    # 计算当前已生成的图片数量
    current_count=$(find "$OUTPUT_DIR" -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
    current_time=$(date +%s)
    
    # 检查是否有新图片
    if [ "$current_count" -gt "$last_count" ]; then
        progress=$((current_count - last_count))
        echo "[$(date '+%H:%M:%S')] ✅ 新增 $progress 张 (总计：$current_count/$TARGET)" | tee -a $LOG_FILE
        last_count=$current_count
        last_change_time=$current_time
        
        # 检查是否完成
        if [ "$current_count" -ge "$TARGET" ]; then
            echo "" | tee -a $LOG_FILE
            echo "[$(date '+%H:%M:%S')] 🎉 完成！已生成 $current_count 张图片" | tee -a $LOG_FILE
            exit 0
        fi
    else
        # 计算无进展的时间
        idle_seconds=$((current_time - last_change_time))
        idle_minutes=$((idle_seconds / 60))
        
        # 每 30 秒报告一次状态
        if [ $((idle_seconds % 60)) -eq 0 ] && [ $idle_seconds -gt 0 ]; then
            echo "[$(date '+%H:%M:%S')] ⏳ 等待中... $current_count/$TARGET (已等待 ${idle_minutes}分钟)" | tee -a $LOG_FILE
        fi
        
        # 如果超过 2 分钟没有进展，重启脚本
        if [ "$idle_seconds" -ge 120 ]; then
            echo "" | tee -a $LOG_FILE
            echo "[$(date '+%H:%M:%S')] ⚠️  检测到 ${idle_minutes}分钟无进展，正在重启脚本..." | tee -a $LOG_FILE
            
            # 杀死旧进程
            pkill -f "generate_seed_data_100.py"
            sleep 2
            
            # 启动新进程
            echo "[$(date '+%H:%M:%S')] 🔄 启动第 $attempt 次尝试..." | tee -a $LOG_FILE
            nohup $VENV_PYTHON "$SCRIPT_PATH" > /tmp/generate_seed_100_run${attempt}.log 2>&1 &
            new_pid=$!
            echo "[$(date '+%H:%M:%S')] ℹ️  新进程 PID: $new_pid" | tee -a $LOG_FILE
            
            attempt=$((attempt + 1))
            last_change_time=$current_time
            sleep 5
        fi
    fi
    
    # 每 30 秒检查一次
    sleep 30
done
