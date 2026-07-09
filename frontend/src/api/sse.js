import { getToken } from '../utils/auth'

const BASE = import.meta.env.VITE_API_BASE || ''

async function readSSEStream(resp, callbacks) {
  const { onToken, onSources, onDone, onError } = callbacks

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
    buffer = lines.pop()

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

export async function streamChat(sessionId, content, callbacks, attachmentText = null, attachmentName = null) {
  const token = getToken()

  const body = { content }
  if (attachmentText) {
    body.attachment_text = attachmentText
    body.attachment_name = attachmentName
  }

  const resp = await fetch(`${BASE}/api/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify(body),
  })

  await readSSEStream(resp, callbacks)
}

export async function streamAgentMessage(sessionId, content, callbacks) {
  const token = getToken()

  const resp = await fetch(`${BASE}/api/chat/sessions/${sessionId}/agent-message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify({ content }),
  })

  await readSSEStream(resp, callbacks)
}
