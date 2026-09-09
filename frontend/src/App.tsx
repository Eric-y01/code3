import { Component, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { AppConfig, Example, TaskStatus } from './types'
import { getConfig, getExamples } from './api'
import Home from './pages/Home'
import Processing from './pages/Processing'
import ReportPage from './pages/ReportPage'

// 错误边界：渲染期任何异常都展示可读提示，避免整页白屏
class ErrorBoundary extends Component<{ children: ReactNode }, { message: string }> {
  state = { message: '' }

  static getDerivedStateFromError(e: unknown) {
    return { message: e instanceof Error ? e.message : String(e) }
  }

  render() {
    if (this.state.message) {
      return (
        <div className="card" style={{ marginTop: 18, borderColor: '#fecaca', background: '#fef2f2', color: '#b91c1c' }}>
          <strong>页面渲染出错</strong>
          <div style={{ fontSize: '.88rem', marginTop: 6, lineHeight: 1.7 }}>{this.state.message}</div>
          <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
            <button className="btn-primary" onClick={() => window.location.reload()}>重新加载</button>
            <button className="btn-ghost" onClick={() => this.setState({ message: '' })}>返回</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  const [view, setView] = useState<'home' | 'processing' | 'report'>('home')
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [taskId, setTaskId] = useState<string>('')
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [error, setError] = useState<string>('')
  const [startupError, setStartupError] = useState<string>('')

  useEffect(() => {
    getConfig().then(setConfig).catch((e: Error) => setStartupError(e.message))
    getExamples()
      .then(d => setExamples(d.examples))
      .catch((e: Error) => setStartupError(prev => prev || e.message))
  }, [])

  const startExample = (slug: string, productName: string, description: string) => {
    setError('')
    setTaskId('')
    setTaskStatus(null)
    setView('processing')
    import('./api').then(({ analyzeExample }) =>
      analyzeExample(slug, productName, description)
        .then(r => {
          setTaskId(r.task_id)
          if (r.instant) {
            // 缓存命中会立即返回，Processing 组件会自动完成
          }
        })
        .catch(e => { setError(e.message); setView('home') })
    )
  }

  const startUpload = (fileId: string, productName: string, description: string) => {
    setError('')
    setTaskId('')
    setTaskStatus(null)
    setView('processing')
    import('./api').then(({ analyzeUpload }) =>
      analyzeUpload(fileId, productName, description)
        .then(r => setTaskId(r.task_id))
        .catch(e => { setError(e.message); setView('home') })
    )
  }

  const handleReportReady = (status: TaskStatus) => {
    setTaskStatus(status)
    setView('report')
  }

  return (
    <div className="container">
      {startupError && (
        <div className="error-box no-print" style={{ marginBottom: 16, background: '#fef2f2', color: '#b91c1c', borderColor: '#fecaca' }}>
          <strong>无法连接后端服务</strong>
          <div style={{ fontSize: '.88rem', marginTop: 6, lineHeight: 1.7 }}>
            {startupError}
            <br />
            Windows 一键启动：项目根目录运行 <code>powershell -ExecutionPolicy Bypass -File scripts\start_windows.ps1</code>
            （或手动：<code>cd backend; .venv\Scripts\uvicorn app.main:app --port 8000</code>，再刷新本页）。
          </div>
          <button className="btn-ghost" onClick={() => { setStartupError(''); window.location.reload() }}
                  style={{ marginLeft: 12 }}>重试</button>
        </div>
      )}
      {error && (
        <div className="error-box no-print" style={{ marginBottom: 16 }}>
          {error}
          <button className="btn-ghost" onClick={() => setError('')} style={{ marginLeft: 12 }}>×</button>
        </div>
      )}
      <ErrorBoundary>
        {view === 'home' && (
          <Home
            config={config}
            examples={examples}
            onStartExample={startExample}
            onStartUpload={startUpload}
          />
        )}
        {view === 'processing' && (
          <Processing
            taskId={taskId}
            onDone={handleReportReady}
            onBack={() => setView('home')}
          />
        )}
        {view === 'report' && taskStatus && (
          <ReportPage
            status={taskStatus}
            onBack={() => setView('home')}
            onRestart={() => { setTaskStatus(null); setTaskId(''); setView('home') }}
          />
        )}
      </ErrorBoundary>
    </div>
  )
}
