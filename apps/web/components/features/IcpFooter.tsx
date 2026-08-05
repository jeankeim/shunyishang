'use client'

/**
 * ICP 备案信息页脚
 * 合规要求：网站首页底部必须展示 ICP 备案号，并链接到工信部备案管理系统。
 * 公安联网备案通过后，在下方补充公安备案号（含图标）。
 */
const ICP_NUMBER = '浙ICP备2026060847号'

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
      <p className="mt-1 text-[11px] text-stone-300">
        五行穿搭内容仅供娱乐参考
      </p>
    </footer>
  )
}
