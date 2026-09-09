import { useState } from 'react'
import type { DetailSection, ImagePlan, Meta, Persona, Product, Scene, TaskStatus, Titles } from '../types'
import { exportMarkdown } from '../api'

interface Props {
  status: TaskStatus
  onBack: () => void
  onRestart: () => void
}

export default function ReportPage({ status, onBack, onRestart }: Props) {
  const report = status.report
  if (!report) return null
  const { meta } = report
  const [activeTab, setActiveTab] = useState<keyof Titles>('taobao')
  const [copied, setCopied] = useState('')

  const copy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(key)
      setTimeout(() => setCopied(''), 1500)
    } catch { /* noop */ }
  }

  const handleExport = async () => {
    if (!meta.report_id) return
    const md = await exportMarkdown(meta.report_id)
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `AI运营报告-${report.product.product_name || '商品'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="card report-header">
        <div>
          <h1 style={{ margin: '0 0 6px' }}>AI 电商商品运营报告</h1>
          <div className="report-meta">
            生成时间：{meta.generated_at} · {meta.is_mock ? '演示模式' : '真实模型'} · {meta.provider}
            {meta.from_cache ? ' · 命中缓存' : ''}
          </div>
        </div>
        <div className="no-print" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn-primary" onClick={handleExport}>导出 Markdown</button>
          <button className="btn-secondary" onClick={() => window.print()}>打印 / 存 PDF</button>
          <button className="btn-secondary" onClick={onRestart}>重新分析</button>
          <button className="btn-ghost" onClick={onBack}>返回</button>
        </div>
      </div>

      <ImagesSection meta={meta} />
      <ProductSection product={report.product} />
      <PersonaSection persona={report.persona} />
      <TitlesSection titles={report.titles} active={activeTab} setActive={setActiveTab} />
      <SellingSection items={report.selling_points.items} />
      <DetailSectionView sections={report.detail_sections.sections} />
      <VideoSection script={report.video_script} />
      <ImagePlansSection plans={report.image_plans.plans} copied={copied} onCopy={copy} />

      <div className="card" style={{ marginTop: 20, color: 'var(--muted)', fontSize: '.85rem' }}>
        提示：本报告由 AI 生成，发布前请结合商品事实信息（材质、价格、规格等）人工审核；视觉推断结果已标注来源，不可见属性请补充说明。
      </div>
    </div>
  )
}

function ImagesSection({ meta }: { meta: Meta }) {
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title">商品图 & 主体识别</div>
      <div className="image-compare">
        <div className="image-box">
          <img src={meta.image_url} alt="原图" />
          <div className="caption">原图（分析链路始终使用原图）</div>
        </div>
        {meta.cutout_url ? (
          <div className="image-box">
            <img src={meta.cutout_url} alt="抠图" />
            <div className="caption">商品主体抠图（仅展示链路）</div>
          </div>
        ) : (
          <div className="image-box degrade">
            <div>未生成透明抠图</div>
            <div style={{ fontSize: '.8rem', marginTop: 4, lineHeight: 1.6 }}>
              {meta.cutout_note || '抠图服务未启用或模型下载失败，已自动降级为原图展示。'}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ProductSection({ product }: { product: Product }) {
  if (!product) return null
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title">商品智能分析</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        <div><span className="subsection">名称：</span>{product.product_name || '—'}</div>
        <div><span className="subsection">品类：</span>{product.category || '—'}</div>
        <div><span className="subsection">风格：</span>{product.style || '—'}</div>
      </div>

      <div className="subsection" style={{ marginTop: 14 }}>外观特征（视觉推断）</div>
      <div>
        {(product.appearance ?? []).map((a, i) => (
          <span key={i} className="tag source-visual">{a.aspect}：{a.detail}</span>
        ))}
      </div>

      <div className="subsection" style={{ marginTop: 14 }}>适用场景</div>
      <div>
        {(product.scenes ?? []).map((s, i) => <span key={i} className="tag">{s}</span>)}
      </div>

      {product.user_provided?.length > 0 && (
        <>
          <div className="subsection" style={{ marginTop: 14 }}>用户提供事实信息</div>
          <div>
            {product.user_provided.map((u, i) => (
              <span key={i} className="tag source-user">{u.field}：{u.value}</span>
            ))}
          </div>
        </>
      )}

      {product.visual_uncertainty?.length > 0 && (
        <>
          <div className="subsection" style={{ marginTop: 14 }}>视觉不确定（建议补充）</div>
          <div>
            {product.visual_uncertainty.map((u, i) => (
              <span key={i} className="tag warn">{u}</span>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function PersonaSection({ persona }: { persona: Persona }) {
  if (!persona?.name) return null
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title">目标用户画像</div>
      <div className="persona-grid">
        <PersonaItem label="画像代号" value={persona.name} />
        <PersonaItem label="年龄" value={persona.age_range} />
        <PersonaItem label="职业" value={persona.occupation} />
        <PersonaItem label="消费能力" value={persona.spending_power} />
        <PersonaItem label="购买场景" value={(persona.purchase_scenes ?? []).join('、')} />
        <PersonaItem label="购买动机" value={(persona.motivations ?? []).join('、')} />
        <PersonaItem label="痛点" value={(persona.pain_points ?? []).join('、')} />
        <PersonaItem label="营销切入点" value={persona.marketing_angle} />
      </div>
    </div>
  )
}

function PersonaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="persona-item">
      <div className="label">{label}</div>
      <div className="value">{value || '—'}</div>
    </div>
  )
}

function TitlesSection({ titles, active, setActive }: { titles: Titles; active: keyof Titles; setActive: (k: keyof Titles) => void }) {
  const labels: Record<keyof Titles, string> = { taobao: '淘宝版', jd: '京东版', xiaohongshu: '小红书版' }
  const t = titles?.[active] || { title: '', rationale: '' }
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title">三平台标题</div>
      <div className="tabs">
        {(Object.keys(labels) as (keyof Titles)[]).map(k => (
          <div key={k} className={`tab ${active === k ? 'active' : ''}`} onClick={() => setActive(k)}>{labels[k]}</div>
        ))}
      </div>
      <div className="title-card">
        <div style={{ fontSize: '1.05rem', fontWeight: 700 }}>{t.title}</div>
        <div className="rationale">{t.rationale}</div>
      </div>
    </div>
  )
}

function SellingSection({ items }: { items: { title: string; detail: string }[] }) {
  const list = items ?? []
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title">五点卖点</div>
      <ol className="selling-list">
        {list.map((it, i) => (
          <li key={i}><strong>{it.title}</strong><br /><span style={{ color: 'var(--muted)' }}>{it.detail}</span></li>
        ))}
      </ol>
    </div>
  )
}

function DetailSectionView({ sections }: { sections: DetailSection[] }) {
  const list = sections ?? []
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title">商品详情页文案</div>
      {list.map((s, i) => (
        <div key={i} className="detail-section">
          <h4>{s.heading}</h4>
          <p>{s.content}</p>
        </div>
      ))}
    </div>
  )
}

function VideoSection({ script }: { script: { title: string; hook: string; format: string; scenes: Scene[]; ending_call: string; hashtags: string[] } }) {
  if (!script) return null
  const scenes = script.scenes ?? []
  const hashtags = script.hashtags ?? []
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title">短视频脚本</div>
      <div style={{ marginBottom: 10 }}><strong>标题：</strong>{script.title}</div>
      <div style={{ marginBottom: 10 }}><strong>形式：</strong>{script.format}</div>
      <div className="title-card" style={{ marginBottom: 16 }}>
        <strong>前三秒钩子：</strong>{script.hook}
      </div>
      <table className="script-table">
        <thead>
          <tr><th>镜号</th><th>时间</th><th>画面</th><th>展示点</th><th>旁白</th></tr>
        </thead>
        <tbody>
          {scenes.map((sc, i) => (
            <tr key={i}>
              <td>{sc.no}</td><td>{sc.time}</td><td>{sc.visual}</td><td>{sc.focus}</td><td>{sc.voiceover}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 14 }}><strong>结尾转化：</strong>{script.ending_call}</div>
      <div style={{ marginTop: 6 }}><strong>话题标签：</strong>{hashtags.map(h => '#' + h).join(' ')}</div>
    </div>
  )
}

function ImagePlansSection({ plans, copied, onCopy }: { plans: ImagePlan[]; copied: string; onCopy: (t: string, k: string) => void }) {
  const list = plans ?? []
  const rows: { key: string; label: string }[] = [
    { key: 'subject', label: '主体' },
    { key: 'scene', label: '场景道具' },
    { key: 'lighting', label: '光线影调' },
    { key: 'composition', label: '构图机位' },
    { key: 'style', label: '风格质感' },
  ]
  const copyAll = () => {
    const all = list
      .map((p) => [
        `【${p.name}】（${p.ratio} · ${p.usage}）`,
        p.prompt,
        p.negative_prompt ? `负向：${p.negative_prompt}` : '',
      ].filter(Boolean).join('\n'))
      .join('\n\n')
    if (all) onCopy(all, 'all-plans')
  }
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="plan-section-header">
        <div className="section-title">AI 营销图片方案</div>
        {list.length > 1 && (
          <button className="btn-secondary btn-sm" onClick={copyAll}>
            {copied === 'all-plans' ? '已全部复制' : '复制全部 Prompt'}
          </button>
        )}
      </div>
      <p className="section-hint">
        提示词已按「主体 / 场景道具 / 光线影调 / 构图机位 / 风格质感」拆解，可直接把下方完整 Prompt 粘贴到 即梦、Midjourney、Stable Diffusion 等 AI 绘图工具使用。
      </p>
      <div className="plan-grid">
        {list.map((p, i) => (
          <div key={i} className="plan-card">
            <div className="plan-head">
              <span className="plan-name">{p.name}</span>
              <span className="plan-ratio">{p.ratio}</span>
            </div>
            <div className="plan-usage">用途：{p.usage}</div>
            {rows.map((r) => {
              const text = (p as unknown as Record<string, string>)[r.key] || ''
              return text ? (
                <div key={r.key} className="plan-row">
                  <span className="plan-row-label">{r.label}</span>
                  <span>{text}</span>
                </div>
              ) : null
            })}
            <div className="plan-prompt-label">完整正向 Prompt（可直接复制）</div>
            <div className="prompt">{p.prompt}</div>
            {p.negative_prompt && (
              <div className="plan-row negative"><span className="plan-row-label">负向</span><span>{p.negative_prompt}</span></div>
            )}
            {p.tip && <div style={{ fontSize: '.82rem', marginTop: 6, color: 'var(--muted)' }}><strong>建议：</strong>{p.tip}</div>}
            <button className="btn-secondary" style={{ marginTop: 10, width: '100%' }}
                    onClick={() => onCopy(p.prompt, `${p.name}-${i}`)}>
              {copied === `${p.name}-${i}` ? '已复制' : '复制 Prompt'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
