import { getToken } from '../utils/auth'

const BASE = import.meta.env.VITE_API_BASE || ''

export async function streamChat(sessionId, content, callbacks) {
  const { onToken, onSources, onDone, onError } = callbacks
  const token = getToken()

  const resp = await fetch(`${BASE}/api/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify({ content }),
  })

  if (!resp.ok) {
    onError?.('网络错误')
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // 保留最后不完整的行

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || !trimmed.startsWith('data:')) continue

      const jsonStr = trimmed.slice(5).trim()
      try {
        const event = JSON.parse(jsonStr)
        switch (event.type) {
          case 'token': onToken?.(event.content); break
          case 'sources': onSources?.(event.sources); break
          case 'done': onDone?.(event.message_id); break
          case 'error': onError?.(event.message, event.code); break
          default: break
        }
      } catch (e) {
        console.error('SSE 解析错误:', e, jsonStr)
      }
    }
  }
}
