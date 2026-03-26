# Task 02: 五行能量雷达图组件

## 目标
使用 Recharts 实现双图层雷达图，可视化用户八字五行（现状）和推荐衣物五行（建议）。

## 设计规范

### 五行配色
| 五行 | 颜色 | Hex |
|:---:|:---:|:---:|
| 金 | 白/金 | `#E5E7EB` |
| 木 | 绿 | `#4ADE80` |
| 水 | 蓝/黑 | `#60A5FA` |
| 火 | 红/紫 | `#F87171` |
| 土 | 黄/棕 | `#D97706` |

### 双图层设计
- **图层 A（现状）**：虚线 + 半透明灰色，表示用户当前八字五行分布
- **图层 B（建议）**：实线 + 鲜艳渐变色，表示推荐衣物应补充的五行

## 执行步骤

### 1. 类型定义 (types/index.ts)
```typescript
export interface FiveElementData {
  element: '金' | '木' | '水' | '火' | '土';
  current: number;   // 当前值 (0-100)
  suggested: number; // 建议值 (0-100)
  fullMark: 100;
}

export interface FiveElementRadarProps {
  data: FiveElementData[];
  highlightElement?: string; // 高亮显示喜用神
  size?: 'sm' | 'md' | 'lg';
}
```

### 2. 雷达图组件 (components/features/FiveElementRadar.tsx)
```typescript
'use client';

import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';
import { cn } from '@/lib/utils';

const ELEMENT_CONFIG = {
  '金': { color: '#E5E7EB', emoji: '⚪', angle: 0 },
  '木': { color: '#4ADE80', emoji: '🟢', angle: 72 },
  '水': { color: '#60A5FA', emoji: '🔵', angle: 144 },
  '火': { color: '#F87171', emoji: '🔴', angle: 216 },
  '土': { color: '#D97706', emoji: '🟡', angle: 288 },
};

interface FiveElementRadarProps {
  currentData?: Record<string, number>;  // 用户八字五行 {金: 20, 木: 30...}
  suggestedData?: Record<string, number>; // 推荐衣物五行
  xiyongShen?: string[]; // 喜用神
  className?: string;
}

export function FiveElementRadar({
  currentData,
  suggestedData,
  xiyongShen = [],
  className,
}: FiveElementRadarProps) {
  // 转换为 Recharts 数据格式
  const data = ['金', '木', '水', '火', '土'].map((element) => ({
    element: `${ELEMENT_CONFIG[element].emoji}${element}`,
    当前八字: currentData?.[element] || 0,
    建议补充: suggestedData?.[element] || 0,
    fullMark: 100,
    isXiyong: xiyongShen.includes(element),
  }));

  const hasCurrent = currentData && Object.values(currentData).some(v => v > 0);
  const hasSuggested = suggestedData && Object.values(suggestedData).some(v => v > 0);

  return (
    <div className={cn("bg-card/50 backdrop-blur rounded-xl border p-6", className)}>
      <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
        <span>五行能量分布</span>
        {xiyongShen.length > 0 && (
          <span className="text-sm font-normal text-muted-foreground">
            (喜用神: {xiyongShen.join('、')})
          </span>
        )}
      </h3>

      <ResponsiveContainer width="100%" height={320}>
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="hsl(var(--border))" />
          <PolarAngleAxis
            dataKey="element"
            tick={({ payload, x, y, textAnchor }) => {
              const element = payload.value.slice(2); // 去掉 emoji
              const isXiyong = xiyongShen.includes(element);
              return (
                <text
                  x={x}
                  y={y}
                  textAnchor={textAnchor}
                  fill={isXiyong ? ELEMENT_CONFIG[element].color : 'hsl(var(--muted-foreground))'}
                  fontSize={14}
                  fontWeight={isXiyong ? 'bold' : 'normal'}
                >
                  {payload.value}
                </text>
              );
            }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={false}
            axisLine={false}
          />

          {/* 图层 A: 当前八字（虚线 + 半透明） */}
          {hasCurrent && (
            <Radar
              name="当前八字"
              dataKey="当前八字"
              stroke="#64748b"
              strokeDasharray="4 4"
              fill="#64748b"
              fillOpacity={0.1}
              strokeWidth={2}
            />
          )}

          {/* 图层 B: 建议补充（实线 + 鲜艳） */}
          {hasSuggested && (
            <Radar
              name="建议补充"
              dataKey="建议补充"
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary))"
              fillOpacity={0.3}
              strokeWidth={3}
            />
          )}

          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
          />
        </RadarChart>
      </ResponsiveContainer>

      {/* 五行图例 */}
      <div className="mt-4 grid grid-cols-5 gap-2 text-center text-xs">
        {Object.entries(ELEMENT_CONFIG).map(([element, config]) => (
          <div
            key={element}
            className={cn(
              "flex flex-col items-center gap-1 p-2 rounded",
              xiyongShen.includes(element) && "bg-primary/10"
            )}
          >
            <div
              className="w-4 h-4 rounded-full shadow"
              style={{ backgroundColor: config.color }}
            />
            <span className={cn(
              xiyongShen.includes(element) && "text-primary font-medium"
            )}>
              {element}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 3. 数据转换工具 (lib/utils.ts)
```typescript
import { BaziResult } from '@/types';

/**
 * 将八字结果转换为雷达图数据
 */
export function baziToRadarData(bazi: BaziResult | null): Record<string, number> {
  if (!bazi) return {};

  const counts: Record<string, number> = { '金': 0, '木': 0, '水': 0, '火': 0, '土': 0 };

  // 天干五行
  const tianganWuxing: Record<string, string> = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水',
  };

  // 地支五行
  const dizhiWuxing: Record<string, string> = {
    '寅': '木', '卯': '木',
    '巳': '火', '午': '火',
    '辰': '土', '戌': '土', '丑': '土', '未': '土',
    '申': '金', '酉': '金',
    '亥': '水', '子': '水',
  };

  // 统计四柱
  const pillars = [
    bazi.year_pillar,
    bazi.month_pillar,
    bazi.day_pillar,
    bazi.hour_pillar,
  ];

  pillars.forEach((pillar) => {
    if (pillar && pillar.length === 2) {
      const [gan, zhi] = pillar.split('');
      if (tianganWuxing[gan]) counts[tianganWuxing[gan]]++;
      if (dizhiWuxing[zhi]) counts[dizhiWuxing[zhi]]++;
    }
  });

  // 归一化到 0-100
  const max = Math.max(...Object.values(counts), 1);
  return Object.fromEntries(
    Object.entries(counts).map(([k, v]) => [k, Math.round((v / max) * 100)])
  );
}

/**
 * 将推荐物品转换为雷达图数据
 */
export function itemsToRadarData(items: Array<{ primary_element: string }>): Record<string, number> {
  const counts: Record<string, number> = { '金': 0, '木': 0, '水': 0, '火': 0, '土': 0 };

  items.forEach((item) => {
    if (item.primary_element) {
      counts[item.primary_element] = (counts[item.primary_element] || 0) + 1;
    }
  });

  // 归一化
  const max = Math.max(...Object.values(counts), 1);
  return Object.fromEntries(
    Object.entries(counts).map(([k, v]) => [k, Math.round((v / max) * 100)])
  );
}
```

## 验收动作

1. **硬编码测试**
在 `page.tsx` 中硬编码数据：
```typescript
const testCurrent = { '金': 20, '木': 80, '水': 30, '火': 60, '土': 40 };
const testSuggested = { '金': 80, '木': 30, '水': 60, '火': 30, '土': 50 };

<FiveElementRadar
  currentData={testCurrent}
  suggestedData={testSuggested}
  xiyongShen={['金', '水']}
/>
```

2. **视觉检查**
- 虚线表示"当前八字"，实线表示"建议补充"
- 喜用神（金、水）在图例中高亮显示
- 鼠标 Hover 显示具体数值

## 验收标准
- [ ] 雷达图显示五行（金木水火土）五个维度
- [ ] 当前八字用虚线 + 灰色表示
- [ ] 建议补充用实线 + 主题色表示
- [ ] 喜用神在图例中高亮（带背景色）
- [ ] 鼠标 Hover 到顶点显示具体数值
- [ ] 无数据时雷达图为空，不报错
- [ ] 响应式：容器宽度变化时图表自适应
