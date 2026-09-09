import { useEffect, useRef, useState } from 'react'
import type { TaskStatus } from '../types'
import { getTask } from '../api'

interface Props {
  taskId: string
  onDone: (status: TaskStatus) => void
  onBack: () => void
}

export default function Processing({ taskId, onDone, onBack }: Props) {
  const [status, setStatus] = useState<TaskStatus | null>(null)
  const [error, setError] = useState('')
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!taskId) return
    setError('')
    intervalRef.current = setInterval(async () => {
      try {
        const s = await getTask(taskId)
        setStatus(s)
        if (s.status === 'done' && s.report) {
          if (intervalRef.current) clearInterval(intervalRef.current)
          onDone(s)
        } else if (s.status === 'error') {
          if (intervalRef.current) clearInterval(intervalRef.current)
          setError(s.error || '任务失败')
        }
      } catch (e: any) {
        setError(e.message)
      }
    }, 700)
    getTask(taskId).then(setStatus).catch(() => null)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [taskId, onDone])

  const steps = status?.steps || []
  const progress = status?.progress ?? 0

  return (
    <div className="card" style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="header" style={{ marginBottom: 8 }}>
        <div>
          <h1>AI 正在分析商品</h1>
          <div style={{ color: 'var(--muted)', fontSize: '.9rem' }}>请稍候，系统正在调用视觉与文本模型</div>
        </div>
        <button className="btn-secondary no-print" onClick={onBack}>取消</button>
      </div>

      <div className="progress-wrap">
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.9rem', marginBottom: 6 }}>
          <span>总进度</span>
          <span>{progress}%</span>
        </div>
        <div className="progress-bar"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
      </div>

      <div className="step-list">
        {steps.length === 0 && (
          <div className="step running"><div className="dot">●</div><div>任务准备中…</div></div>
        )}
        {steps.map((s, i) => (
          <div key={s.key} className={`step ${s.status}`}>
            <div className="dot">
              {s.status === 'done' ? '✓' : s.status === 'error' ? '!' : i + 1}
            </div>
            <div>{s.label}</div>
          </div>
        ))}
      </div>

      {error && (
        <div className="error-box" style={{ marginTop: 20 }}>
          {error}
          <div style={{ marginTop: 10 }}>
            <button className="btn-secondary" onClick={onBack}>返回重试</button>
          </div>
        </div>
      )}
    </div>
  )
}
