import type { Product } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function imageUrl(path: string): string {
  if (path.startsWith('http')) return path
  const whiteBackgroundPath = path.replace(/^\/media\/products\//, '/media/products_white/')
  return `${API_URL}${whiteBackgroundPath}`
}

export async function fetchProducts(search = ''): Promise<Product[]> {
  const query = search ? `?search=${encodeURIComponent(search)}` : ''
  const response = await fetch(`${API_URL}/api/products${query}`)
  if (!response.ok) throw new Error('We could not load the catalogue.')
  return response.json()
}

export async function fetchProduct(id: string): Promise<Product> {
  const response = await fetch(`${API_URL}/api/products/${encodeURIComponent(id)}`)
  if (!response.ok) throw new Error('That product could not be found.')
  return response.json()
}

export type AuthUser = { id: number; first_name: string; last_name: string; name: string; email: string }
export type AuthResponse = { token: string; user: AuthUser }

async function authRequest(path: string, body: unknown): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_URL}/api/auth/${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.')
  return data
}

export async function login(email: string, password: string): Promise<AuthResponse> { return authRequest('login', { email, password }) as Promise<AuthResponse> }
export async function register(body: { first_name: string; last_name: string; email: string; password: string; confirm_password: string }): Promise<AuthResponse> { return authRequest('register', body) as Promise<AuthResponse> }
export async function requestPasswordPin(email: string): Promise<{ message: string; development_pin?: string }> { return authRequest('forgot-password', { email }) as Promise<{ message: string; development_pin?: string }> }
export async function resetPassword(body: { email: string; pin: string; password: string; confirm_password: string }): Promise<{ message: string }> { return authRequest('reset-password', body) as Promise<{ message: string }> }

export type ChatTurn = { role: 'user' | 'assistant'; content: string }
export type ChatReply = { reply: string; products: Product[]; follow_up_suggestions: string[] }
export type PageContext = { path: string; page_type: string; product_id?: string }
export type ChatHistoryItem = ChatTurn & { products: Product[]; created_at: string }

export async function sendChat(message: string, history: ChatTurn[], pageContext: PageContext): Promise<ChatReply> {
  const token = localStorage.getItem('campus_customs_token')
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ message, history, page_context: pageContext }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The shop assistant is unavailable.')
  return data as ChatReply
}

export async function fetchChatHistory(): Promise<ChatHistoryItem[]> {
  const token = localStorage.getItem('campus_customs_token')
  if (!token) return []
  const response = await fetch(`${API_URL}/api/chat/history`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error('We could not reload your chat history.')
  return response.json()
}
