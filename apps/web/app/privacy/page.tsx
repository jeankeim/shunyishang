import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '隐私政策 - 我的个人穿搭',
  description: '我的个人穿搭个人信息保护与隐私政策',
}

/**
 * 隐私政策页（PIPL 合规）
 * 注册勾选与敏感信息同意勾选均链接至本页
 */
export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[var(--brand-surface,#faf9f6)]">
      <div className="max-w-3xl mx-auto px-5 py-10">
        <h1 className="text-2xl font-bold text-[var(--brand-heading,#2c2a26)] mb-2">
          我的个人穿搭隐私政策
        </h1>
        <p className="text-sm text-[var(--brand-subtle,#8a857c)] mb-8">
          更新日期：2026年7月25日　|　生效日期：2026年7月25日
        </p>

        <div className="space-y-8 text-sm leading-relaxed text-[var(--brand-body,#4a463f)]">
          <section>
            <p>
              我的个人穿搭（以下简称"我们"或"本产品"）深知个人信息对您的重要性，我们依据《中华人民共和国个人信息保护法》（PIPL）、《中华人民共和国网络安全法》等法律法规制定本政策，并恪守以下原则：权责一致、目的明确、选择同意、最小必要、确保安全、主体参与、公开透明。请您在注册和使用本产品前仔细阅读本政策。
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">一、我们收集的个人信息</h2>
            <h3 className="font-medium mb-2">1. 账号信息（注册必需）</h3>
            <p className="mb-3">
              手机号或电子邮箱（二选一，用于账号注册与登录）、登录密码（加盐哈希存储，我们无法获知您的明文密码）、昵称（可选）、性别（可选）。
            </p>
            <h3 className="font-medium mb-2">2. 敏感个人信息（可选，需您单独同意）</h3>
            <p className="mb-2">
              为向您提供基于八字五行的个性化穿搭建议，在您<strong>主动填写并单独勾选同意</strong>后，我们会处理以下敏感个人信息：
            </p>
            <ul className="list-disc pl-5 space-y-1 mb-3">
              <li>出生日期</li>
              <li>出生时辰</li>
              <li>出生地点</li>
            </ul>
            <p className="mb-3">
              <strong>特别提示</strong>：上述信息属于《个人信息保护法》定义的敏感个人信息。拒绝提供不影响您使用本产品的基础功能（浏览穿搭内容、管理个人衣橱等），仅会导致八字五行个性化推荐、运势穿搭等功能不可用。上述信息在我们的数据库中采用<strong>应用层加密存储</strong>（AES 对称加密），任何直接查询数据库的行为均无法读取明文。
            </p>
            <h3 className="font-medium mb-2">3. 您主动上传的内容</h3>
            <p className="mb-3">
              衣橱单品照片、个人头像、穿搭日记内容等。照片仅用于为您展示和生成穿搭建议，不会用于其他用途。
            </p>
            <h3 className="font-medium mb-2">4. 自动收集的信息</h3>
            <p>
              为保障服务安全与稳定，我们会记录您的 IP 地址、访问时间、设备类型等日志信息（用于接口限流、防刷与故障排查），保存期限不超过 6 个月。
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">二、我们如何使用您的信息</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>账号信息：用于注册、登录、找回账号与安全验证</li>
              <li>出生信息：仅用于计算八字五行属性，生成个性化穿搭色彩与材质建议</li>
              <li>衣橱照片：仅用于您本人的衣橱管理与穿搭组合展示</li>
              <li>日志信息：仅用于安全防护、限流与故障排查</li>
            </ul>
            <p className="mt-3">
              我们<strong>不会</strong>将您的个人信息用于广告投放、用户画像售卖，也不会向任何第三方出售您的个人信息。
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">三、信息的存储与保护</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>存储地点：您的个人信息存储于中华人民共和国境内的服务器，不出境</li>
              <li>敏感信息加密：出生日期、时辰、地点采用应用层对称加密后落库</li>
              <li>密码保护：登录密码采用不可逆加盐哈希算法存储</li>
              <li>传输安全：全站强制 HTTPS 加密传输</li>
              <li>存储期限：您的个人信息在账号存续期间保存；注销账号后立即删除（详见第五条）</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">四、第三方服务</h2>
            <p className="mb-2">为实现产品功能，我们接入了以下第三方服务，仅共享实现功能所必需的最少信息：</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>阿里云对象存储（OSS）：存储您上传的照片与生成的穿搭图片</li>
              <li>阿里云百炼大模型服务：生成穿搭建议文案（传输内容为五行属性与衣物描述，<strong>不包含</strong>您的出生日期等原始敏感信息与真实身份信息）</li>
              <li>天气服务提供商：根据您选择的城市获取天气数据（仅传输城市名称）</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">五、您的权利</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong>查阅与更正</strong>：您可随时在「个人资料」页查看和修改您的个人信息</li>
              <li><strong>撤回同意</strong>：您可在「个人资料」页清空出生信息，撤回对敏感信息处理的同意</li>
              <li>
                <strong>注销账号</strong>：您可在「个人资料」页申请注销账号。注销后，我们将<strong>立即且不可恢复地删除</strong>您的全部个人信息，包括账号信息、出生信息、衣橱数据、上传的照片、穿搭日记等
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">六、未成年人保护</h2>
            <p>
              本产品面向成年人提供服务。若您为未满 14 周岁的未成年人，请在监护人陪同下阅读本政策，并在取得监护人同意后使用本产品。
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">七、免责与功能性质说明</h2>
            <p>
              本产品提供的八字五行分析结果仅作为服饰色彩与风格搭配的<strong>文化参考</strong>，属于传统文化娱乐与穿搭辅助建议，不构成任何形式的命运预测、医疗、投资或其他专业意见。
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--brand-heading,#2c2a26)] mb-3">八、本政策的更新与联系我们</h2>
            <p className="mb-3">
              本政策更新时，我们将在本页面发布更新版本并标注更新日期；涉及敏感个人信息处理方式的重大变更，我们将重新征得您的同意。
            </p>
            <p>
              如您对本政策或个人信息处理有任何疑问、意见或投诉，可通过产品内反馈渠道与我们联系，我们将在 15 个工作日内答复。
            </p>
          </section>
        </div>

        <div className="mt-10 pt-6 border-t border-[var(--brand-border,#e5e0d8)]/60 text-center">
          <a
            href="/"
            className="text-sm text-[var(--wuxing-wood,#3DA35D)] hover:underline"
          >
            返回首页
          </a>
        </div>
      </div>
    </div>
  )
}
