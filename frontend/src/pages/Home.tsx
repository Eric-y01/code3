import { useEffect, useRef, useState } from 'react'
import type { AppConfig, Example } from '../types'
import { uploadImage } from '../api'

interface Props {
  config: AppConfig | null
  examples: Example[]
  onStartExample: (slug: string, productName: string, description: string) => void
  onStartUpload: (fileId: string, productName: string, description: string) => void
}

export default function Home({ config, examples, onStartExample, onStartUpload }: Props) {
  const [preview, setPreview] = useState<string>('')
  const [fileId, setFileId] = useState<string>('')
  const [productName, setProductName] = useState('')
  const [description, setDescription] = useState('')
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const isMock = config?.is_mock ?? true

  const handleSelect = async (f: File) => {
    setPreview(URL.createObjectURL(f))
    setBusy(true)
    try {
      const res = await uploadImage(f, productName, description)
      setFileId(res.file_id)
    } catch (e: any) {
      alert('上传失败：' + e.message)
      setPreview('')
      setFileId('')
    } finally {
      setBusy(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleSelect(f)
  }

  const onAnalyze = () => {
    if (!fileId) return
    if (isMock && !productName.trim()) {
      alert('演示模式请先在上方填写「商品名称」\n（如：保温杯 / 咖啡杯 / 耳机），\n系统才能匹配最接近的演示模板。')
      return
    }
    onStartUpload(fileId, productName, description)
  }

  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview) }
  }, [preview])

  return (
    <div>
      <div className="header card">
        <div>
          <h1>AI 电商运营助手</h1>
          <div style={{ color: 'var(--muted)', fontSize: '.9rem', marginTop: 4 }}>
            上传商品图 → 智能分析 → 生成标题/卖点/详情/脚本 → 运营报告
          </div>
        </div>
        <div className={`badge ${isMock ? 'mock' : 'real'}`}>
          {isMock ? '演示模式（Mock）' : '真实模型'}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <h3 style={{ marginTop: 0 }}>1. 上传商品图片</h3>
        {isMock && (
          <div className="error-box" style={{ background: '#fff7ed', color: '#9a3412' }}>
            当前为 <strong>Mock 演示模式</strong>（未配置 OPENAI_API_KEY）。上传图片后可点击下方「生成演示报告」：
            系统不会识别图片像素，而是按你填写的「商品名称」匹配最接近的内置模板（保温杯 / 咖啡杯 / 耳机）
            生成一份结构完整的演示报告。想真正 AI 分析自己的图片，请在 <code>.env</code> 中配置
            <code> OPENAI_API_KEY </code> 后重启。
          </div>
        )}

        {!preview ? (
          <div
            className={`upload-zone ${drag ? 'dragover' : ''}`}
            onDragOver={e => { e.preventDefault(); setDrag(true) }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
          >
            <div style={{ fontSize: '2rem', marginBottom: 8 }}>⬆️</div>
            <div>点击或拖拽上传图片（jpg / png / webp）</div>
            <div style={{ fontSize: '.8rem', marginTop: 8 }}>建议单张商品图，背景干净效果更佳</div>
            <input ref={inputRef} type="file" accept="image/*" hidden
                   onChange={e => e.target.files?.[0] && handleSelect(e.target.files[0])} />
          </div>
        ) : (
          <div style={{ textAlign: 'center' }}>
            <img src={preview} alt="preview" style={{ maxHeight: 220, borderRadius: 12, border: '1px solid var(--border)' }} />
            <div style={{ marginTop: 10 }}>
              <button className="btn-secondary" onClick={() => { setPreview(''); setFileId('') }}>重新上传</button>
            </div>
          </div>
        )}

        <label className="field-label">商品名称{isMock ? '（演示模式必填）' : '（可选）'}</label>
        <input className="input-field" placeholder={isMock ? '如：智能保温杯 / 北欧咖啡杯 / 头戴耳机' : '如：智能保温杯'}
               value={productName} onChange={e => setProductName(e.target.value)} />

        <label className="field-label">补充说明（材质/品牌/价格等事实信息，可选）</label>
        <textarea className="input-field" rows={3}
                  placeholder="如：304不锈钢内胆，400ml，¥129"
                  value={description} onChange={e => setDescription(e.target.value)} />

        <button className="btn-primary"
                disabled={!fileId || busy || (isMock && !productName.trim())}
                title={isMock && !productName.trim() ? '演示模式需先填写商品名称' : ''}
                onClick={onAnalyze} style={{ marginTop: 16, width: '100%' }}>
          {busy ? '上传中…'
            : isMock && !productName.trim() ? '请先填写商品名称'
            : isMock ? '生成演示报告（Mock）'
            : 'AI 分析商品'}
        </button>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>2. 或一键使用内置示例（无 API Key 可完整演示）</h3>
        <div className="example-grid">
          {examples.map(ex => (
            <div key={ex.slug} className="example-card"
                 onClick={() => onStartExample(ex.slug, ex.suggested_name, ex.description)}>
              <img src={ex.image_url} alt={ex.name} />
              <div className="info">
                <div className="name">{ex.name}</div>
                <div className="tagline">{ex.tagline}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
