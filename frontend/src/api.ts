import type { AppConfig, Example, TaskStatus } from './types'

const headers = { Accept: 'application/json' }

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, { ...init, headers: { ...headers, ...(init?.headers || {}) } })
  } catch {
    // 网络层失败（后端未启动 / 端口不对）→ 给可读中文提示
    throw new Error(
      '无法连接到后端服务（http://' + window.location.host + '）。' +
      '请确认已启动后端：在项目根目录运行 scripts\\start_windows.ps1（或见 README）。'
    )
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({} as any))
    throw new Error(body.detail || `请求失败 ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const getConfig = () => fetchJson<AppConfig>('/api/config')
export const getExamples = () => fetchJson<{ examples: Example[] }>('/api/examples')

export async function uploadImage(file: File, productName: string, description: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('product_name', productName)
  form.append('description', description)
  return fetchJson<{ file_id: string; url: string; image_hash: string }>('/api/uploads', {
    method: 'POST',
    body: form,
  })
}

export async function analyzeExample(exampleId: string, productName: string, description: string) {
  return fetchJson<{ task_id: string; instant: boolean }>('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ example_id: exampleId, product_name: productName, description }),
  })
}

export async function analyzeUpload(fileId: string, productName: string, description: string) {
  return fetchJson<{ task_id: string; instant: boolean }>('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId, product_name: productName, description }),
  })
}

export const getTask = (id: string) => fetchJson<TaskStatus>(`/api/tasks/${id}`)

export async function exportMarkdown(reportId: string) {
  const res = await fetch(`/api/reports/${reportId}/markdown`)
  if (!res.ok) throw new Error('导出失败')
  return res.text()
}
