// 场景选择 → 推荐输入框联动工具
// 点击「常用场景」后将场景名称自动填充到 ChatInput 输入框，减少手动输入步骤。
// 通过 CustomEvent 跨组件通知；若输入框尚未挂载（如当前处于其他 Tab），
// 则暂存到 pendingAutofill，待 ChatInput 挂载时消费，保证联动不丢失。

const AUTOFILL_EVENT = 'chat-input-autofill'

let pendingAutofill: string | null = null

/** 请求将文本填充到推荐输入框（空字符串表示清除联动填充） */
export function requestChatInputAutofill(text: string) {
  pendingAutofill = text
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent<string>(AUTOFILL_EVENT, { detail: text }))
  }
}

/** ChatInput 挂载时消费挂载前产生的联动文本（消费后清空） */
export function consumePendingChatAutofill(): string | null {
  const value = pendingAutofill
  pendingAutofill = null
  return value
}

/** 订阅联动填充事件，返回取消订阅函数 */
export function onChatInputAutofill(handler: (text: string) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<string>).detail || '')
  window.addEventListener(AUTOFILL_EVENT, listener)
  return () => window.removeEventListener(AUTOFILL_EVENT, listener)
}
