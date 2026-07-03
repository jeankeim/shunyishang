'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CreditCard, Smartphone, Wallet } from 'lucide-react'
import { useMembershipStore } from '@/store/membership'

interface PaymentFormProps {
  plan: 'monthly' | 'yearly'
  price: number
  onSuccess?: () => void
}

const paymentMethods = [
  { id: 'wechat', label: '微信支付', icon: Smartphone, color: 'text-green-600' },
  { id: 'alipay', label: '支付宝', icon: Wallet, color: 'text-blue-600' },
  { id: 'mock', label: '模拟支付', icon: CreditCard, color: 'text-stone-600' },
]

export function PaymentForm({ plan, price, onSuccess }: PaymentFormProps) {
  const { subscribe, isLoading } = useMembershipStore()
  const [selectedMethod, setSelectedMethod] = useState('mock')
  const [showConfirm, setShowConfirm] = useState(false)

  const handleSubscribe = async () => {
    try {
      await subscribe(plan, selectedMethod)
      setShowConfirm(false)
      onSuccess?.()
    } catch {
      // error handled in store
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium text-stone-700 mb-3">选择支付方式</h4>
        <div className="grid grid-cols-3 gap-2">
          {paymentMethods.map((method) => (
            <button
              key={method.id}
              onClick={() => setSelectedMethod(method.id)}
              className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 transition-all duration-200 ${
                selectedMethod === method.id
                  ? 'border-emerald-400 bg-emerald-50'
                  : 'border-stone-200 hover:border-stone-300'
              }`}
            >
              <method.icon className={`w-5 h-5 ${method.color}`} />
              <span className="text-xs font-medium text-stone-600">{method.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between p-4 bg-stone-50 rounded-xl">
        <div>
          <p className="text-sm text-stone-500">应付金额</p>
          <p className="text-2xl font-bold text-stone-800">¥{price}</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setShowConfirm(true)}
          disabled={isLoading}
          className="px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium rounded-xl shadow-sm hover:shadow-md transition-shadow disabled:opacity-50"
        >
          确认支付
        </motion.button>
      </div>

      <AnimatePresence>
        {showConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
            onClick={() => setShowConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-sm w-full mx-4 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-bold text-stone-800 mb-2">确认支付</h3>
              <p className="text-sm text-stone-500 mb-4">
                将使用{paymentMethods.find(m => m.id === selectedMethod)?.label}支付 ¥{price}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowConfirm(false)}
                  className="flex-1 py-2.5 border border-stone-200 rounded-xl text-stone-600 font-medium hover:bg-stone-50"
                >
                  取消
                </button>
                <button
                  onClick={handleSubscribe}
                  disabled={isLoading}
                  className="flex-1 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl font-medium hover:shadow-md disabled:opacity-50"
                >
                  {isLoading ? '处理中...' : '确认'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
