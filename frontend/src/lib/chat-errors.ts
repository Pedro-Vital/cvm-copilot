import { APICallError } from 'ai'

import { ApiError } from '@/lib/api'

export interface ChatErrorInfo {
  title: string
  message: string
  sessionExpired: boolean
}

const NETWORK: ChatErrorInfo = {
  title: 'Sem conexão com o servidor',
  message: 'Não foi possível alcançar a API. Verifique sua conexão e se o backend está no ar.',
  sessionExpired: false,
}

function fromStatus(status: number): ChatErrorInfo | null {
  if (status === 401) {
    return {
      title: 'Sessão expirada',
      message: 'Sua sessão expirou. Entre novamente para continuar.',
      sessionExpired: true,
    }
  }
  if (status === 403 || status === 404) {
    return {
      title: 'Conversa indisponível',
      message: 'Esta conversa não existe ou pertence a outro usuário.',
      sessionExpired: false,
    }
  }
  return null
}

/**
 * Maps the three ways a chat request fails to something an analyst can act on:
 * HTTP errors before the stream starts (APICallError / ApiError), fetch
 * rejections (network down or CORS — the browser hides which), and `error`
 * events inside the stream, whose text the backend already writes for the
 * analyst (grounding failure, retrieval failure, ...).
 */
export function describeChatError(error: Error): ChatErrorInfo {
  if (error instanceof ApiError) {
    if (error.isNetworkError) return NETWORK
    return fromStatus(error.status) ?? { title: 'Erro no servidor', message: error.message, sessionExpired: false }
  }
  if (APICallError.isInstance(error)) {
    return (
      fromStatus(error.statusCode ?? 0) ?? {
        title: 'Erro no servidor',
        message: 'O servidor não conseguiu processar a pergunta. Tente novamente em instantes.',
        sessionExpired: false,
      }
    )
  }
  if (error instanceof TypeError) return NETWORK
  return { title: 'Não foi possível concluir a resposta', message: error.message, sessionExpired: false }
}
