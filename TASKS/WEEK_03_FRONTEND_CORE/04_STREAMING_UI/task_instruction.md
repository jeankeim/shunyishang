# Task 04: 流式响应解析与打字机效果

## 目标
将后端 SSE 流实时转化为前端的打字机效果和动态卡片动画。

## 执行步骤

### 1. 类型定义 (types/index.ts)
```typescript
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'analysis' | 'items' | 'token' | 'done' | 'error';
  metadata?: {
    targetElements?: string[];
    items?: RecommendedItem[];
    baziAnalysis?: any;
  };
  createdAt: number;
}

export interface RecommendedItem {
  item_code: string;
  name: string;
  category: string;
  primary_element: string;
  secondary_element?: string;
  final_score: number;
  attributes?: {
    color?: { name: string };
    material?: { name: string };
  };
}

export interface BaziInput {
  birthYear: number;
  birthMonth: number;
  birthDay: number;
  birthHour: number;
  gender: '男' | '女';
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}
```

### 2. Zustand Store (store/chat.ts)
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ChatMessage, Conversation, BaziInput } from '@/types';

interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  userBazi: BaziInput | null;
  isLoading: boolean;

  // Actions
  createConversation: () => string;
  setCurrentConversation: (id: string) => void;
  addMessage: (conversationId: string, message: ChatMessage) => void;
  updateMessage: (conversationId: string, messageId: string, updates: Partial<ChatMessage>) => void;
  setUserBazi: (bazi: BaziInput) => void;
  setIsLoading: (loading: boolean) => void;
  clearConversations: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      userBazi: null,
      isLoading: false,

      createConversation: () => {
        const id = `conv_${Date.now()}`;
        const conversation: Conversation = {
          id,
          title: '新对话',
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        set((state) => ({
          conversations: [conversation, ...state.conversations],
          currentConversationId: id,
        }));
        return id;
      },

      setCurrentConversation: (id) => {
        set({ currentConversationId: id });
      },

      addMessage: (conversationId, message) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, message],
                  updatedAt: Date.now(),
                  title: conv.messages.length === 0 && message.role === 'user'
                    ? message.content.slice(0, 20) + (message.content.length > 20 ? '...' : '')
                    : conv.title,
                }
              : conv
          ),
        }));
      },

      updateMessage: (conversationId, messageId, updates) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: conv.messages.map((msg) =>
                    msg.id === messageId ? { ...msg, ...updates } : msg
                  ),
                }
              : conv
          ),
        }));
      },

      setUserBazi: (bazi) => {
        set({ userBazi: bazi });
      },

      setIsLoading: (loading) => {
        set({ isLoading: loading });
      },

      clearConversations: () => {
        set({ conversations: [], currentConversationId: null });
      },
    }),
    {
      name: 'wuxing-chat-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        userBazi: state.userBazi,
      }),
    }
  )
);
```

### 3. 打字机组件 (components/features/TypewriterText.tsx)
```typescript
'use client';

import { useEffect, useState } from 'react';

interface TypewriterTextProps {
  text: string;
  speed?: number;
  onComplete?: () => void;
}

export function TypewriterText({ text, speed = 30, onComplete }: TypewriterTextProps) {
  const [displayText, setDisplayText] = useState('');

  useEffect(() => {
    if (!text) return;

    let index = 0;
    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayText(text.slice(0, index + 1));
        index++;
      } else {
        clearInterval(timer);
        onComplete?.();
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed, onComplete]);

  // 如果文本变化很大，直接显示（流式场景）
  useEffect(() => {
    if (text.length > displayText.length + 10) {
      setDisplayText(text);
    }
  }, [text]);

  return <span>{displayText}</span>;
}
```

### 4. 推荐卡片组件 (components/features/RecommendCard.tsx)
```typescript
'use client';

import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RecommendedItem } from '@/types';

const ELEMENT_COLORS: Record<string, string> = {
  '金': 'bg-gray-200 text-gray-800',
  '木': 'bg-green-400 text-green-900',
  '水': 'bg-blue-400 text-blue-900',
  '火': 'bg-red-400 text-red-900',
  '土': 'bg-yellow-600 text-yellow-50',
};

interface RecommendCardProps {
  item: RecommendedItem;
  index: number;
}

export function RecommendCard({ item, index }: RecommendCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
    >
      <Card className="overflow-hidden hover:shadow-lg transition-shadow">
        {/* 占位图 */}
        <div
          className="h-32 bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center"
          style={{
            backgroundImage: `url(https://placehold.co/400x200?text=${encodeURIComponent(item.name)})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        />
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2">
            <h4 className="font-medium text-sm line-clamp-2">{item.name}</h4>
            <Badge
              variant="secondary"
              className={ELEMENT_COLORS[item.primary_element] || 'bg-gray-500'}
            >
              {item.primary_element}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">{item.category}</p>
          <div className="flex items-center gap-2 mt-2 text-xs">
            <span className="text-muted-foreground">匹配度</span>
            <span className="font-medium text-primary">
              {(item.final_score * 100).toFixed(0)}%
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
```

### 5. 聊天界面 (components/features/ChatInterface.tsx)
```typescript
'use client';

import { useRef, useCallback } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useChatStore } from '@/store/chat';
import { streamRecommendation } from '@/lib/api';
import { ChatMessage, BaziInput } from '@/types';
import { v4 as uuidv4 } from 'uuid';
import { ChatMessageItem } from './ChatMessageItem';
import { ChatInput } from './ChatInput';

export function ChatInterface() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const {
    currentConversation,
    currentConversationId,
    createConversation,
    addMessage,
    updateMessage,
    setIsLoading,
    userBazi,
  } = useChatStore();

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  const handleSend = async (content: string, bazi?: BaziInput) => {
    let convId = currentConversationId;
    if (!convId) {
      convId = createConversation();
    }

    // 用户消息
    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: 'user',
      content,
      createdAt: Date.now(),
    };
    addMessage(convId, userMessage);

    // AI 占位
    const aiMessageId = uuidv4();
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      createdAt: Date.now(),
    };
    addMessage(convId, aiMessage);

    setIsLoading(true);

    // 流式请求
    try {
      for await (const event of streamRecommendation({
        query: content,
        bazi: bazi ? {
          birth_year: bazi.birthYear,
          birth_month: bazi.birthMonth,
          birth_day: bazi.birthDay,
          birth_hour: bazi.birthHour,
          gender: bazi.gender,
        } : undefined,
      })) {
        switch (event.type) {
          case 'analysis':
            updateMessage(convId, aiMessageId, {
              type: 'analysis',
              metadata: {
                targetElements: event.data.target_elements,
                baziAnalysis: event.data.bazi_analysis,
              },
            });
            break;

          case 'items':
            updateMessage(convId, aiMessageId, {
              metadata: {
                ...currentConversation?.messages.find(m => m.id === aiMessageId)?.metadata,
                items: event.data,
              },
            });
            break;

          case 'token':
            updateMessage(convId, aiMessageId, {
              content: currentConversation?.messages.find(m => m.id === aiMessageId)?.content + event.data,
            });
            scrollToBottom();
            break;

          case 'done':
            updateMessage(convId, aiMessageId, { type: 'done' });
            setIsLoading(false);
            break;

          case 'error':
            updateMessage(convId, aiMessageId, {
              content: '抱歉，服务暂时不可用，请稍后重试。',
              type: 'error',
            });
            setIsLoading(false);
            break;
        }
      }
    } catch (error) {
      updateMessage(convId, aiMessageId, {
        content: '连接失败，请检查网络后重试。',
        type: 'error',
      });
      setIsLoading(false);
    }
  };

  const messages = currentConversation?.messages || [];

  return (
    <div className="flex flex-col h-full">
      <ScrollArea ref={scrollRef} className="flex-1 px-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <div className="text-4xl mb-4">🌿</div>
            <h2 className="text-xl font-semibold mb-2">五行智能衣橱</h2>
            <p className="text-sm">输入你的穿搭需求，获取五行推荐</p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto py-4 space-y-4">
            {messages.map((message) => (
              <ChatMessageItem key={message.id} message={message} />
            ))}
          </div>
        )}
      </ScrollArea>

      <ChatInput onSend={handleSend} disabled={false} bazi={userBazi || undefined} />
    </div>
  );
}
```

### 6. 消息项组件 (components/features/ChatMessageItem.tsx)
```typescript
'use client';

import { motion } from 'framer-motion';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ChatMessage } from '@/types';
import { TypewriterText } from './TypewriterText';
import { RecommendCard } from './RecommendCard';
import { cn } from '@/lib/utils';

const ELEMENT_EMOJI: Record<string, string> = {
  '金': '⚪', '木': '🟢', '水': '🔵', '火': '🔴', '土': '🟡',
};

interface ChatMessageItemProps {
  message: ChatMessage;
}

export function ChatMessageItem({ message }: ChatMessageItemProps) {
  const isUser = message.role === 'user';
  const isStreaming = message.type !== 'done' && message.role === 'assistant';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex gap-4 py-4",
        isUser ? "bg-transparent" : "bg-card/30 rounded-lg"
      )}
    >
      <Avatar className="h-8 w-8 shrink-0">
        {isUser ? (
          <AvatarFallback>我</AvatarFallback>
        ) : (
          <AvatarFallback className="bg-primary text-primary-foreground">AI</AvatarFallback>
        )}
      </Avatar>

      <div className="flex-1 space-y-3 min-w-0">
        <div className="font-medium">{isUser ? '我' : '五行AI助手'}</div>

        {/* 五行标签 */}
        {message.metadata?.targetElements && (
          <div className="flex gap-2 flex-wrap">
            {message.metadata.targetElements.map((e) => (
              <Badge key={e} variant="secondary">
                {ELEMENT_EMOJI[e]}{e}
              </Badge>
            ))}
          </div>
        )}

        {/* 内容 */}
        <div className="prose prose-sm max-w-none text-foreground">
          {isStreaming && message.type === 'token' ? (
            <TypewriterText text={message.content} speed={20} />
          ) : (
            message.content
          )}
          {isStreaming && <span className="animate-pulse">▊</span>}
        </div>

        {/* 推荐卡片 */}
        {message.metadata?.items && message.metadata.items.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
            {message.metadata.items.map((item, index) => (
              <RecommendCard key={item.item_code} item={item} index={index} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
```

## 验收动作

1. **全流程测试**
   - 输入"明天面试"，点击发送
   - 观察：analysis → items → token 逐字显示 → done
   - 卡片依次滑入，有动画效果

2. **错误处理**
   - 关闭后端服务，发送消息
   - 应显示"连接失败"提示

## 验收标准
- [ ] SSE 流式数据正确解析，各阶段（analysis/items/token/done）正常显示
- [ ] 打字机效果：文字逐字流出，非等待后蹦出
- [ ] 推荐卡片使用 AnimatePresence，依次滑入
- [ ] 卡片显示：占位图、名称、五行标签、匹配度
- [ ] 错误时显示友好提示，不白屏
- [ ] 对话历史持久化，刷新不丢失
- [ ] 并发请求时只保留最后一个连接
