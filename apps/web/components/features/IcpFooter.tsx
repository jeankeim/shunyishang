'use client'

import Image from 'next/image'

/**
 * 备案信息页脚
 * 合规要求：
 * 1. 网站首页底部必须展示 ICP 备案号，并链接到工信部备案管理系统；
 * 2. 公安联网备案通过后 30 日内，将公安备案号（含官方图标）放置在网页底部，
 *    并链接到全国互联网安全管理服务平台查询页。
 */
const ICP_NUMBER = '浙ICP备2026060847号'
const PSB_NUMBER = '浙公网安备33010602014806号'
const PSB_CODE = '33010602014806'

export function IcpFooter() {
  return (
    <footer className="pt-8 pb-2 text-center">
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-stone-400 hover:text-stone-600 transition-colors"
      >
        {ICP_NUMBER}
      </a>
      <div className="mt-1">
        <a
          href={`https://beian.mps.gov.cn/#/query/webSearch?code=${PSB_CODE}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600 transition-colors"
        >
          <Image
            src="/icons/gongan.png"
            alt="公安备案图标"
            width={14}
            height={14}
            className="inline-block"
          />
          {PSB_NUMBER}
        </a>
      </div>
      <p className="mt-1 text-[11px] text-stone-300">
        五行穿搭内容仅供娱乐参考
      </p>
    </footer>
  )
}
