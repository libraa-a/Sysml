export type SysmlRole = 'user'

export type Identity = {
  username: string
  role: SysmlRole
  display?: string
  token?: string
  exp?: number
}

export type ProjectMember = {
  username: string
  role: 'owner' | 'editor' | 'viewer'
}

export type Project = {
  id: string
  name: string
  description?: string
  organization?: string
  owner?: string
  visibility?: 'private' | 'shared'
  kind?: 'workspace' | 'shared' | 'copy'
  members?: ProjectMember[]
  member_count?: number
  source_project_id?: string
  published_from?: string
  published_by?: string
  published_at?: string
  copied_from?: string
  copied_by?: string
  copied_at?: string
  updated_at?: string
  created_at?: string
  branches?: number
  elements?: number
  documents?: number
  views?: number
  commits?: number
  tags?: number
}

export type ProjectPayload = {
  id?: string
  name?: string
  organization?: string
  description?: string
  members?: string | Array<{ username: string; role?: 'owner' | 'editor' | 'viewer' }>
}

export type Branch = {
  name: string
  head?: string
  created_at?: string
  elements?: number
  documents?: number
}

export type Tag = {
  id: string
  name: string
  commit: string
  description?: string
  created_at: string
  author?: string
  model_hash?: string
  element_count?: number
}

export type Relation = {
  type: string
  target: string
}

export type SysmlElement = {
  id: string
  type: string
  name: string
  stereotype?: string
  description?: string
  owner?: string
  attributes?: Record<string, unknown>
  relations?: Relation[]
}

export type Metamodel = {
  types: Record<
    string,
    {
      stereotype?: string
      required_attributes?: string[]
      relations?: Record<string, string[]>
    }
  >
  type_prefix: Record<string, string>
  type_labels: Record<string, string>
  relation_labels: Record<string, string>
  diagram_types: Record<
    string,
    {
      label: string
      types: string[]
      relations: string[]
    }
  >
}

export type ValidationIssue = {
  severity: 'error' | 'warning' | 'info'
  element_id: string
  message: string
}

export type ValidationPayload = {
  summary: {
    errors: number
    warnings: number
    infos: number
    elements: number
  }
  issues: ValidationIssue[]
}

export type DiagramNode = {
  id: string
  name: string
  type: string
  label: string
  x: number
  y: number
  width: number
  height: number
}

export type DiagramEdge = {
  source: string
  target: string
  type: string
  label: string
}

export type DiagramPayload = {
  type: string
  label: string
  nodes: DiagramNode[]
  edges: DiagramEdge[]
  view?: SysmlElement
}

export type ViewPayload = {
  view: SysmlElement
  viewpoint?: SysmlElement | null
  view_query?: Record<string, unknown>
  viewpoint_default_query?: Record<string, unknown>
  effective_query?: Record<string, unknown>
  root_element_ids: string[]
  manual_element_ids: string[]
  query_element_ids: string[]
  automatic_element_ids: string[]
  overlap_element_ids: string[]
  content_element_ids: string[]
  manual_elements: SysmlElement[]
  query_elements: SysmlElement[]
  automatic_elements: SysmlElement[]
  content_elements: SysmlElement[]
  elements: SysmlElement[]
  element_count: number
  element_ids: string[]
  content_count?: number
  content_summary?: Record<string, number>
  summary: Record<string, number>
  scope_breakdown?: {
    manual: number
    query: number
    automatic: number
    overlap: number
    content: number
  }
}

export type TraceRef = {
  id: string
  name: string
  type: string
}

export type TraceabilityRow = {
  requirement: TraceRef
  satisfied_by: TraceRef[]
  verified_by: TraceRef[]
  refined_by?: TraceRef[]
  constrained_by?: TraceRef[]
  status: 'closed' | 'partial' | 'open'
}

export type Commit = {
  id: string
  branch: string
  message: string
  author: string
  created_at: string
  element_count: number
  model_hash?: string
}

export type AuditEvent = {
  action: string
  branch_name?: string
  actor: string
  created_at: string
  element_id?: string
  detail?: Record<string, unknown>
}

export type DiffPayload = {
  from: string
  to: string
  summary: {
    added: number
    removed: number
    modified: number
  }
  added: SysmlElement[]
  removed: SysmlElement[]
  modified: {
    id: string
    name: string
    changes: { field: string }[]
  }[]
}

export type DocumentRecord = {
  id: string
  title?: string
  created_at: string
  model_hash: string
  html?: string
  markdown?: string
  pdf_base64?: string
}

export type AiDocgenMode = 'full' | 'summary' | 'trace' | 'review'

export type AiDocgenDraft = {
  template: string
  model: string
  mode: AiDocgenMode
  summary: {
    element_count: number
    type_counts: Record<string, number>
    validation: Record<string, unknown>
  }
}

export type AiModelReview = {
  review: string
  model: string
  summary: AiDocgenDraft['summary']
}

export type AiClosureSuggestion = {
  requirement_id: string
  requirement_name?: string
  status?: 'open' | 'partial'
  missing?: string[]
  rationale?: string
  suggested_test_case?: SysmlElement | null
  suggested_constraint?: SysmlElement | null
  suggested_relations?: Relation[]
}

export type AiClosureSuggestionResponse = {
  suggestions: AiClosureSuggestion[]
  raw: string
  model: string
  summary: AiDocgenDraft['summary']
}

export type AiVersionImpact = {
  analysis: string
  model: string
  from: string
  to: string
  summary: AiDocgenDraft['summary']
}

export type AiDocumentQualityReview = {
  review: string
  model: string
  document_id: string
  summary: AiDocgenDraft['summary']
}

export type AiChatMessage = {
  role: 'user' | 'assistant'
  content: string
  retrieval?: AiChatRetrieval
}

export type AiChatResponse = {
  answer: string
  model: string
  summary: AiDocgenDraft['summary']
  retrieval?: AiChatRetrieval
}

export type AiChatReference = {
  kind: 'element' | 'traceability' | 'validation'
  id: string
  label: string
  score: number
}

export type AiChatRetrieval = {
  query_tokens?: string[]
  references?: AiChatReference[]
  elements?: Array<Record<string, unknown>>
  traceability?: Array<Record<string, unknown>>
  validation_issues?: Array<Record<string, unknown>>
}

export type MdkAdapter = {
  id: string
  label: string
  can_read: boolean
  can_write: boolean
  can_validate: boolean
  can_commit: boolean
  can_rollback: boolean
  formats: string[]
  vendor?: string
  version?: string
  supported_extensions?: string[]
  input_mime_types?: string[]
  output_formats?: string[]
  schema_version?: string
  limitations?: string[]
}

export type MappingReportEntry = Record<string, unknown>

export type MappingReport = {
  adapter: string
  imported: number
  skipped: MappingReportEntry[]
  converted: MappingReportEntry[]
  downgraded: MappingReportEntry[]
  warnings: string[]
}

export type MdkParsePayload = {
  filename?: string
  tool?: string
  adapter?: string
  format?: string
  content: string | Record<string, unknown>
}

export type MdkParseResponse = {
  parsed_model: {
    name: string
    type: string
    adapter: string
    elements: SysmlElement[]
    element_count: number
  }
  mapping_report: MappingReport
}

export type MdkImportJob = {
  id: string
  status: 'parsed' | 'applied'
  project: string
  branch: string
  adapter: string
  filename: string
  created_at: string
  created_by: string
  applied_at?: string
  applied_by?: string
  parsed_model: MdkParseResponse['parsed_model']
  mapping_report: MappingReport
  apply_result?: {
    imported?: number
    commit?: Commit
    mapping_report?: MappingReport
  } | null
}

export type PasswordResetRequest = {
  request_id: string
  delivery: string
  code: string
  expires_at: number
}

export type PasswordResetVerify = {
  request_id: string
  username: string
  verified: boolean
}

type ApiOptions = RequestInit & {
  identity?: Identity | null
  role?: SysmlRole
}

const apiBase = (import.meta.env.VITE_SYSML_API_BASE || '').replace(/\/$/, '')

const identityStorageKey = 'sysml_identity'
const tokenStorageKey = 'sysml_token'

export function loadIdentity(): Identity | null {
  const stored = window.localStorage.getItem(identityStorageKey)
  if (!stored) return null
  try {
    return JSON.parse(stored) as Identity
  } catch {
    window.localStorage.removeItem(identityStorageKey)
    window.localStorage.removeItem(tokenStorageKey)
    return null
  }
}

export function saveIdentity(identity: Identity | null) {
  if (!identity) {
    window.localStorage.removeItem(identityStorageKey)
    window.localStorage.removeItem(tokenStorageKey)
    return
  }
  window.localStorage.setItem(identityStorageKey, JSON.stringify(identity))
  if (identity.token) {
    window.localStorage.setItem(tokenStorageKey, identity.token)
  }
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const identity = options.identity ?? loadIdentity()
  const headers = new Headers(options.headers)
  headers.set('Content-Type', headers.get('Content-Type') || 'application/json')
  headers.set('X-User', identity?.username || 'engineer')
  headers.set('X-Role', identity?.role || options.role || 'user')

  const token = identity?.token || window.localStorage.getItem(tokenStorageKey)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = response.statusText
    const errorText = await response.text()
    try {
      const payload = JSON.parse(errorText)
      message = payload.error || payload.detail || message
    } catch {
      message = errorText
    }
    throw new Error(message || '请求失败')
  }

  const contentType = response.headers.get('Content-Type') || ''
  if (contentType.includes('application/json')) {
    return response.json() as Promise<T>
  }
  return response.text() as T
}

export async function login(username: string, password: string) {
  return api<{ identity: Identity }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    identity: null,
  })
}

export async function register(username: string, password: string) {
  return api<{ identity: Identity }>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password, role: 'user' }),
    identity: null,
  })
}

export async function publishProject(
  projectId: string,
  payload: ProjectPayload,
  options: ApiOptions = {}
) {
  return api<{ project: Project }>(
    `/api/projects/${encodeURIComponent(projectId)}/publish`,
    {
      ...options,
      method: 'POST',
      body: JSON.stringify(payload),
    }
  )
}

export async function copySharedProject(
  projectId: string,
  payload: ProjectPayload = {},
  options: ApiOptions = {}
) {
  return api<{ project: Project }>(
    `/api/projects/${encodeURIComponent(projectId)}/copy`,
    {
      ...options,
      method: 'POST',
      body: JSON.stringify(payload),
    }
  )
}

export async function requestPasswordReset(email: string) {
  return api<PasswordResetRequest>('/api/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
    identity: null,
  })
}

export async function verifyPasswordResetCode(requestId: string, code: string) {
  return api<PasswordResetVerify>('/api/auth/reset-password/verify', {
    method: 'POST',
    body: JSON.stringify({ request_id: requestId, code }),
    identity: null,
  })
}

export async function setNewPassword(requestId: string, password: string) {
  return api<{ username: string; reset: boolean }>('/api/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ request_id: requestId, password }),
    identity: null,
  })
}

export function defaultElement(
  type: string,
  metamodel: Metamodel | null
): SysmlElement {
  const modelType = metamodel?.types[type]
  const attributes = Object.fromEntries(
    (modelType?.required_attributes || []).map((key) => [key, ''])
  )
  if (type === 'View') {
    Object.assign(attributes, {
      viewpoint: '',
      viewpoint_id: '',
      included_elements: [],
      query: {
        types: [],
        owners: [],
        text: '',
        relation_depth: 1,
        relations: [],
      },
      doc_section_title: '',
    })
  }
  if (type === 'Viewpoint') {
    Object.assign(attributes, {
      purpose: '',
      allowed_types: ['Requirement', 'Block', 'TestCase'],
      required_types: ['Requirement'],
      allowed_relations: ['satisfy', 'verify'],
      default_query: {
        types: ['Requirement', 'Block', 'TestCase'],
        owners: [],
        text: '',
        relation_depth: 1,
        relations: ['satisfy', 'verify'],
      },
      document_template: 'summary-trace-validation',
    })
  }
  return {
    id: '',
    type,
    name: '',
    stereotype: modelType?.stereotype || type.toLowerCase(),
    owner: '',
    description: '',
    attributes,
    relations: [],
  }
}
