import {
  useCallback,
  useEffect,
  lazy,
  useMemo,
  Suspense,
  useState,
  type ChangeEvent,
  type FormEvent,
  type ReactNode,
} from 'react'
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  reconnectEdge,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeProps,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
  type OnReconnect,
} from '@xyflow/react'
import {
  AlertCircle,
  Archive,
  Boxes,
  Braces,
  CheckCircle2,
  Code2,
  Download,
  Edit3,
  FileText,
  GitBranch,
  GitCommitHorizontal,
  GitCompare,
  GitMerge,
  LayoutDashboard,
  Loader2,
  LogIn,
  LogOut,
  MessageCircle,
  Network,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  UserCircle,
  Workflow,
  Wrench,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  api,
  type AiDocgenDraft,
  type AiDocgenMode,
  type AiChatMessage,
  type AiChatResponse,
  type AiModelReview,
  defaultElement,
  loadIdentity,
  login,
  saveIdentity,
  type AuditEvent,
  type Branch,
  type Commit,
  type DiagramPayload,
  type DiffPayload,
  type DocumentRecord,
  type Identity,
  type MappingReport,
  type MdkAdapter,
  type MdkImportJob,
  type MdkParseResponse,
  type Metamodel,
  type Project,
  type Relation,
  type SysmlElement,
  type Tag,
  type TraceabilityRow,
  type ValidationPayload,
  type ViewPayload,
} from '@/lib/sysml-api'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ThemeSwitch } from '@/components/theme-switch'

const DocgenTemplateEditor = lazy(() =>
  import('./docgen-template-editor').then((module) => ({
    default: module.DocgenTemplateEditor,
  }))
)

const defaultTemplate = `# {{model:summary}}

## Requirements
{{table:requirements}}

## Blocks
{{table:blocks}}

## Interfaces
{{table:interfaces}}

## Constraints
{{table:constraints}}

## Tests
{{table:tests}}

## Traceability
{{trace:matrix}}

## Validation
{{validation:issues}}
`

const sampleMdkJson = JSON.stringify(
  {
    elements: [
      {
        id: 'REQ-MDK-001',
        name: '外部工具导入需求',
        type: 'Requirement',
        stereotype: 'requirement',
        attributes: {
          text: '系统应支持从外部建模工具导入模型元素。',
          verification: 'Review',
        },
        relations: [],
      },
    ],
  },
  null,
  2
)

const typeNames: Record<string, string> = {
  Requirement: '需求',
  Block: '模块',
  Activity: '活动',
  Interface: '接口',
  Port: '端口',
  Constraint: '约束',
  State: '状态',
  TestCase: '测试',
  View: '视图',
  Viewpoint: '视角',
}

const relationNames: Record<string, string> = {
  satisfy: '满足',
  verify: '验证',
  refine: '细化',
  compose: '组成',
  expose: '暴露端口',
  connect: '连接',
  allocate: '分配',
  flow: '流转',
  transition: '迁移',
  constrain: '约束',
}

const displayTypeNames: Record<string, string> = {
  Requirement: 'Requirement',
  Block: 'Block',
  Activity: 'Activity',
  Interface: 'Interface',
  Port: 'Port',
  Constraint: 'Constraint',
  State: 'State',
  TestCase: 'Test Case',
  View: 'View',
  Viewpoint: 'Viewpoint',
}

const displayDiagramNames: Record<string, string> = {
  requirements: 'Requirements Trace',
  structure: 'Structure & Interface',
  behavior: 'Behavior & State',
  views: 'View-Focused Graph',
  all: 'Full Model Graph',
}

const displayRelationNames: Record<string, string> = {
  satisfy: 'Satisfy',
  verify: 'Verify',
  refine: 'Refine',
  compose: 'Compose',
  expose: 'Expose Port',
  connect: 'Connect',
  allocate: 'Allocate',
  flow: 'Flow',
  transition: 'Transition',
  constrain: 'Constrain',
}

const severityLabels = {
  error: 'Error',
  warning: 'Warning',
  info: 'Info',
}

const workbenchTabs = ['model', 'diagram', 'trace', 'version', 'docgen', 'mdk', 'assistant'] as const

type WorkbenchTab = (typeof workbenchTabs)[number]

type SaveElementInput = {
  element: SysmlElement
  attributesText?: string
  relationsText?: string
  successMessage?: string
  nextSelectedId?: string
}

type SysmlNodeData = {
  element: SysmlElement
  label: string
  onEdit: (id: string) => void
}

type SysmlFlowNode = Node<SysmlNodeData, 'sysml'>

type SysmlEdgeData = {
  relationType: string
  relationLabel: string
}

type SysmlFlowEdge = Edge<SysmlEdgeData, 'smoothstep'> & {
  pathOptions?: {
    borderRadius?: number
    offset?: number
    stepPosition?: number
  }
}

const nodeWidth = 230
const nodeHeight = 116

export function SysmlWorkbench() {
  const [identity, setIdentity] = useState<Identity | null>(() => loadIdentity())
  const [loginForm, setLoginForm] = useState({
    username: identity?.username || 'engineer',
    password: 'engineer123',
  })
  const [role, setRole] = useState(identity?.role || 'author')
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState('')
  const [branches, setBranches] = useState<Branch[]>([])
  const [branch, setBranch] = useState('main')
  const [metamodel, setMetamodel] = useState<Metamodel | null>(null)
  const [elements, setElements] = useState<SysmlElement[]>([])
  const [allElements, setAllElements] = useState<SysmlElement[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [form, setForm] = useState<SysmlElement>(() =>
    defaultElement('Requirement', null)
  )
  const [attributesText, setAttributesText] = useState('{}')
  const [relationsText, setRelationsText] = useState('[]')
  const [validation, setValidation] = useState<ValidationPayload | null>(null)
  const [diagramType, setDiagramType] = useState('requirements')
  const [diagram, setDiagram] = useState<DiagramPayload | null>(null)
  const [views, setViews] = useState<SysmlElement[]>([])
  const [selectedViewId, setSelectedViewId] = useState('all')
  const [viewScope, setViewScope] = useState<ViewPayload | null>(null)
  const [diagramPositions, setDiagramPositions] = useState<
    Record<string, { x: number; y: number }>
  >({})
  const [traceability, setTraceability] = useState<TraceabilityRow[]>([])
  const [commits, setCommits] = useState<Commit[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [diff, setDiff] = useState<DiffPayload | null>(null)
  const [diffFrom, setDiffFrom] = useState('working')
  const [diffTo, setDiffTo] = useState('working')
  const [rollbackCommit, setRollbackCommit] = useState('')
  const [newBranch, setNewBranch] = useState('')
  const [newTag, setNewTag] = useState('')
  const [mergeSource, setMergeSource] = useState('')
  const [forceMerge, setForceMerge] = useState(false)
  const [template, setTemplate] = useState(defaultTemplate)
  const [docViewId, setDocViewId] = useState('all')
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [currentDocument, setCurrentDocument] = useState<DocumentRecord | null>(
    null
  )
  const [aiModelReview, setAiModelReview] = useState<AiModelReview | null>(null)
  const [mdkAdapters, setMdkAdapters] = useState<MdkAdapter[]>([])
  const [mdkTool, setMdkTool] = useState('json')
  const [mdkFilename, setMdkFilename] = useState('model.json')
  const [mdkContent, setMdkContent] = useState(sampleMdkJson)
  const [mdkParseResult, setMdkParseResult] = useState<MdkParseResponse | null>(
    null
  )
  const [mdkImportJob, setMdkImportJob] = useState<MdkImportJob | null>(null)
  const [mdkCommit, setMdkCommit] = useState(true)
  const [mdkMessage, setMdkMessage] = useState('MDK frontend import')
  const [assistantQuestion, setAssistantQuestion] = useState('')
  const [assistantMessages, setAssistantMessages] = useState<AiChatMessage[]>([])
  const [activeTab, setActiveTab] = useState<WorkbenchTab>(() =>
    tabFromHash(window.location.hash)
  )
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')

  const project = projects.find((item) => item.id === projectId)
  const types = Object.keys(metamodel?.types || {})
  const relationTypes = Object.keys(metamodel?.relation_labels || {})
  const selectedElement =
    elements.find((item) => item.id === selectedId) ||
    allElements.find((item) => item.id === selectedId)
  const viewElements = allElements.filter((item) => item.type === 'View')
  const viewpointElements = allElements.filter((item) => item.type === 'Viewpoint')
  const elementCounts = useMemo(() => countBy(elements, (item) => item.type), [
    elements,
  ])

  useEffect(() => {
    bootstrap()
  }, [])

  useEffect(() => {
    const onHashChange = () => {
      const nextTab = tabFromHash(window.location.hash)
      setActiveTab(nextTab)
      preloadTab(nextTab)
    }

    onHashChange()
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [projectId, branch])

  useEffect(() => {
    if (!projectId) return
    loadProjectBranches(projectId)
  }, [projectId])

  useEffect(() => {
    if (!projectId || !branch) return
    loadElements()
  }, [projectId, branch, typeFilter, query])

  useEffect(() => {
    if (!projectId || !branch) return
    loadAllElements()
  }, [projectId, branch])

  useEffect(() => {
    if (!projectId || !branch) return
    loadViews()
  }, [projectId, branch, allElements.length])

  useEffect(() => {
    if (!selectedElement) return
    setForm(selectedElement)
    setAttributesText(JSON.stringify(selectedElement.attributes || {}, null, 2))
    setRelationsText(JSON.stringify(selectedElement.relations || [], null, 2))
  }, [selectedElement?.id])

  useEffect(() => {
    if (!projectId || !branch) return
    loadDiagram()
  }, [diagramType, projectId, branch, selectedViewId])

  async function bootstrap() {
    setLoading(true)
    try {
      const [metamodelPayload, projectsPayload] = await Promise.all([
        api<Metamodel>('/api/metamodel', { identity, role }),
        api<{ projects: Project[] }>('/api/projects', { identity, role }),
      ])
      setMetamodel(metamodelPayload)
      setProjects(projectsPayload.projects)
      setProjectId(projectsPayload.projects[0]?.id || '')
    } catch (error) {
      notifyError(error)
    } finally {
      setLoading(false)
    }
  }

  async function loadProjectBranches(nextProjectId = projectId) {
    if (!nextProjectId) return
    try {
      const payload = await api<{ branches: Branch[] }>(
        `/api/projects/${encodeURIComponent(nextProjectId)}/branches`,
        { identity, role }
      )
      setBranches(payload.branches)
      const nextBranch = payload.branches.some((item) => item.name === branch)
        ? branch
        : payload.branches[0]?.name || 'main'
      setBranch(nextBranch)
      setMergeSource(
        payload.branches.find((item) => item.name !== nextBranch)?.name || ''
      )
    } catch (error) {
      notifyError(error)
    }
  }

  async function loadElements() {
    if (!projectId || !branch) return
    try {
      const params = new URLSearchParams()
      if (typeFilter !== 'all') params.set('type', typeFilter)
      if (query.trim()) params.set('q', query.trim())
      const payload = await api<{ elements: SysmlElement[] }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/elements?${params}`,
        { identity, role }
      )
      setElements(payload.elements)
      const nextId = payload.elements.some((item) => item.id === selectedId)
        ? selectedId
        : payload.elements[0]?.id || ''
      setSelectedId(nextId)
      if (!nextId) startNewElement()
      await Promise.all([loadValidation(), loadDiagram()])
    } catch (error) {
      notifyError(error)
    }
  }

  async function loadAllElements() {
    if (!projectId || !branch) return
    try {
      const payload = await api<{ elements: SysmlElement[] }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/elements`,
        { identity, role }
      )
      setAllElements(payload.elements)
    } catch (error) {
      notifyError(error)
    }
  }

  async function loadValidation() {
    if (!projectId || !branch) return
    try {
      const payload = await api<ValidationPayload>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/validate`,
        { identity, role }
      )
      setValidation(payload)
    } catch (error) {
      notifyError(error)
    }
  }

  async function loadViews() {
    if (!projectId || !branch) return
    try {
      const payload = await api<{ views: SysmlElement[] }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/views`,
        { identity, role }
      )
      setViews(payload.views)
      if (
        selectedViewId !== 'all' &&
        !payload.views.some((view) => view.id === selectedViewId)
      ) {
        setSelectedViewId('all')
        setViewScope(null)
      }
      if (
        docViewId !== 'all' &&
        !payload.views.some((view) => view.id === docViewId)
      ) {
        setDocViewId('all')
      }
    } catch (error) {
      notifyError(error)
    }
  }

  async function loadDiagram() {
    if (!projectId || !branch) return
    try {
      if (selectedViewId !== 'all') {
        const [diagramPayload, scopePayload] = await Promise.all([
          api<{ diagram: DiagramPayload }>(
            `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/views/${encodeURIComponent(selectedViewId)}/diagram`,
            { identity, role }
          ),
          api<ViewPayload>(
            `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/views/${encodeURIComponent(selectedViewId)}`,
            { identity, role }
          ),
        ])
        setDiagram(diagramPayload.diagram)
        setViewScope(scopePayload)
        return
      }
      const payload = await api<{ diagram: DiagramPayload }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/diagram?type=${diagramType}`,
        { identity, role }
      )
      setDiagram(payload.diagram)
      setViewScope(null)
    } catch (error) {
      notifyError(error)
    }
  }

  async function loadTraceability() {
    if (!projectId || !branch) return
    setBusy('trace')
    try {
      const payload = await api<{ traceability: TraceabilityRow[] }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/traceability`,
        { identity, role }
      )
      setTraceability(payload.traceability)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function loadVersionData() {
    if (!projectId) return
    setBusy('version')
    try {
      const [commitPayload, tagPayload, auditPayload] = await Promise.all([
        api<{ commits: Commit[] }>(
          `/api/projects/${encodeURIComponent(projectId)}/commits`,
          { identity, role }
        ),
        api<{ tags: Tag[] }>(
          `/api/projects/${encodeURIComponent(projectId)}/tags`,
          { identity, role }
        ),
        api<{ events: AuditEvent[] }>(
          `/api/projects/${encodeURIComponent(projectId)}/audit?limit=80`,
          { identity, role }
        ),
      ])
      setCommits(commitPayload.commits)
      setTags(tagPayload.tags)
      setAuditEvents(auditPayload.events)
      setRollbackCommit(commitPayload.commits[0]?.id || '')
      setDiffFrom(commitPayload.commits[1]?.id || commitPayload.commits[0]?.id || 'working')
      setDiffTo('working')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function loadDocuments() {
    if (!projectId || !branch) return
    setBusy('documents')
    try {
      const payload = await api<{ documents: DocumentRecord[] }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/documents`,
        { identity, role }
      )
      setDocuments(payload.documents)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  function selectTab(tab: WorkbenchTab) {
    setActiveTab(tab)
    preloadTab(tab)
    const nextHash = `#${tab}`
    if (window.location.hash !== nextHash) {
      window.history.replaceState(null, '', nextHash)
    }
  }

  function preloadTab(tab: WorkbenchTab) {
    if (tab === 'trace') void loadTraceability()
    if (tab === 'version') void loadVersionData()
    if (tab === 'docgen') void loadDocuments()
    if (tab === 'mdk') void loadMdkAdapters()
  }

  async function loadMdkAdapters() {
    setBusy((current) => current || 'mdk-adapters')
    try {
      const payload = await api<{ adapters: MdkAdapter[] }>('/api/mdk/adapters', {
        identity,
        role,
      })
      setMdkAdapters(payload.adapters)
      if (!payload.adapters.some((adapter) => adapter.id === mdkTool)) {
        setMdkTool(payload.adapters[0]?.id || 'json')
      }
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy((current) => (current === 'mdk-adapters' ? '' : current))
    }
  }

  async function handleLogin() {
    setBusy('login')
    try {
      const payload = await login(loginForm.username.trim(), loginForm.password)
      setIdentity(payload.identity)
      setRole(payload.identity.role)
      saveIdentity(payload.identity)
      toast.success(`已登录：${payload.identity.display || payload.identity.username}`)
      await bootstrap()
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  function handleLogout() {
    setIdentity(null)
    saveIdentity(null)
    setRole('author')
    toast.success('已退出登录')
  }

  function startNewElement(type = form.type || 'Requirement') {
    const next = defaultElement(type, metamodel)
    setSelectedId('')
    setForm(next)
    setAttributesText(JSON.stringify(next.attributes || {}, null, 2))
    setRelationsText(JSON.stringify(next.relations || [], null, 2))
  }

  function updateForm<K extends keyof SysmlElement>(
    key: K,
    value: SysmlElement[K]
  ) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function handleTypeChange(type: string) {
    const defaults = defaultElement(type, metamodel)
    setForm((current) => ({
      ...current,
      type,
      stereotype: current.id
        ? current.stereotype
        : defaults.stereotype || current.stereotype,
      attributes: current.id ? current.attributes : defaults.attributes,
    }))
    if (!form.id) {
      setAttributesText(JSON.stringify(defaults.attributes || {}, null, 2))
    }
  }

  async function persistElement({
    element,
    attributesText: nextAttributesText,
    relationsText: nextRelationsText,
    successMessage = '模型元素已保存',
    nextSelectedId,
  }: SaveElementInput) {
    if (!projectId || !branch) return
    const payload = {
      ...element,
      id: element.id.trim(),
      name: element.name.trim(),
      owner: element.owner?.trim() || '',
      stereotype: element.stereotype?.trim() || '',
      description: element.description?.trim() || '',
      attributes:
        nextAttributesText === undefined
          ? element.attributes || {}
          : parseJson<Record<string, unknown>>(nextAttributesText, '属性 JSON', {}),
      relations:
        nextRelationsText === undefined
          ? element.relations || []
          : parseJson<Relation[]>(nextRelationsText, '关系 JSON', []),
    }
    const isUpdate = Boolean(payload.id)
    const path = isUpdate
      ? `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/elements/${encodeURIComponent(payload.id)}`
      : `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/elements`
    const result = await api<{ element: SysmlElement }>(path, {
      method: isUpdate ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
      identity,
      role,
    })
    setSelectedId(nextSelectedId ?? result.element.id)
    await Promise.all([loadElements(), loadAllElements()])
    if (successMessage) toast.success(successMessage)
  }

  async function saveElement(event: FormEvent) {
    event.preventDefault()
    if (!projectId || !branch) return
    setBusy('save-element')
    try {
      await persistElement({
        element: form,
        attributesText,
        relationsText,
      })
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function updateDiagramElement(
    element: SysmlElement,
    successMessage: string,
    nextSelectedId = element.id
  ) {
    if (!projectId || !branch) return
    setBusy('diagram-edit')
    try {
      await persistElement({
        element,
        successMessage,
        nextSelectedId,
      })
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  function handleDiagramPositionsChange(
    positions: Record<string, { x: number; y: number }>
  ) {
    setDiagramPositions((current) => ({ ...current, ...positions }))
  }

  async function deleteElement() {
    if (!projectId || !branch || !selectedElement) return
    if (!window.confirm(`确认删除 ${selectedElement.id} ${selectedElement.name}？`)) {
      return
    }
    setBusy('delete-element')
    try {
      await api(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/elements/${encodeURIComponent(selectedElement.id)}`,
        { method: 'DELETE', identity, role }
      )
      setSelectedId('')
      await Promise.all([loadElements(), loadAllElements()])
      toast.success('模型元素已删除')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function addRelation() {
    if (!form.id || !elements.length || !relationTypes.length) return
    const target = elements.find((item) => item.id !== form.id)?.id || elements[0]?.id
    const next = [...(parseJsonSafe<Relation[]>(relationsText, []) || [])]
    next.push({ type: relationTypes[0], target })
    setRelationsText(JSON.stringify(next, null, 2))
  }

  function toggleViewElement(elementId: string, checked: boolean) {
    const attributes = parseJsonSafe<Record<string, unknown>>(attributesText, {})
    const current = Array.isArray(attributes.included_elements)
      ? attributes.included_elements.map(String)
      : []
    const next = checked
      ? Array.from(new Set([...current, elementId]))
      : current.filter((item) => item !== elementId)
    const updated = { ...attributes, included_elements: next }
    setAttributesText(JSON.stringify(updated, null, 2))
    setForm((currentForm) => ({
      ...currentForm,
      attributes: updated,
    }))
  }

  function updateViewAttributes(patch: Record<string, unknown>) {
    const attributes = parseJsonSafe<Record<string, unknown>>(attributesText, {})
    const updated = { ...attributes, ...patch }
    setAttributesText(JSON.stringify(updated, null, 2))
    setForm((currentForm) => ({
      ...currentForm,
      attributes: updated,
    }))
  }

  function updateViewQuery(patch: Record<string, unknown>) {
    const attributes = parseJsonSafe<Record<string, unknown>>(attributesText, {})
    const currentQuery =
      attributes.query && typeof attributes.query === 'object' && !Array.isArray(attributes.query)
        ? (attributes.query as Record<string, unknown>)
        : {}
    updateViewAttributes({ query: { ...currentQuery, ...patch } })
  }

  async function commitBranch() {
    if (!projectId || !branch) return
    const message = window.prompt('提交说明', 'Update SysML model')
    if (message === null) return
    setBusy('commit')
    try {
      const result = await api<{ commit: Commit }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/commit`,
        {
          method: 'POST',
          body: JSON.stringify({ message }),
          identity,
          role,
        }
      )
      await loadProjectBranches()
      toast.success(`已提交 ${result.commit.id}`)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function exportModel(format: 'json' | 'xmi') {
    if (!projectId || !branch) return
    setBusy(`export-${format}`)
    try {
      const payload = await api<unknown>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/export?format=${format}`,
        { identity, role }
      )
      if (format === 'xmi') {
        downloadText(`${projectId}-${branch}.xmi`, String(payload), 'application/xml')
      } else {
        downloadText(
          `${projectId}-${branch}.json`,
          JSON.stringify(payload, null, 2),
          'application/json'
        )
      }
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function runDiff() {
    if (!projectId || !branch) return
    setBusy('diff')
    try {
      const params = new URLSearchParams({ from: diffFrom, to: diffTo })
      const payload = await api<DiffPayload>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/diff?${params}`,
        { identity, role }
      )
      setDiff(payload)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function createBranch() {
    if (!projectId || !newBranch.trim()) return
    setBusy('branch')
    try {
      await api(`/api/projects/${encodeURIComponent(projectId)}/branches`, {
        method: 'POST',
        body: JSON.stringify({ name: newBranch.trim(), source: branch }),
        identity,
        role,
      })
      setBranch(newBranch.trim())
      setNewBranch('')
      await loadProjectBranches()
      await Promise.all([loadElements(), loadAllElements()])
      toast.success('分支已创建')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function createTag() {
    if (!projectId || !newTag.trim()) return
    const latestCommit = commits[0]?.id
    if (!latestCommit) {
      toast.error('Create a commit before tagging this model state')
      return
    }
    setBusy('tag')
    try {
      await api(`/api/projects/${encodeURIComponent(projectId)}/tags`, {
        method: 'POST',
        body: JSON.stringify({
          name: newTag.trim(),
          commit: latestCommit,
          description: `Read-only baseline for ${branch}`,
        }),
        identity,
        role,
      })
      setNewTag('')
      await loadVersionData()
      toast.success(`Tag ${newTag.trim()} created`)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function rollback() {
    if (!projectId || !branch || !rollbackCommit) return
    if (!window.confirm(`确认回滚到 ${rollbackCommit}？`)) return
    setBusy('rollback')
    try {
      await api(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/rollback`,
        {
          method: 'POST',
          body: JSON.stringify({ commit: rollbackCommit }),
          identity,
          role,
        }
      )
      await loadProjectBranches()
      await Promise.all([loadElements(), loadAllElements()])
      await loadVersionData()
      toast.success('回滚已完成')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function mergeBranch() {
    if (!projectId || !branch || !mergeSource || mergeSource === branch) return
    setBusy('merge')
    try {
      const result = await api<{
        merged: boolean
        conflicts?: { id: string }[]
        additions?: string[]
      }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/merge`,
        {
          method: 'POST',
          body: JSON.stringify({ source: mergeSource, force: forceMerge }),
          identity,
          role,
        }
      )
      if (!result.merged) {
        toast.error(`存在 ${result.conflicts?.length || 0} 个冲突`)
        return
      }
      await loadProjectBranches()
      await Promise.all([loadElements(), loadAllElements()])
      await loadVersionData()
      toast.success('分支合并完成')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function generateDocument() {
    if (!projectId || !branch) return
    setBusy('generate-document')
    try {
      const effectiveTemplate =
        docViewId === 'all'
          ? template
          : `# View Document\n\n{{view:${docViewId}}}\n`
      const result = await api<{ document: DocumentRecord }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/documents`,
        {
          method: 'POST',
          body: JSON.stringify({ template: effectiveTemplate, format: 'html' }),
          identity,
          role,
        }
      )
      setCurrentDocument(result.document)
      await loadDocuments()
      toast.success('文档已生成')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function generateAiDocgenDraft(mode: AiDocgenMode) {
    if (!projectId || !branch) return
    setBusy(`ai-docgen-${mode}`)
    try {
      const result = await api<AiDocgenDraft>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/docgen/ai-draft`,
        {
          method: 'POST',
          body: JSON.stringify({ mode, template }),
          identity,
          role,
        }
      )
      setTemplate(result.template)
      toast.success('AI DocGen draft generated')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function runAiModelReview() {
    if (!projectId || !branch) return
    setBusy('ai-model-review')
    try {
      const result = await api<AiModelReview>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/ve/ai-review`,
        {
          method: 'POST',
          body: JSON.stringify({ selected_id: selectedId }),
          identity,
          role,
        }
      )
      setAiModelReview(result)
      toast.success('AI model review completed')
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function openDocument(documentId: string) {
    if (!projectId || !branch) return
    setBusy(`document-${documentId}`)
    try {
      const payload = await api<{ document: DocumentRecord }>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/documents/${encodeURIComponent(documentId)}`,
        { identity, role }
      )
      setCurrentDocument(payload.document)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function askAssistant() {
    if (!projectId || !branch) return
    const question = assistantQuestion.trim()
    if (!question) {
      toast.error('请输入问题')
      return
    }
    const nextMessages: AiChatMessage[] = [
      ...assistantMessages,
      { role: 'user', content: question },
    ]
    setAssistantMessages(nextMessages)
    setAssistantQuestion('')
    setBusy('ai-chat')
    try {
      const result = await api<AiChatResponse>(
        `/api/projects/${encodeURIComponent(projectId)}/branches/${encodeURIComponent(branch)}/ai/chat`,
        {
          method: 'POST',
          body: JSON.stringify({ question, history: assistantMessages }),
          identity,
          role,
        }
      )
      setAssistantMessages([
        ...nextMessages,
        { role: 'assistant', content: result.answer },
      ])
    } catch (error) {
      setAssistantMessages(assistantMessages)
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function parseMdkContent(
    nextContent = mdkContent,
    nextFilename = mdkFilename,
    nextTool = mdkTool
  ) {
    if (!nextContent.trim()) {
      toast.error('请先上传或粘贴外部工具模型内容')
      return
    }
    setBusy('mdk-parse')
    try {
      const content =
        nextTool === 'json' ? parseJson<Record<string, unknown>>(nextContent, '模型 JSON', {}) : nextContent
      const payload = await api<MdkParseResponse>('/api/mdk/parse', {
        method: 'POST',
        body: JSON.stringify({
          filename: nextFilename.trim(),
          tool: nextTool,
          content,
        }),
        identity,
        role,
      })
      setMdkParseResult(payload)
      setMdkImportJob(null)
      toast.success(`解析完成：${payload.parsed_model.element_count} 个元素`)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function createMdkImportJob() {
    if (!projectId || !branch) return
    if (!mdkContent.trim()) {
      toast.error('请先上传或粘贴外部工具模型内容')
      return
    }
    setBusy('mdk-job')
    try {
      const content =
        mdkTool === 'json' ? parseJson<Record<string, unknown>>(mdkContent, '模型 JSON', {}) : mdkContent
      const payload = await api<{ job: MdkImportJob }>('/api/mdk/import-jobs', {
        method: 'POST',
        body: JSON.stringify({
          project: projectId,
          branch,
          filename: mdkFilename.trim(),
          tool: mdkTool,
          content,
        }),
        identity,
        role,
      })
      setMdkImportJob(payload.job)
      setMdkParseResult({
        parsed_model: payload.job.parsed_model,
        mapping_report: payload.job.mapping_report,
      })
      toast.success(`导入任务已创建：${payload.job.id}`)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  async function applyMdkImportJob() {
    if (!projectId || !branch || !mdkImportJob) return
    setBusy('mdk-apply')
    try {
      const payload = await api<{
        job: MdkImportJob
        result: { imported: number; mapping_report?: MappingReport }
      }>(
        `/api/mdk/import-jobs/${encodeURIComponent(mdkImportJob.id)}/apply`,
        {
          method: 'POST',
          body: JSON.stringify({
            project: projectId,
            branch,
            commit: mdkCommit,
            message: mdkMessage,
          }),
          identity,
          role,
        }
      )
      setMdkImportJob(payload.job)
      await Promise.all([loadElements(), loadAllElements()])
      if (mdkCommit) await loadProjectBranches()
      toast.success(`已应用导入任务，导入 ${payload.result.imported} 个元素`)
    } catch (error) {
      notifyError(error)
    } finally {
      setBusy('')
    }
  }

  function downloadCurrent(format: 'html' | 'markdown' | 'pdf') {
    if (!currentDocument) {
      toast.error('请先生成或打开一个文档')
      return
    }
    if (format === 'markdown') {
      downloadText(
        `${currentDocument.id}.md`,
        currentDocument.markdown || '',
        'text/markdown'
      )
      return
    }
    if (format === 'pdf') {
      if (!currentDocument.pdf_base64) {
        toast.error('当前文档没有 PDF 内容')
        return
      }
      downloadBase64(
        `${currentDocument.id}.pdf`,
        currentDocument.pdf_base64,
        'application/pdf'
      )
      return
    }
    downloadText(
      `${currentDocument.id}.html`,
      currentDocument.html || '',
      'text/html'
    )
  }

  const stats = [
    {
      label: 'Elements',
      value: elements.length,
      detail: `${Object.keys(elementCounts).length} SysML types`,
      icon: Boxes,
    },
    {
      label: 'Requirements',
      value: elementCounts.Requirement || 0,
      detail: 'Requirement',
      icon: ShieldCheck,
    },
    {
      label: 'Blocks',
      value: elementCounts.Block || 0,
      detail: 'Block',
      icon: Archive,
    },
    {
      label: 'Validation',
      value:
        (validation?.summary.errors || 0) + (validation?.summary.warnings || 0),
      detail: `${validation?.summary.errors || 0} errors / ${validation?.summary.warnings || 0} warnings`,
      icon: AlertCircle,
    },
  ]

  return (
    <>
      <Header fixed className='border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/70'>
        <div className='me-auto min-w-0'>
          <div className='flex items-center gap-2'>
            <span className='truncate text-sm font-semibold'>
              SysML DocGen
            </span>
            <Badge variant='outline' className='hidden sm:inline-flex'>
              FastAPI + Shadcn Admin
            </Badge>
          </div>
          <p className='mt-0.5 hidden text-xs text-muted-foreground sm:block'>
            MMS / VE / MDK / DocGen integrated workbench
          </p>
        </div>
        <IdentityDialog
          identity={identity}
          role={role}
          setRole={setRole}
          loginForm={loginForm}
          setLoginForm={setLoginForm}
          onLogin={handleLogin}
          onLogout={handleLogout}
          busy={busy}
        />
        <ThemeSwitch />
        <ConfigDrawer />
      </Header>

      <Main fluid className='sysml-workbench min-h-[calc(100svh-4rem)] pb-8'>
        {loading ? (
          <div className='flex min-h-[520px] items-center justify-center'>
            <div className='flex items-center gap-3 text-sm text-muted-foreground'>
              <Loader2 className='size-4 animate-spin' />
              Loading SysML workbench
            </div>
          </div>
        ) : (
          <div className='sysml-shell space-y-5'>
            <section className='space-y-4 pt-2'>
              <div className='sysml-hero rounded-lg p-4 md:p-5'>
                <div className='flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between'>
                  <div className='min-w-0'>
                    <div className='sysml-eyebrow mb-2 text-xs font-semibold uppercase'>
                      MBSE Model Management System
                    </div>
                    <div className='flex flex-wrap items-center gap-2'>
                      <h1 className='truncate text-2xl font-semibold tracking-tight md:text-3xl'>
                        {project?.name || 'SysML Project'}
                      </h1>
                      <Badge variant='outline' className='rounded-sm'>
                        branch / {branch}
                      </Badge>
                      <Badge variant='secondary' className='rounded-sm'>
                        {branches.find((item) => item.name === branch)?.head ||
                          'working'}
                      </Badge>
                    </div>
                    <p className='mt-2 max-w-3xl text-sm text-muted-foreground'>
                      {project?.organization || 'Current project'}
                      <span className='mx-2 text-border'>/</span>
                      MMS, VE, MDK and DocGen are kept in one traceable workspace.
                    </p>
                  </div>
                  <div className='grid gap-2 md:grid-cols-[minmax(220px,1fr)_160px_auto] xl:min-w-[740px]'>
                    <Select value={projectId} onValueChange={setProjectId}>
                      <SelectTrigger className='w-full'>
                        <SelectValue placeholder='Select project' />
                      </SelectTrigger>
                      <SelectContent>
                        {projects.map((item) => (
                          <SelectItem key={item.id} value={item.id}>
                            {item.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Select value={branch} onValueChange={setBranch}>
                      <SelectTrigger className='w-full'>
                        <SelectValue placeholder='Select branch' />
                      </SelectTrigger>
                      <SelectContent>
                        {branches.map((item) => (
                          <SelectItem key={item.name} value={item.name}>
                            {item.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className='flex flex-wrap gap-2 md:flex-nowrap'>
                      <Button
                        variant='outline'
                        onClick={() => exportModel('json')}
                        disabled={busy === 'export-json'}
                      >
                        <Download className='size-4' />
                        JSON
                      </Button>
                      <Button
                        variant='outline'
                        onClick={() => exportModel('xmi')}
                        disabled={busy === 'export-xmi'}
                      >
                        <Code2 className='size-4' />
                        XMI
                      </Button>
                      <Button onClick={commitBranch} disabled={busy === 'commit'}>
                        <GitCommitHorizontal className='size-4' />
                        Commit
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              <div className='grid gap-3 sm:grid-cols-2 xl:grid-cols-4'>
                {stats.map((item) => (
                  <Card key={item.label} className='sysml-card sysml-metric'>
                    <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
                      <CardTitle className='text-sm font-medium'>
                        {item.label}
                      </CardTitle>
                      <item.icon className='size-4 text-muted-foreground' />
                    </CardHeader>
                    <CardContent>
                      <div className='text-2xl font-bold'>{item.value}</div>
                      <p className='mt-1 text-xs text-muted-foreground'>
                        {item.detail}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>

            <Tabs
              value={activeTab}
              onValueChange={(value) => selectTab(value as WorkbenchTab)}
              className='space-y-4'
            >
              <div className='sticky top-16 z-20 overflow-x-auto rounded-lg py-2 backdrop-blur'>
                <TabsList className='sysml-tabs h-11 p-1'>
                  <TabsTrigger value='model'>
                    <LayoutDashboard className='size-4' />
                    Model
                  </TabsTrigger>
                  <TabsTrigger value='diagram'>
                    <Network className='size-4' />
                    Graph
                  </TabsTrigger>
                  <TabsTrigger value='trace'>
                    <Workflow className='size-4' />
                    Trace
                  </TabsTrigger>
                  <TabsTrigger value='version'>
                    <GitBranch className='size-4' />
                    Versions
                  </TabsTrigger>
                  <TabsTrigger value='docgen'>
                    <FileText className='size-4' />
                    Docs
                  </TabsTrigger>
                  <TabsTrigger value='mdk'>
                    <Wrench className='size-4' />
                    MDK
                  </TabsTrigger>
                  <TabsTrigger value='assistant'>
                    <MessageCircle className='size-4' />
                    Assistant
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value='model'>
                <ModelTab
                  elements={elements}
                  bindableElements={allElements}
                  selectedId={selectedId}
                  setSelectedId={setSelectedId}
                  typeFilter={typeFilter}
                  setTypeFilter={setTypeFilter}
                  query={query}
                  setQuery={setQuery}
                  types={types}
                  form={form}
                  updateForm={updateForm}
                  handleTypeChange={handleTypeChange}
                  attributesText={attributesText}
                  setAttributesText={setAttributesText}
                  relationsText={relationsText}
                  setRelationsText={setRelationsText}
                  views={views.length ? views : viewElements}
                  viewpoints={viewpointElements}
                  validation={validation}
                  aiReview={aiModelReview}
                  onNew={() => startNewElement(types[0] || 'Requirement')}
                  onNewView={() => startNewElement('View')}
                  onNewViewpoint={() => startNewElement('Viewpoint')}
                  onDelete={deleteElement}
                  onSave={saveElement}
                  onAddRelation={addRelation}
                  onToggleViewElement={toggleViewElement}
                  onUpdateViewAttributes={updateViewAttributes}
                  onUpdateViewQuery={updateViewQuery}
                  onAiReview={runAiModelReview}
                  busy={busy}
                />
              </TabsContent>

              <TabsContent value='diagram'>
                <DiagramTab
                  diagram={diagram}
                  diagramType={diagramType}
                  setDiagramType={setDiagramType}
                  views={views.length ? views : viewElements}
                  selectedViewId={selectedViewId}
                  setSelectedViewId={setSelectedViewId}
                  viewScope={viewScope}
                  metamodel={metamodel}
                  elements={allElements.length ? allElements : elements}
                  selectedId={selectedId}
                  setSelectedId={setSelectedId}
                  onRefresh={loadDiagram}
                  onSaveElement={updateDiagramElement}
                  diagramPositions={diagramPositions}
                  onDiagramPositionsChange={handleDiagramPositionsChange}
                  busy={busy}
                />
              </TabsContent>

              <TabsContent value='trace'>
                <TraceTab
                  traceability={traceability}
                  busy={busy}
                  onRefresh={loadTraceability}
                />
              </TabsContent>

              <TabsContent value='version'>
                <VersionTab
                  branches={branches}
                  commits={commits}
                  tags={tags}
                  auditEvents={auditEvents}
                  diff={diff}
                  diffFrom={diffFrom}
                  setDiffFrom={setDiffFrom}
                  diffTo={diffTo}
                  setDiffTo={setDiffTo}
                  rollbackCommit={rollbackCommit}
                  setRollbackCommit={setRollbackCommit}
                  newBranch={newBranch}
                  setNewBranch={setNewBranch}
                  newTag={newTag}
                  setNewTag={setNewTag}
                  mergeSource={mergeSource}
                  setMergeSource={setMergeSource}
                  forceMerge={forceMerge}
                  setForceMerge={setForceMerge}
                  onRefresh={loadVersionData}
                  onDiff={runDiff}
                  onRollback={rollback}
                  onCreateBranch={createBranch}
                  onCreateTag={createTag}
                  onMerge={mergeBranch}
                  busy={busy}
                />
              </TabsContent>

              <TabsContent value='docgen'>
                <DocgenTab
                  template={template}
                  setTemplate={setTemplate}
                  elements={elements}
                  views={views.length ? views : viewElements}
                  docViewId={docViewId}
                  setDocViewId={setDocViewId}
                  validation={validation}
                  documents={documents}
                  currentDocument={currentDocument}
                  onReset={() => setTemplate(defaultTemplate)}
                  onGenerate={generateDocument}
                  onAiDraft={generateAiDocgenDraft}
                  onOpen={openDocument}
                  onDownload={downloadCurrent}
                  busy={busy}
                />
              </TabsContent>

              <TabsContent value='mdk'>
                <MdkTab
                  adapters={mdkAdapters}
                  tool={mdkTool}
                  setTool={setMdkTool}
                  filename={mdkFilename}
                  setFilename={setMdkFilename}
                  content={mdkContent}
                  setContent={setMdkContent}
                  parseResult={mdkParseResult}
                  importJob={mdkImportJob}
                  commit={mdkCommit}
                  setCommit={setMdkCommit}
                  message={mdkMessage}
                  setMessage={setMdkMessage}
                  onRefreshAdapters={loadMdkAdapters}
                  onParse={parseMdkContent}
                  onCreateJob={createMdkImportJob}
                  onApplyJob={applyMdkImportJob}
                  busy={busy}
                />
              </TabsContent>
              <TabsContent value='assistant'>
                <AssistantTab
                  messages={assistantMessages}
                  question={assistantQuestion}
                  setQuestion={setAssistantQuestion}
                  onAsk={askAssistant}
                  busy={busy}
                />
              </TabsContent>
            </Tabs>
          </div>
        )}
      </Main>
    </>
  )
}

type ModelTabProps = {
  elements: SysmlElement[]
  bindableElements: SysmlElement[]
  selectedId: string
  setSelectedId: (id: string) => void
  typeFilter: string
  setTypeFilter: (type: string) => void
  query: string
  setQuery: (query: string) => void
  types: string[]
  form: SysmlElement
  updateForm: <K extends keyof SysmlElement>(
    key: K,
    value: SysmlElement[K]
  ) => void
  handleTypeChange: (type: string) => void
  attributesText: string
  setAttributesText: (value: string) => void
  relationsText: string
  setRelationsText: (value: string) => void
  views: SysmlElement[]
  viewpoints: SysmlElement[]
  validation: ValidationPayload | null
  aiReview: AiModelReview | null
  onNew: () => void
  onNewView: () => void
  onNewViewpoint: () => void
  onDelete: () => void
  onSave: (event: FormEvent) => void
  onAddRelation: () => void
  onToggleViewElement: (elementId: string, checked: boolean) => void
  onUpdateViewAttributes: (patch: Record<string, unknown>) => void
  onUpdateViewQuery: (patch: Record<string, unknown>) => void
  onAiReview: () => void
  busy: string
}

function IdentityDialog({
  identity,
  role,
  setRole,
  loginForm,
  setLoginForm,
  onLogin,
  onLogout,
  busy,
}: {
  identity: Identity | null
  role: Identity['role']
  setRole: (role: Identity['role']) => void
  loginForm: { username: string; password: string }
  setLoginForm: React.Dispatch<
    React.SetStateAction<{ username: string; password: string }>
  >
  onLogin: () => void
  onLogout: () => void
  busy: string
}) {
  const signedName = identity?.display || identity?.username || 'Guest'
  const signedRole = identity?.role || role

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant='outline' className='gap-2'>
          <UserCircle className='size-4' />
          <span className='hidden sm:inline'>{signedName}</span>
          <Badge variant='secondary' className='rounded-sm'>
            {signedRole}
          </Badge>
        </Button>
      </DialogTrigger>
      <DialogContent className='sm:max-w-[520px]'>
        <DialogHeader>
          <DialogTitle>Account & Access</DialogTitle>
          <DialogDescription>
            Identity controls model writes, commits, rollback, and branch merge permissions.
          </DialogDescription>
        </DialogHeader>
        <div className='rounded-lg border bg-muted/30 p-4'>
          <div className='flex items-center gap-3'>
            <div className='flex size-11 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground'>
              {(identity?.username || 'SD').slice(0, 2).toUpperCase()}
            </div>
            <div className='min-w-0'>
              <div className='truncate font-medium'>{signedName}</div>
              <div className='text-sm text-muted-foreground'>
                {identity?.username || 'Guest'} / {signedRole}
              </div>
            </div>
          </div>
        </div>
        <div className='grid gap-4 sm:grid-cols-2'>
          <Field label='Username'>
            <Input
              value={loginForm.username}
              onChange={(event) =>
                setLoginForm((current) => ({
                  ...current,
                  username: event.target.value,
                }))
              }
            />
          </Field>
          <Field label='Password'>
            <Input
              type='password'
              value={loginForm.password}
              onChange={(event) =>
                setLoginForm((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
            />
          </Field>
        </div>
        <Field label='Request role'>
          <Select
            value={role}
            onValueChange={(value) =>
              setRole(value as 'admin' | 'author' | 'reader')
            }
          >
            <SelectTrigger className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value='author'>author</SelectItem>
              <SelectItem value='reader'>reader</SelectItem>
              <SelectItem value='admin'>admin</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <div className='flex flex-wrap justify-end gap-2'>
          <Button variant='outline' onClick={onLogout}>
            <LogOut className='size-4' />
            Sign out
          </Button>
          <Button onClick={onLogin} disabled={busy === 'login'}>
            {busy === 'login' ? (
              <Loader2 className='size-4 animate-spin' />
            ) : (
              <LogIn className='size-4' />
            )}
            Sign in
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function ModelTab(props: ModelTabProps) {
  const typeCounts = countBy(props.elements, (item) => item.type)

  return (
    <div className='grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]'>
      <Card className='sysml-card self-start'>
        <CardHeader className='space-y-3'>
          <div className='flex items-center justify-between gap-3'>
            <div>
              <CardTitle>模型元素</CardTitle>
              <CardDescription>按类型筛选、搜索并选择元素</CardDescription>
            </div>
            <Button size='sm' onClick={props.onNew}>
              <Plus className='size-4' />
              新建
            </Button>
          </div>
          <div className='grid gap-2 sm:grid-cols-[150px_1fr]'>
            <Select value={props.typeFilter} onValueChange={props.setTypeFilter}>
              <SelectTrigger className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='all'>全部类型</SelectItem>
                {props.types.map((type) => (
                  <SelectItem key={type} value={type}>
                    {labelType(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className='relative'>
              <Search className='absolute left-3 top-2.5 size-4 text-muted-foreground' />
              <Input
                className='pl-9'
                placeholder='搜索 ID、名称或描述'
                value={props.query}
                onChange={(event) => props.setQuery(event.target.value)}
              />
            </div>
          </div>
          <div className='grid grid-cols-3 gap-2 text-xs'>
            <div className='rounded-md border bg-muted/30 px-3 py-2'>
              <div className='font-semibold'>{props.elements.length}</div>
              <div className='text-muted-foreground'>Elements</div>
            </div>
            <div className='rounded-md border bg-muted/30 px-3 py-2'>
              <div className='font-semibold'>{Object.keys(typeCounts).length}</div>
              <div className='text-muted-foreground'>Types</div>
            </div>
            <div className='rounded-md border bg-muted/30 px-3 py-2'>
              <div className='font-semibold'>{props.validation?.summary.warnings || 0}</div>
              <div className='text-muted-foreground'>Warnings</div>
            </div>
          </div>
        </CardHeader>
        <CardContent className='p-0'>
          <ScrollArea className='h-[520px]'>
            {props.elements.length ? (
              <div className='divide-y'>
                {props.elements.map((element) => (
                  <button
                    key={element.id}
                    className={cn(
                      'grid w-full gap-1 px-4 py-3 text-left transition-colors hover:bg-muted/60',
                      props.selectedId === element.id && 'bg-muted'
                    )}
                    type='button'
                    onClick={() => props.setSelectedId(element.id)}
                  >
                    <div className='flex items-center justify-between gap-3'>
                      <span className='font-mono text-sm font-semibold'>
                        {element.id}
                      </span>
                      <Badge variant='secondary'>{labelType(element.type)}</Badge>
                    </div>
                    <div className='truncate text-sm font-medium'>
                      {element.name || '未命名元素'}
                    </div>
                    <p className='line-clamp-2 text-xs text-muted-foreground'>
                      {element.description || '暂无描述'}
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState title='没有元素' description='当前筛选条件下没有模型元素' />
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      <div className='space-y-4'>
        <Card className='sysml-card'>
          <CardHeader>
            <div className='flex items-center justify-between gap-3'>
              <div>
                <CardTitle>Views</CardTitle>
                <CardDescription>
                  First-class model views for scoped Graph and Docs output.
                </CardDescription>
              </div>
              <div className='flex flex-wrap gap-2'>
                <Button size='sm' variant='outline' onClick={props.onNewViewpoint}>
                  <Plus className='size-4' />
                  New Viewpoint
                </Button>
                <Button size='sm' variant='outline' onClick={props.onNewView}>
                  <Plus className='size-4' />
                  New View
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className='space-y-4'>
            <div>
              <div className='mb-2 flex items-center justify-between gap-2'>
                <div className='text-sm font-semibold'>Viewpoints</div>
                <Badge variant='outline'>{props.viewpoints.length}</Badge>
              </div>
              {props.viewpoints.length ? (
                <div className='grid gap-2 md:grid-cols-2'>
                  {props.viewpoints.map((viewpoint) => {
                    const attributes = viewpoint.attributes || {}
                    return (
                      <button
                        key={viewpoint.id}
                        type='button'
                        onClick={() => props.setSelectedId(viewpoint.id)}
                        className={cn(
                          'rounded-md border p-3 text-left transition-colors hover:bg-muted/60',
                          props.selectedId === viewpoint.id && 'border-primary bg-muted'
                        )}
                      >
                        <div className='flex items-center justify-between gap-2'>
                          <span className='font-mono text-sm font-semibold'>
                            {viewpoint.id}
                          </span>
                          <Badge variant='secondary'>Viewpoint</Badge>
                        </div>
                        <div className='mt-1 text-sm font-medium'>
                          {viewpoint.name || viewpoint.id}
                        </div>
                        <p className='mt-1 line-clamp-2 text-xs text-muted-foreground'>
                          {String(attributes.purpose || viewpoint.description || 'No purpose yet')}
                        </p>
                      </button>
                    )
                  })}
                </div>
              ) : (
                <EmptyState
                  title='No Viewpoints yet'
                  description='Create a Viewpoint first, then select it in a View.'
                />
              )}
            </div>
            <Separator />
            <div>
              <div className='mb-2 flex items-center justify-between gap-2'>
                <div className='text-sm font-semibold'>Views</div>
                <Badge variant='outline'>{props.views.length}</Badge>
              </div>
            {props.views.length ? (
              <div className='grid gap-2 md:grid-cols-2'>
                {props.views.map((view) => {
                  const attributes = view.attributes || {}
                  const included = Array.isArray(attributes.included_elements)
                    ? attributes.included_elements.length
                    : 0
                  return (
                    <button
                      key={view.id}
                      type='button'
                      onClick={() => props.setSelectedId(view.id)}
                      className={cn(
                        'rounded-md border p-3 text-left transition-colors hover:bg-muted/60',
                        props.selectedId === view.id && 'border-primary bg-muted'
                      )}
                    >
                      <div className='flex items-center justify-between gap-2'>
                        <span className='font-mono text-sm font-semibold'>
                          {view.id}
                        </span>
                        <Badge variant='secondary'>{included} linked</Badge>
                      </div>
                      <div className='mt-1 text-sm font-medium'>
                        {view.name || view.id}
                      </div>
                      <p className='mt-1 line-clamp-2 text-xs text-muted-foreground'>
                        {String(attributes.viewpoint || 'General viewpoint')} /{' '}
                        {view.description || 'No description'}
                      </p>
                    </button>
                  )
                })}
              </div>
            ) : (
              <EmptyState
                title='No Views yet'
                description='Create a View to bind elements and drive scoped Graph/Docs output.'
              />
            )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className='flex items-start justify-between gap-3'>
              <div>
                <CardTitle>元素编辑器</CardTitle>
                <CardDescription>属性与关系字段使用 JSON 格式</CardDescription>
              </div>
              <Button
                variant='destructive'
                size='sm'
                onClick={props.onDelete}
                disabled={!props.form.id || props.busy === 'delete-element'}
              >
                <Trash2 className='size-4' />
                删除
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <form className='grid gap-4' onSubmit={props.onSave}>
              <div className='grid gap-4 md:grid-cols-2'>
                <Field label='ID'>
                  <Input
                    value={props.form.id}
                    onChange={(event) =>
                      props.updateForm('id', event.target.value)
                    }
                    placeholder='留空可由后端生成'
                  />
                </Field>
                <Field label='类型'>
                  <Select
                    value={props.form.type}
                    onValueChange={props.handleTypeChange}
                  >
                    <SelectTrigger className='w-full'>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {props.types.map((type) => (
                        <SelectItem key={type} value={type}>
                          {labelType(type)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label='名称'>
                  <Input
                    required
                    value={props.form.name}
                    onChange={(event) =>
                      props.updateForm('name', event.target.value)
                    }
                  />
                </Field>
                <Field label='负责人'>
                  <Input
                    value={props.form.owner || ''}
                    onChange={(event) =>
                      props.updateForm('owner', event.target.value)
                    }
                  />
                </Field>
                <Field label='构造型'>
                  <Input
                    value={props.form.stereotype || ''}
                    onChange={(event) =>
                      props.updateForm('stereotype', event.target.value)
                    }
                  />
                </Field>
              </div>
              <Field label='描述'>
                <Textarea
                  rows={3}
                  value={props.form.description || ''}
                  onChange={(event) =>
                    props.updateForm('description', event.target.value)
                  }
                />
              </Field>
              {props.form.type === 'View' && (
                <ViewDefinitionPanel
                  elements={props.bindableElements}
                  viewpoints={props.viewpoints}
                  viewId={props.form.id}
                  attributesText={props.attributesText}
                  onToggle={props.onToggleViewElement}
                  onUpdateAttributes={props.onUpdateViewAttributes}
                  onUpdateQuery={props.onUpdateViewQuery}
                />
              )}
              <div className='grid gap-4 lg:grid-cols-2'>
                <Field label='属性 JSON'>
                  <Textarea
                    className='min-h-[220px] font-mono text-xs'
                    value={props.attributesText}
                    onChange={(event) => props.setAttributesText(event.target.value)}
                  />
                </Field>
                <Field label='关系 JSON'>
                  <Textarea
                    className='min-h-[220px] font-mono text-xs'
                    value={props.relationsText}
                    onChange={(event) => props.setRelationsText(event.target.value)}
                  />
                </Field>
              </div>
              <div className='flex flex-wrap justify-end gap-2'>
                <Button type='button' variant='outline' onClick={props.onAddRelation}>
                  <Plus className='size-4' />
                  添加关系
                </Button>
                <Button
                  type='submit'
                  disabled={props.busy === 'save-element'}
                >
                  {props.busy === 'save-element' ? (
                    <Loader2 className='size-4 animate-spin' />
                  ) : (
                    <Save className='size-4' />
                  )}
                  保存元素
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <ValidationPanel validation={props.validation} />
        <AiModelReviewPanel
          review={props.aiReview}
          busy={props.busy}
          onReview={props.onAiReview}
        />
      </div>
    </div>
  )
}

function ValidationPanel({ validation }: { validation: ValidationPayload | null }) {
  if (!validation) return null
  return (
    <Card className='sysml-card'>
      <CardHeader>
        <div className='flex items-center justify-between gap-3'>
          <div>
            <CardTitle>语义校验</CardTitle>
            <CardDescription>
              {validation.summary.elements} 个元素，{validation.summary.errors} 个错误，
              {validation.summary.warnings} 个警告
            </CardDescription>
          </div>
          <Badge
            variant={validation.summary.errors ? 'destructive' : 'secondary'}
          >
            {validation.summary.errors ? '需处理' : '可发布'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {validation.issues.length ? (
          <div className='space-y-2'>
            {validation.issues.slice(0, 8).map((issue, index) => (
              <Alert
                key={`${issue.element_id}-${index}`}
                variant={issue.severity === 'error' ? 'destructive' : 'default'}
              >
                <AlertCircle className='size-4' />
                <AlertTitle>
                  {severityLabels[issue.severity]} / {issue.element_id}
                </AlertTitle>
                <AlertDescription>{issue.message}</AlertDescription>
              </Alert>
            ))}
          </div>
        ) : (
          <div className='flex items-center gap-2 text-sm text-muted-foreground'>
            <CheckCircle2 className='size-4 text-emerald-600' />
            未发现校验问题
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ViewDefinitionPanel({
  elements,
  viewpoints,
  viewId,
  attributesText,
  onToggle,
  onUpdateAttributes,
  onUpdateQuery,
}: {
  elements: SysmlElement[]
  viewpoints: SysmlElement[]
  viewId: string
  attributesText: string
  onToggle: (elementId: string, checked: boolean) => void
  onUpdateAttributes: (patch: Record<string, unknown>) => void
  onUpdateQuery: (patch: Record<string, unknown>) => void
}) {
  const attributes = parseJsonSafe<Record<string, unknown>>(attributesText, {})
  const query =
    attributes.query && typeof attributes.query === 'object' && !Array.isArray(attributes.query)
      ? (attributes.query as Record<string, unknown>)
      : {}
  const selectedTypes = stringList(query.types)
  const selectedOwners = stringList(query.owners)
  const selectedRelations = stringList(query.relations)
  const ownerOptions = Array.from(
    new Set(elements.map((element) => element.owner || '').filter(Boolean))
  ).sort()
  const included = includedElementIds(attributesText)
  const candidates = elements.filter((element) => element.id !== viewId)
  const grouped = candidates.reduce<Record<string, SysmlElement[]>>((acc, element) => {
    acc[element.type] = acc[element.type] || []
    acc[element.type].push(element)
    return acc
  }, {})
  const orderedTypes = Object.keys(grouped).sort()

  return (
    <Card className='border-dashed bg-muted/20'>
      <CardHeader className='pb-3'>
        <div className='flex items-center justify-between gap-3'>
          <div>
            <CardTitle className='text-base'>Viewpoint & View Query</CardTitle>
            <CardDescription>
              Configure the Viewpoint, automatic query, and manually bound elements.
            </CardDescription>
          </div>
          <Badge variant='secondary'>{included.size} selected</Badge>
        </div>
      </CardHeader>
      <CardContent className='space-y-5'>
        <div className='grid gap-4 lg:grid-cols-2'>
          <Field label='Viewpoint'>
            <Select
              value={String(attributes.viewpoint_id || 'none')}
              onValueChange={(value) => {
                const viewpoint = viewpoints.find((item) => item.id === value)
                onUpdateAttributes({
                  viewpoint_id: value === 'none' ? '' : value,
                  viewpoint: viewpoint?.name || '',
                })
              }}
            >
              <SelectTrigger className='w-full'>
                <SelectValue placeholder='Select a Viewpoint' />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='none'>No Viewpoint</SelectItem>
                {viewpoints.map((viewpoint) => (
                  <SelectItem key={viewpoint.id} value={viewpoint.id}>
                    {viewpoint.name || viewpoint.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {!viewpoints.length && (
              <p className='mt-2 text-xs text-muted-foreground'>
                No Viewpoint exists yet. Click New Viewpoint in the Views card first.
              </p>
            )}
          </Field>
          <Field label='Document section title'>
            <Input
              value={String(attributes.doc_section_title || '')}
              onChange={(event) =>
                onUpdateAttributes({ doc_section_title: event.target.value })
              }
              placeholder='例如：电源需求审查'
            />
          </Field>
        </div>

        <div className='rounded-md border bg-background p-4'>
          <div className='mb-3'>
            <div className='text-sm font-semibold'>View Query</div>
            <p className='text-xs text-muted-foreground'>
              Use this form to automatically collect model elements for this View.
            </p>
          </div>
          <div className='grid gap-4 lg:grid-cols-2'>
            <Field label='Element types'>
              <MultiCheckGrid
                options={elementsTypes(elements)}
                selected={selectedTypes}
                onChange={(next) => onUpdateQuery({ types: next })}
              />
            </Field>
            <Field label='Relations to focus'>
              <MultiCheckGrid
                options={['satisfy', 'verify', 'refine', 'constrain', 'include', 'conform']}
                selected={selectedRelations}
                onChange={(next) => onUpdateQuery({ relations: next })}
                label={labelRelation}
              />
            </Field>
            <Field label='Owners'>
              <MultiCheckGrid
                options={ownerOptions}
                selected={selectedOwners}
                onChange={(next) => onUpdateQuery({ owners: next })}
              />
            </Field>
            <Field label='Keyword'>
              <Input
                value={String(query.text || '')}
                onChange={(event) => onUpdateQuery({ text: event.target.value })}
                placeholder='搜索 ID、名称、描述、属性'
              />
            </Field>
            <Field label='Relation depth'>
              <Select
                value={String(query.relation_depth ?? 0)}
                onValueChange={(value) =>
                  onUpdateQuery({ relation_depth: Number(value) })
                }
              >
                <SelectTrigger className='w-full'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value='0'>0 - only matched/manual elements</SelectItem>
                  <SelectItem value='1'>1 - include directly related elements</SelectItem>
                  <SelectItem value='2'>2 - include two relation hops</SelectItem>
                  <SelectItem value='3'>3 - include three relation hops</SelectItem>
                </SelectContent>
              </Select>
            </Field>
          </div>
        </div>

        <div>
          <div className='mb-3'>
            <div className='text-sm font-semibold'>Bind Elements To View</div>
            <p className='text-xs text-muted-foreground'>
              Check elements to write them into attributes.included_elements.
            </p>
          </div>
        {candidates.length ? (
          <ScrollArea className='h-[300px] rounded-md border bg-background'>
            <div className='space-y-4 p-3'>
              {orderedTypes.map((type) => (
                <div key={type} className='space-y-2'>
                  <div className='flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground'>
                    <span>{labelType(type)}</span>
                    <Badge variant='outline'>{grouped[type].length}</Badge>
                  </div>
                  <div className='space-y-2'>
                    {grouped[type]
                      .sort((left, right) => left.id.localeCompare(right.id))
                      .map((element) => {
                        const checked = included.has(element.id)
                        return (
                          <label
                            key={element.id}
                            className='flex cursor-pointer items-start gap-3 rounded-md border p-3 hover:bg-muted/50'
                          >
                            <Checkbox
                              checked={checked}
                              onCheckedChange={(value) =>
                                onToggle(element.id, value === true)
                              }
                            />
                            <span className='min-w-0 flex-1'>
                              <span className='block font-mono text-xs font-semibold'>
                                {element.id}
                              </span>
                              <span className='block truncate text-sm'>
                                {element.name || element.id}
                              </span>
                              <span className='line-clamp-1 text-xs text-muted-foreground'>
                                {element.description || element.owner || 'No description'}
                              </span>
                            </span>
                          </label>
                        )
                      })}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <EmptyState
            title='No bindable elements'
            description='Create requirements, blocks, tests, or interfaces before binding a View.'
          />
        )}
        </div>
      </CardContent>
    </Card>
  )
}

function AiModelReviewPanel({
  review,
  busy,
  onReview,
}: {
  review: AiModelReview | null
  busy: string
  onReview: () => void
}) {
  const loading = busy === 'ai-model-review'

  return (
    <Card className='sysml-card'>
      <CardHeader>
        <div className='flex items-center justify-between gap-3'>
          <div>
            <CardTitle>{'AI \u6a21\u578b\u5ba1\u67e5'}</CardTitle>
            <CardDescription>{'\u57fa\u4e8e\u5f53\u524d VE \u6a21\u578b\u7ed9\u51fa\u4e00\u81f4\u6027\u548c\u8ffd\u6eaf\u5efa\u8bae'}</CardDescription>
          </div>
          <Button variant='secondary' size='sm' onClick={onReview} disabled={loading}>
            {loading ? (
              <Loader2 className='size-4 animate-spin' />
            ) : (
              <Sparkles className='size-4' />
            )}
            {'AI \u5ba1\u67e5'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className='flex items-center gap-2 text-sm text-muted-foreground'>
            <Loader2 className='size-4 animate-spin' />
            {'AI \u5ba1\u67e5\u4e2d'}
          </div>
        ) : review ? (
          <div className='rounded-md border bg-muted/20 p-4'>
            <MarkdownMessage content={review.review} compact />
          </div>
        ) : (
          <EmptyState
            title={'\u5c1a\u672a\u8fd0\u884c AI \u5ba1\u67e5'}
            description={'\u70b9\u51fb AI \u5ba1\u67e5\u540e\uff0c\u7cfb\u7edf\u4f1a\u5206\u6790\u5f53\u524d\u6a21\u578b\u7684\u5b8c\u6574\u6027\u3001\u8ffd\u6eaf\u6027\u548c\u6587\u6863\u53ef\u751f\u6210\u6027'}
          />
        )}
      </CardContent>
    </Card>
  )
}

function MultiCheckGrid({
  options,
  selected,
  onChange,
  label = (value: string) => value,
}: {
  options: string[]
  selected: string[]
  onChange: (next: string[]) => void
  label?: (value: string) => string
}) {
  if (!options.length) {
    return (
      <div className='rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground'>
        No options available
      </div>
    )
  }
  return (
    <div className='grid max-h-[150px] gap-2 overflow-auto rounded-md border bg-muted/20 p-2 sm:grid-cols-2'>
      {options.map((option) => {
        const checked = selected.includes(option)
        return (
          <label
            key={option}
            className='flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-background'
          >
            <Checkbox
              checked={checked}
              onCheckedChange={(value) => {
                const next =
                  value === true
                    ? Array.from(new Set([...selected, option]))
                    : selected.filter((item) => item !== option)
                onChange(next)
              }}
            />
            <span className='truncate'>{label(option)}</span>
          </label>
        )
      })}
    </div>
  )
}

type DiagramTabProps = {
  diagram: DiagramPayload | null
  diagramType: string
  setDiagramType: (type: string) => void
  views: SysmlElement[]
  selectedViewId: string
  setSelectedViewId: (viewId: string) => void
  viewScope: ViewPayload | null
  metamodel: Metamodel | null
  elements: SysmlElement[]
  selectedId: string
  setSelectedId: (id: string) => void
  onRefresh: () => void
  onSaveElement: (
    element: SysmlElement,
    successMessage: string,
    nextSelectedId?: string
  ) => void
  diagramPositions: Record<string, { x: number; y: number }>
  onDiagramPositionsChange: (
    positions: Record<string, { x: number; y: number }>
  ) => void
  busy: string
}

function DiagramTab(props: DiagramTabProps) {
  return (
    <div className='grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]'>
      <Card className='sysml-card self-start xl:sticky xl:top-32'>
        <CardHeader>
          <CardTitle>图谱设置</CardTitle>
          <CardDescription>按不同 SysML 视角查看关系网络</CardDescription>
        </CardHeader>
        <CardContent className='space-y-4'>
          <Field label='View scope'>
            <Select
              value={props.selectedViewId}
              onValueChange={props.setSelectedViewId}
            >
              <SelectTrigger className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='all'>All model elements</SelectItem>
                {props.views.map((view) => (
                  <SelectItem key={view.id} value={view.id}>
                    {view.name || view.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label='图谱类型'>
            <Select value={props.diagramType} onValueChange={props.setDiagramType}>
              <SelectTrigger className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.keys(props.metamodel?.diagram_types || {}).map((type) => (
                  <SelectItem key={type} value={type}>
                    {displayDiagramNames[type] || type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          {props.viewScope && (
            <div className='rounded-md border bg-muted/30 p-3 text-sm'>
              <div className='font-medium'>{props.viewScope.view.name}</div>
              <p className='mt-1 text-xs text-muted-foreground'>
                {props.viewScope.element_count} elements in this View /{' '}
                {Object.entries(props.viewScope.summary)
                  .map(([type, count]) => `${type}: ${count}`)
                  .join(', ') || 'No scoped elements'}
              </p>
            </div>
          )}
          <Button variant='outline' onClick={props.onRefresh}>
            <RefreshCw className='size-4' />
            刷新图谱
          </Button>
          <Separator />
          <div className='grid gap-2'>
            <p className='text-sm font-medium'>当前元素</p>
            <ScrollArea className='h-[260px] rounded-md border'>
              <div className='divide-y'>
                {props.elements.map((element) => (
                  <button
                    key={element.id}
                    type='button'
                    onClick={() => props.setSelectedId(element.id)}
                    className={cn(
                      'flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-muted',
                      props.selectedId === element.id && 'bg-muted'
                    )}
                  >
                    <span className='truncate font-mono'>{element.id}</span>
                    <Badge variant='outline'>{labelType(element.type)}</Badge>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </div>
        </CardContent>
      </Card>

      <Card className='sysml-card overflow-hidden'>
        <CardHeader>
          <div className='flex items-center justify-between gap-3'>
            <div>
              <CardTitle>
                {props.viewScope
                  ? `View Graph: ${props.viewScope.view.name || props.viewScope.view.id}`
                  : displayDiagramNames[props.diagramType] || 'Model Graph'}
              </CardTitle>
              <CardDescription>
                {props.diagram?.nodes.length || 0} 节点 / {props.diagram?.edges.length || 0} 关系
              </CardDescription>
            </div>
            <Badge variant='secondary'>React Flow</Badge>
          </div>
        </CardHeader>
        <CardContent className='p-0'>
          <DiagramCanvas
            diagram={props.diagram}
            elements={props.elements}
            selectedId={props.selectedId}
            onSelect={props.setSelectedId}
            metamodel={props.metamodel}
            onSaveElement={props.onSaveElement}
            diagramPositions={props.diagramPositions}
            onDiagramPositionsChange={props.onDiagramPositionsChange}
            busy={props.busy}
          />
        </CardContent>
      </Card>
    </div>
  )
}

function DiagramCanvas({
  diagram,
  elements,
  selectedId,
  onSelect,
  metamodel,
  onSaveElement,
  diagramPositions,
  onDiagramPositionsChange,
  busy,
}: {
  diagram: DiagramPayload | null
  elements: SysmlElement[]
  selectedId: string
  onSelect: (id: string) => void
  metamodel: Metamodel | null
  onSaveElement: (
    element: SysmlElement,
    successMessage: string,
    nextSelectedId?: string
  ) => void
  diagramPositions: Record<string, { x: number; y: number }>
  onDiagramPositionsChange: (
    positions: Record<string, { x: number; y: number }>
  ) => void
  busy: string
}) {
  const [nodes, setNodes] = useState<SysmlFlowNode[]>([])
  const [edges, setEdges] = useState<SysmlFlowEdge[]>([])
  const [selectedEdgeId, setSelectedEdgeId] = useState('')
  const [edgeRelationType, setEdgeRelationType] = useState('')
  const relationTypes = Object.keys(metamodel?.relation_labels || relationNames)
  const elementMap = useMemo(
    () => new Map(elements.map((element) => [element.id, element])),
    [elements]
  )

  const editNode = useCallback(
    (id: string) => {
      const element = elementMap.get(id)
      if (!element) return
      const nextName = window.prompt('节点名称', element.name || '')
      if (nextName === null) return
      const nextDescription = window.prompt(
        '节点描述',
        element.description || ''
      )
      if (nextDescription === null) return
      onSaveElement(
        {
          ...element,
          name: nextName.trim() || element.name,
          description: nextDescription.trim(),
        },
        '节点已更新',
        element.id
      )
    },
    [elementMap, onSaveElement]
  )

  const nodeTypes = useMemo(() => ({ sysml: SysmlFlowNodeCard }), [])

  useEffect(() => {
    if (!diagram) {
      setNodes([])
      setEdges([])
      setSelectedEdgeId('')
      return
    }

    setNodes(
      layoutDiagramNodes(diagram, elements).map((node) => {
        const element = elementMap.get(node.id)
        const position = diagramPositions[node.id] || node.position
        return {
          id: node.id,
          type: 'sysml',
          position,
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          width: nodeWidth,
          height: nodeHeight,
          selected: selectedId === node.id,
          data: {
            element: element || {
              id: node.id,
              type: node.type,
              name: node.name,
              stereotype: node.type.toLowerCase(),
              description: '',
              owner: '',
              attributes: {},
              relations: [],
            },
            label: node.label,
            onEdit: editNode,
          },
        }
      })
    )
    const edgeCounts = new Map<string, number>()
    setEdges(
      diagram.edges.map((edge, index) => {
        const pairKey = `${edge.source}->${edge.target}`
        const parallelIndex = edgeCounts.get(pairKey) || 0
        edgeCounts.set(pairKey, parallelIndex + 1)
        return {
          id: edgeId(edge.source, edge.target, edge.type, index),
          source: edge.source,
          target: edge.target,
          type: 'smoothstep',
          label: labelRelation(edge.type),
          sourceHandle: 'out',
          targetHandle: 'in',
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 18,
            height: 18,
          },
          reconnectable: true,
          style: {
            stroke: edgeColor(edge.type),
            strokeWidth: 1.6,
          },
          labelStyle: {
            fill: 'var(--muted-foreground)',
            fontSize: 12,
            fontWeight: 500,
          },
          labelBgStyle: {
            fill: 'var(--background)',
            fillOpacity: 0.92,
          },
          labelBgPadding: [8, 4],
          labelBgBorderRadius: 4,
          pathOptions: {
            borderRadius: 12,
            offset: 32 + parallelIndex * 18,
          },
          data: {
            relationType: edge.type,
            relationLabel: labelRelation(edge.type),
          },
        }
      })
    )
  }, [diagram, diagramPositions, editNode, elementMap, selectedId])

  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId)

  useEffect(() => {
    setEdgeRelationType(selectedEdge?.data?.relationType || relationTypes[0] || '')
  }, [relationTypes, selectedEdge?.data?.relationType])

  const onNodesChange: OnNodesChange<SysmlFlowNode> = useCallback(
    (changes: NodeChange<SysmlFlowNode>[]) => {
      setNodes((current) => applyNodeChanges(changes, current))
      const moved = changes.reduce<Record<string, { x: number; y: number }>>(
        (acc, change) => {
          if (change.type === 'position' && change.position) {
            acc[change.id] = change.position
          }
          return acc
        },
        {}
      )
      if (Object.keys(moved).length) onDiagramPositionsChange(moved)
    },
    [onDiagramPositionsChange]
  )

  const onEdgesChange: OnEdgesChange<SysmlFlowEdge> = useCallback(
    (changes: EdgeChange<SysmlFlowEdge>[]) => {
      const removed = changes.find((change) => change.type === 'remove')
      if (removed) {
        const edge = edges.find((item) => item.id === removed.id)
        if (edge) removeRelationEdge(edge, elementMap, onSaveElement)
        if (selectedEdgeId === removed.id) setSelectedEdgeId('')
      }
      setEdges((current) => applyEdgeChanges(changes, current))
    },
    [edges, elementMap, onSaveElement, selectedEdgeId]
  )

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return
      const relationType = edgeRelationType || relationTypes[0] || 'satisfy'
      const source = elementMap.get(connection.source)
      if (!source) return
      const relationExists = (source.relations || []).some(
        (relation) =>
          relation.type === relationType && relation.target === connection.target
      )
      if (relationExists) {
        toast.info('该关系已存在')
        return
      }
      const nextEdge: SysmlFlowEdge = {
        id: edgeId(connection.source, connection.target, relationType, edges.length),
        source: connection.source,
        target: connection.target,
        type: 'smoothstep',
        label: labelRelation(relationType),
        sourceHandle: connection.sourceHandle || 'out',
        targetHandle: connection.targetHandle || 'in',
        markerEnd: { type: MarkerType.ArrowClosed },
        reconnectable: true,
        style: {
          stroke: edgeColor(relationType),
          strokeWidth: 1.6,
        },
        labelStyle: {
          fill: 'var(--muted-foreground)',
          fontSize: 12,
          fontWeight: 500,
        },
        labelBgStyle: {
          fill: 'var(--background)',
          fillOpacity: 0.92,
        },
        labelBgPadding: [8, 4],
        labelBgBorderRadius: 4,
        pathOptions: {
          borderRadius: 12,
          offset: 32,
        },
        data: {
          relationType,
          relationLabel: labelRelation(relationType),
        },
      }
      setEdges((current) => addEdge(nextEdge, current))
      onSaveElement(
        {
          ...source,
          relations: [
            ...(source.relations || []),
            { type: relationType, target: connection.target },
          ],
        },
        '关系已添加',
        source.id
      )
    },
    [edgeRelationType, edges.length, elementMap, onSaveElement, relationTypes]
  )

  const onReconnect: OnReconnect<SysmlFlowEdge> = useCallback(
    (oldEdge, connection) => {
      if (!connection.source || !connection.target) return
      const relationType = oldEdge.data?.relationType || edgeRelationType || 'satisfy'
      const oldSource = elementMap.get(oldEdge.source)
      const nextSource = elementMap.get(connection.source)
      if (!oldSource || !nextSource) return
      setEdges((current) => reconnectEdge(oldEdge, connection, current))
      const withoutOldRelation = (oldSource.relations || []).filter(
        (relation) =>
          !(
            relation.type === relationType &&
            relation.target === oldEdge.target
          )
      )
      if (oldSource.id === nextSource.id) {
        onSaveElement(
          {
            ...oldSource,
            relations: [
              ...withoutOldRelation,
              { type: relationType, target: connection.target },
            ],
          },
          '关系已重连',
          oldSource.id
        )
        return
      }
      onSaveElement(
        { ...oldSource, relations: withoutOldRelation },
        '原关系已移除',
        nextSource.id
      )
      window.setTimeout(() => {
        onSaveElement(
          {
            ...nextSource,
            relations: [
              ...(nextSource.relations || []),
              { type: relationType, target: connection.target },
            ],
          },
          '关系已重连',
          nextSource.id
        )
      }, 0)
    },
    [edgeRelationType, elementMap, onSaveElement]
  )

  if (!diagram || !diagram.nodes.length) {
    return (
      <div className='h-[560px] bg-muted/30'>
        <EmptyState title='暂无图谱' description='当前模型没有可绘制的节点' />
      </div>
    )
  }

  return (
    <div className='h-[620px] bg-muted/30'>
      <ReactFlow<SysmlFlowNode, SysmlFlowEdge>
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onReconnect={onReconnect}
        onNodeClick={(_, node) => onSelect(node.id)}
        onNodeDoubleClick={(_, node) => editNode(node.id)}
        onEdgeClick={(_, edge) => {
          setSelectedEdgeId(edge.id)
          setEdgeRelationType(edge.data?.relationType || relationTypes[0] || '')
        }}
        fitView
        fitViewOptions={{ padding: 0.08, maxZoom: 1.05 }}
        minZoom={0.35}
        maxZoom={2.5}
        panOnDrag
        zoomOnScroll
        zoomOnPinch
        nodesDraggable
        nodesConnectable
        edgesReconnectable
        connectionRadius={32}
        defaultEdgeOptions={{
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
          interactionWidth: 24,
        }}
        className='sysml-flow'
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          size={1.2}
          color='var(--border)'
        />
        <MiniMap
          pannable
          zoomable
          style={{ width: 160, height: 110 }}
          nodeBorderRadius={8}
          nodeColor={(node) =>
            node.selected ? 'var(--primary)' : 'var(--muted-foreground)'
          }
          maskColor='color-mix(in oklch, var(--background) 70%, transparent)'
        />
        <Controls position='bottom-left' />
        <div className='nodrag nowheel absolute right-3 top-3 z-10 grid w-[220px] gap-3 rounded-md border bg-background/95 p-3 shadow-sm backdrop-blur'>
          <Field label='新连线类型'>
            <Select value={edgeRelationType} onValueChange={setEdgeRelationType}>
              <SelectTrigger className='w-full'>
                <SelectValue placeholder='选择关系' />
              </SelectTrigger>
              <SelectContent>
                {relationTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {labelRelation(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          {selectedEdge ? (
            <div className='grid gap-2 border-t pt-3'>
              <div className='min-w-0 text-xs text-muted-foreground'>
                已选关系：{selectedEdge.source} {'->'} {selectedEdge.target}
              </div>
              <div className='flex gap-2'>
                <Button
                  variant='outline'
                  size='sm'
                  disabled={busy === 'diagram-edit'}
                  onClick={() => {
                    const source = elementMap.get(selectedEdge.source)
                    if (!source) return
                    const oldType = selectedEdge.data?.relationType || ''
                    const nextRelations = (source.relations || []).map(
                      (relation) =>
                        relation.type === oldType &&
                        relation.target === selectedEdge.target
                          ? { ...relation, type: edgeRelationType }
                          : relation
                    )
                    onSaveElement(
                      { ...source, relations: nextRelations },
                      '关系类型已更新',
                      source.id
                    )
                  }}
                >
                  保存类型
                </Button>
                <Button
                  variant='destructive'
                  size='sm'
                  disabled={busy === 'diagram-edit'}
                  onClick={() => {
                    removeRelationEdge(selectedEdge, elementMap, onSaveElement)
                    setEdges((current) =>
                      current.filter((edge) => edge.id !== selectedEdge.id)
                    )
                    setSelectedEdgeId('')
                  }}
                >
                  删除关系
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      </ReactFlow>
    </div>
  )
}

function SysmlFlowNodeCard({ data, selected }: NodeProps<SysmlFlowNode>) {
  const element = data.element
  return (
    <div
      className={cn(
        'group w-[230px] rounded-md border bg-background shadow-sm transition-all',
        selected && 'border-primary shadow-md ring-2 ring-ring/25'
      )}
    >
      <Handle
        type='target'
        id='in'
        position={Position.Left}
        className='!h-3 !w-3 !border-2 !border-background !bg-primary'
      />
      <div className='grid w-full gap-2 p-3'>
        <div className='flex min-w-0 items-start justify-between gap-2'>
          <span className='truncate font-mono text-xs font-semibold'>
            {element.id}
          </span>
          <div className='flex shrink-0 items-center gap-1'>
            <span
              className='rounded-sm px-1.5 py-0.5 text-[10px] font-medium'
              style={{
                background: `${nodeAccentColor(element.type)}22`,
                color: nodeAccentColor(element.type),
              }}
            >
              {labelType(element.type)}
            </span>
            <button
              type='button'
              className='nodrag rounded-sm p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground group-hover:opacity-100'
              onClick={() => data.onEdit(element.id)}
              title='编辑节点'
            >
              <Edit3 className='size-3.5' />
            </button>
          </div>
        </div>
        <div className='line-clamp-2 text-sm font-medium'>
          {element.name || '未命名元素'}
        </div>
        <p className='line-clamp-2 text-xs text-muted-foreground'>
          {element.description || data.label || '暂无描述'}
        </p>
      </div>
      <Handle
        type='source'
        id='out'
        position={Position.Right}
        className='!h-3 !w-3 !border-2 !border-background !bg-primary'
      />
    </div>
  )
}

function layoutDiagramNodes(diagram: DiagramPayload, elements: SysmlElement[]) {
  const elementMap = new Map(elements.map((element) => [element.id, element]))
  const incoming = new Map<string, number>()
  const outgoing = new Map<string, number>()
  diagram.nodes.forEach((node) => {
    incoming.set(node.id, 0)
    outgoing.set(node.id, 0)
  })
  diagram.edges.forEach((edge) => {
    outgoing.set(edge.source, (outgoing.get(edge.source) || 0) + 1)
    incoming.set(edge.target, (incoming.get(edge.target) || 0) + 1)
  })

  const columns = buildDiagramColumns(diagram.type)
  const columnIndex = new Map<string, number>()
  columns.forEach((types, index) => {
    types.forEach((type) => columnIndex.set(type, index))
  })

  const grouped = new Map<number, DiagramPayload['nodes']>()
  diagram.nodes.forEach((node) => {
    const element = elementMap.get(node.id)
    const type = element?.type || node.type
    const fallbackColumn = Math.max(
      0,
      Math.min(columns.length - 1, Math.round((node.x - 90) / 230))
    )
    const column = columnIndex.get(type) ?? fallbackColumn
    const items = grouped.get(column) || []
    items.push(node)
    grouped.set(column, items)
  })

  return diagram.nodes.map((node) => {
    const element = elementMap.get(node.id)
    const type = element?.type || node.type
    const fallbackColumn = Math.max(
      0,
      Math.min(columns.length - 1, Math.round((node.x - 90) / 230))
    )
    const column = columnIndex.get(type) ?? fallbackColumn
    const peers = (grouped.get(column) || []).sort((left, right) => {
      const leftScore =
        (incoming.get(left.id) || 0) * 2 + (outgoing.get(left.id) || 0)
      const rightScore =
        (incoming.get(right.id) || 0) * 2 + (outgoing.get(right.id) || 0)
      if (rightScore !== leftScore) return rightScore - leftScore
      return left.id.localeCompare(right.id)
    })
    const row = peers.findIndex((peer) => peer.id === node.id)
    const columnWidth = 290
    const rowHeight = 132
    const offset = (column % 2) * 24
    return {
      ...node,
      position: {
        x: 60 + column * columnWidth,
        y: 48 + Math.max(row, 0) * rowHeight + offset,
      },
    }
  })
}

function buildDiagramColumns(diagramType: string) {
  if (diagramType === 'requirements') {
    return [
      ['Requirement'],
      ['Activity', 'Block', 'Interface'],
      ['Constraint', 'TestCase'],
    ]
  }
  if (diagramType === 'structure') {
    return [['Block'], ['Port'], ['Interface'], ['Constraint']]
  }
  if (diagramType === 'behavior') {
    return [['Activity'], ['State'], ['Block']]
  }
  return [
    ['Requirement'],
    ['Activity'],
    ['Block'],
    ['Port', 'Interface'],
    ['Constraint', 'TestCase', 'State', 'View'],
  ]
}

function edgeColor(type: string) {
  const colors: Record<string, string> = {
    satisfy: 'oklch(0.55 0.15 150)',
    verify: 'oklch(0.58 0.15 245)',
    refine: 'oklch(0.57 0.16 35)',
    compose: 'oklch(0.5 0.12 260)',
    expose: 'oklch(0.56 0.13 190)',
    connect: 'oklch(0.52 0.11 210)',
    allocate: 'oklch(0.58 0.14 300)',
    flow: 'oklch(0.6 0.15 70)',
    transition: 'oklch(0.55 0.16 20)',
    constrain: 'oklch(0.52 0.13 330)',
  }
  return colors[type] || 'var(--muted-foreground)'
}

function nodeAccentColor(type: string) {
  const colors: Record<string, string> = {
    Requirement: 'oklch(0.55 0.15 150)',
    Block: 'oklch(0.5 0.12 260)',
    Activity: 'oklch(0.58 0.14 300)',
    Interface: 'oklch(0.52 0.11 210)',
    Port: 'oklch(0.56 0.13 190)',
    Constraint: 'oklch(0.52 0.13 330)',
    State: 'oklch(0.55 0.16 20)',
    TestCase: 'oklch(0.58 0.15 245)',
    View: 'oklch(0.55 0.1 95)',
    Viewpoint: 'oklch(0.58 0.12 75)',
  }
  return colors[type] || 'var(--muted-foreground)'
}

function edgeId(source: string, target: string, type: string, index: number) {
  return `${source}--${type}--${target}--${index}`
}

function removeRelationEdge(
  edge: SysmlFlowEdge,
  elementMap: Map<string, SysmlElement>,
  onSaveElement: (
    element: SysmlElement,
    successMessage: string,
    nextSelectedId?: string
  ) => void
) {
  const source = elementMap.get(edge.source)
  if (!source) return
  const relationType = edge.data?.relationType || ''
  onSaveElement(
    {
      ...source,
      relations: (source.relations || []).filter(
        (relation) =>
          !(relation.type === relationType && relation.target === edge.target)
      ),
    },
    '关系已删除',
    source.id
  )
}

function TraceTab({
  traceability,
  busy,
  onRefresh,
}: {
  traceability: TraceabilityRow[]
  busy: string
  onRefresh: () => void
}) {
  return (
    <Card className='sysml-card'>
      <CardHeader>
        <div className='flex items-center justify-between gap-3'>
          <div>
            <CardTitle>需求追踪矩阵</CardTitle>
            <CardDescription>查看需求到模块、测试、约束的闭环情况</CardDescription>
          </div>
          <Button variant='outline' onClick={onRefresh} disabled={busy === 'trace'}>
            {busy === 'trace' ? (
              <Loader2 className='size-4 animate-spin' />
            ) : (
              <RefreshCw className='size-4' />
            )}
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {traceability.length ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>需求</TableHead>
                <TableHead>满足元素</TableHead>
                <TableHead>验证元素</TableHead>
                <TableHead>约束</TableHead>
                <TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {traceability.map((row) => (
                <TableRow key={row.requirement.id}>
                  <TableCell>
                    <div className='font-mono font-medium'>
                      {row.requirement.id}
                    </div>
                    <div className='text-muted-foreground'>
                      {row.requirement.name}
                    </div>
                  </TableCell>
                  <TableCell>{formatRefs(row.satisfied_by)}</TableCell>
                  <TableCell>{formatRefs(row.verified_by)}</TableCell>
                  <TableCell>{formatRefs(row.constrained_by || [])}</TableCell>
                  <TableCell>
                    <TraceBadge status={row.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyState title='暂无追踪数据' description='点击刷新加载追踪矩阵' />
        )}
      </CardContent>
    </Card>
  )
}

type VersionTabProps = {
  branches: Branch[]
  commits: Commit[]
  tags: Tag[]
  auditEvents: AuditEvent[]
  diff: DiffPayload | null
  diffFrom: string
  setDiffFrom: (value: string) => void
  diffTo: string
  setDiffTo: (value: string) => void
  rollbackCommit: string
  setRollbackCommit: (value: string) => void
  newBranch: string
  setNewBranch: (value: string) => void
  newTag: string
  setNewTag: (value: string) => void
  mergeSource: string
  setMergeSource: (value: string) => void
  forceMerge: boolean
  setForceMerge: (value: boolean) => void
  onRefresh: () => void
  onDiff: () => void
  onRollback: () => void
  onCreateBranch: () => void
  onCreateTag: () => void
  onMerge: () => void
  busy: string
}

function VersionTab(props: VersionTabProps) {
  const commitOptions = [
    { id: 'working', label: 'working' },
    ...props.tags.map((tag) => ({
      id: `tag:${tag.id}`,
      label: `tag:${tag.name} / ${shortLabel(tag.commit, 14)}`,
    })),
    ...props.commits.map((commit) => ({
      id: commit.id,
      label: `${shortLabel(commit.id, 13)} / ${shortLabel(commit.message, 28)}`,
    })),
  ]
  return (
    <div className='space-y-4'>
      <Card className='sysml-card'>
        <CardHeader>
          <div className='flex items-center justify-between'>
            <div>
              <CardTitle>版本操作</CardTitle>
              <CardDescription>分支、Diff、回滚和合并</CardDescription>
            </div>
            <Button variant='outline' size='sm' onClick={props.onRefresh}>
              <RefreshCw className='size-4' />
            </Button>
          </div>
        </CardHeader>
        <CardContent className='grid gap-4 lg:grid-cols-2 2xl:grid-cols-[1.25fr_1.25fr_1fr_1fr_1fr] [&>div]:min-w-0 [&>div]:rounded-md [&>div]:border [&>div]:bg-muted/20 [&>div]:p-3 [&>[data-orientation=horizontal]]:hidden'>
          <div className='grid gap-3'>
            <div className='grid gap-3 sm:grid-cols-2'>
              <Field label='Diff From'>
                <Select value={props.diffFrom} onValueChange={props.setDiffFrom}>
                  <SelectTrigger className='w-full min-w-0 overflow-hidden [&>span]:truncate'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {commitOptions.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label='Diff To'>
                <Select value={props.diffTo} onValueChange={props.setDiffTo}>
                  <SelectTrigger className='w-full min-w-0 overflow-hidden [&>span]:truncate'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {commitOptions.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>
            <Button onClick={props.onDiff} disabled={props.busy === 'diff'}>
              <GitCompare className='size-4' />
              运行 Diff
            </Button>
          </div>
          <Separator />
          <div className='grid gap-3'>
            <Field label='回滚提交'>
              <Select
                value={props.rollbackCommit}
                onValueChange={props.setRollbackCommit}
              >
                <SelectTrigger className='w-full min-w-0 overflow-hidden [&>span]:truncate'>
                  <SelectValue placeholder='选择提交' />
                </SelectTrigger>
                <SelectContent>
                  {props.commits.map((commit) => (
                    <SelectItem key={commit.id} value={commit.id}>
                      {commit.id} / {commit.message}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Button variant='destructive' onClick={props.onRollback}>
              <RotateCcw className='size-4' />
              回滚
            </Button>
          </div>
          <Separator />
          <div className='grid gap-3'>
            <Field label='新分支'>
              <Input
                placeholder='dev-power'
                value={props.newBranch}
                onChange={(event) => props.setNewBranch(event.target.value)}
              />
            </Field>
            <Button variant='outline' onClick={props.onCreateBranch}>
              <GitBranch className='size-4' />
              创建分支
            </Button>
          </div>
          <Separator />
          <div className='grid gap-3'>
            <Field label='标签快照'>
              <Input
                placeholder='PDR-baseline'
                value={props.newTag}
                onChange={(event) => props.setNewTag(event.target.value)}
              />
            </Field>
            <Button
              variant='outline'
              onClick={props.onCreateTag}
              disabled={props.busy === 'tag'}
            >
              <FileText className='size-4' />
              创建标签
            </Button>
            <p className='text-xs text-muted-foreground'>
              标签对应 OpenMBEE 的只读基线，用于冻结已提交的模型状态。
            </p>
          </div>
          <Separator />
          <div className='grid gap-3'>
            <Field label='合并来源'>
              <Select value={props.mergeSource} onValueChange={props.setMergeSource}>
                <SelectTrigger className='w-full'>
                  <SelectValue placeholder='选择分支' />
                </SelectTrigger>
                <SelectContent>
                  {props.branches.map((item) => (
                    <SelectItem key={item.name} value={item.name}>
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <label className='flex items-center gap-2 text-sm'>
              <Checkbox
                checked={props.forceMerge}
                onCheckedChange={(checked) => props.setForceMerge(Boolean(checked))}
              />
              强制合并冲突
            </label>
            <Button variant='outline' onClick={props.onMerge}>
              <GitMerge className='size-4' />
              合并
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className='space-y-4'>
        <Card className='sysml-card'>
          <CardHeader>
            <div className='flex items-center justify-between gap-3'>
              <div>
                <CardTitle>Diff 结果</CardTitle>
                <CardDescription>
                  {props.diff
                    ? `+${props.diff.summary.added} -${props.diff.summary.removed} ~${props.diff.summary.modified}`
                    : '尚未运行 Diff'}
                </CardDescription>
              </div>
              {props.diff && (
                <Badge variant='secondary'>
                  {props.diff.from} → {props.diff.to}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {props.diff ? (
              <div className='grid gap-4 md:grid-cols-3'>
                <DiffGroup title='新增' items={props.diff.added} />
                <DiffGroup title='删除' items={props.diff.removed} />
                <div className='rounded-md border p-3'>
                  <h3 className='mb-2 text-sm font-semibold'>修改</h3>
                  <div className='space-y-2 text-sm'>
                    {props.diff.modified.length ? (
                      props.diff.modified.map((item) => (
                        <div key={item.id} className='rounded-md bg-muted p-2'>
                          <div className='font-mono font-medium'>{item.id}</div>
                          <p className='text-xs text-muted-foreground'>
                            {item.changes.map((change) => change.field).join(', ')}
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className='text-muted-foreground'>无</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState title='等待 Diff' description='选择两个版本后运行 Diff' />
            )}
          </CardContent>
        </Card>

      <div className='grid gap-4 xl:grid-cols-3'>
          <Card className='sysml-card'>
            <CardHeader>
              <CardTitle>标签基线</CardTitle>
              <CardDescription>{props.tags.length} 个只读快照</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className='h-[320px]'>
                <div className='space-y-3'>
                  {props.tags.length ? (
                    props.tags.map((tag) => (
                      <div key={tag.id} className='rounded-md border p-3'>
                        <div className='flex items-center justify-between gap-2'>
                          <div className='font-mono text-sm font-semibold'>
                            {tag.name}
                          </div>
                          <Badge variant='secondary'>tag</Badge>
                        </div>
                        <p className='mt-1 text-xs text-muted-foreground'>
                          {tag.commit} / {tag.created_at}
                        </p>
                        <p className='mt-1 text-xs text-muted-foreground'>
                          {tag.element_count ?? '-'} elements / {tag.model_hash || '-'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <EmptyState
                      title='暂无标签'
                      description='创建标签后可在 Diff 中作为只读基线选择'
                    />
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
          <Card className='sysml-card'>
            <CardHeader>
              <CardTitle>提交记录</CardTitle>
              <CardDescription>{props.commits.length} 条提交</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className='h-[320px]'>
                <div className='space-y-3'>
                  {props.commits.map((commit) => (
                    <div key={commit.id} className='rounded-md border p-3'>
                      <div className='font-mono text-sm font-semibold'>
                        {commit.id}
                      </div>
                      <p className='mt-1 text-sm'>{commit.message}</p>
                      <p className='mt-1 text-xs text-muted-foreground'>
                        {commit.branch} / {commit.author} / {commit.created_at} /{' '}
                        {commit.element_count} elements
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
          <Card className='sysml-card'>
            <CardHeader>
              <CardTitle>审计日志</CardTitle>
              <CardDescription>{props.auditEvents.length} 条事件</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className='h-[320px]'>
                <div className='space-y-3'>
                  {props.auditEvents.map((event, index) => (
                    <div key={`${event.created_at}-${index}`} className='rounded-md border p-3'>
                      <div className='text-sm font-semibold'>{event.action}</div>
                      <p className='mt-1 text-xs text-muted-foreground'>
                        {event.branch_name || '-'} / {event.actor} / {event.created_at}
                      </p>
                      {event.element_id && (
                        <p className='mt-1 font-mono text-xs'>{event.element_id}</p>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function DiffGroup({ title, items }: { title: string; items: SysmlElement[] }) {
  return (
    <div className='rounded-md border p-3'>
      <h3 className='mb-2 text-sm font-semibold'>{title}</h3>
      <div className='space-y-2 text-sm'>
        {items.length ? (
          items.map((item) => (
            <div key={item.id} className='rounded-md bg-muted p-2'>
              <div className='font-mono font-medium'>{item.id}</div>
              <p className='truncate text-xs text-muted-foreground'>
                {labelType(item.type)} / {item.name}
              </p>
            </div>
          ))
        ) : (
          <p className='text-muted-foreground'>无</p>
        )}
      </div>
    </div>
  )
}

type DocgenTabProps = {
  template: string
  setTemplate: (value: string) => void
  elements: SysmlElement[]
  views: SysmlElement[]
  docViewId: string
  setDocViewId: (value: string) => void
  validation: ValidationPayload | null
  documents: DocumentRecord[]
  currentDocument: DocumentRecord | null
  onReset: () => void
  onGenerate: () => void
  onAiDraft: (mode: AiDocgenMode) => void
  onOpen: (id: string) => void
  onDownload: (format: 'html' | 'markdown' | 'pdf') => void
  busy: string
}

function DocgenTab(props: DocgenTabProps) {
  return (
    <div className='sysml-doc-grid'>
      <Card className='sysml-card'>
        <CardHeader>
          <div className='flex items-center justify-between gap-3'>
            <div>
              <CardTitle>DocGen {'\u6a21\u677f'}</CardTitle>
              <CardDescription>{'\u4f7f\u7528\u5360\u4f4d\u7b26\u751f\u6210 HTML / Markdown / PDF'}</CardDescription>
            </div>
            <div className='flex gap-2'>
              <DocumentHistorySheet
                documents={props.documents}
                onOpen={props.onOpen}
              />
              <Button variant='outline' size='sm' onClick={props.onReset}>
                <RotateCcw className='size-4' />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className='space-y-4'>
          <Field label='Document scope'>
            <Select value={props.docViewId} onValueChange={props.setDocViewId}>
              <SelectTrigger className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='all'>Full model document</SelectItem>
                {props.views.map((view) => (
                  <SelectItem key={view.id} value={view.id}>
                    {view.name || view.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Suspense
            fallback={
              <div className='flex h-[420px] items-center justify-center rounded-md border bg-muted/30 text-sm text-muted-foreground'>
                <Loader2 className='size-4 animate-spin' />
                Loading editor
              </div>
            }
          >
            <DocgenTemplateEditor
              value={props.template}
              onChange={props.setTemplate}
              elements={props.elements}
              validation={props.validation}
            />
          </Suspense>
          <div className='flex flex-wrap gap-2'>
            <Button
              variant='secondary'
              onClick={() => props.onAiDraft('full')}
              disabled={props.busy === 'ai-docgen-full'}
            >
              {props.busy === 'ai-docgen-full' ? (
                <Loader2 className='size-4 animate-spin' />
              ) : (
                <Sparkles className='size-4' />
              )}
              {'AI \u751f\u6210\u7ae0\u8282'}
            </Button>
            <Button
              onClick={props.onGenerate}
              disabled={props.busy === 'generate-document'}
            >
              {props.busy === 'generate-document' ? (
                <Loader2 className='size-4 animate-spin' />
              ) : (
                <FileText className='size-4' />
              )}
              {'\u751f\u6210'}
            </Button>
            <Button variant='outline' onClick={() => props.onDownload('markdown')}>
              Markdown
            </Button>
            <Button variant='outline' onClick={() => props.onDownload('html')}>
              HTML
            </Button>
            <Button variant='outline' onClick={() => props.onDownload('pdf')}>
              PDF
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className='sysml-card overflow-hidden'>
        <CardHeader>
          <div className='flex items-center justify-between gap-3'>
            <div>
              <CardTitle>{'\u6587\u6863\u9884\u89c8'}</CardTitle>
              <CardDescription>
                {props.currentDocument?.id || '\u5c1a\u672a\u751f\u6210\u6587\u6863'}
              </CardDescription>
            </div>
            {props.currentDocument && <Badge variant='secondary'>HTML</Badge>}
          </div>
        </CardHeader>
        <CardContent className='p-0'>
          {props.currentDocument?.html ? (
            <iframe
              title='Document preview'
              srcDoc={props.currentDocument.html}
              className='h-[720px] w-full border-0 bg-background'
            />
          ) : (
            <div className='h-[720px]'>
              <EmptyState title={'\u7b49\u5f85\u751f\u6210'} description={'\u70b9\u51fb\u751f\u6210\u6309\u94ae\u9884\u89c8\u6587\u6863'} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function DocumentHistorySheet({
  documents,
  onOpen,
}: {
  documents: DocumentRecord[]
  onOpen: (id: string) => void
}) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant='outline' size='sm'>
          <FileText className='size-4' />
          {'\u5386\u53f2'}
        </Button>
      </SheetTrigger>
      <SheetContent side='right' className='w-[420px] sm:max-w-[420px]'>
        <SheetHeader>
          <SheetTitle>Document history</SheetTitle>
          <SheetDescription>{'\u6253\u5f00\u5df2\u751f\u6210\u7684\u6587\u6863\u7248\u672c'}</SheetDescription>
        </SheetHeader>
        <ScrollArea className='min-h-0 flex-1 px-4 pb-4'>
          {documents.length ? (
            <div className='space-y-2'>
              {documents.map((document) => (
                <button
                  key={document.id}
                  type='button'
                  onClick={() => onOpen(document.id)}
                  className='grid w-full gap-1 rounded-md border bg-background px-3 py-3 text-left text-sm transition-colors hover:bg-muted'
                >
                  <span className='truncate font-mono font-semibold'>{document.id}</span>
                  <span className='truncate text-xs text-muted-foreground'>
                    {document.created_at}
                  </span>
                  <span className='truncate font-mono text-[11px] text-muted-foreground'>
                    {document.model_hash}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState title={'\u6682\u65e0\u6587\u6863'} description={'\u751f\u6210\u540e\u4f1a\u51fa\u73b0\u5728\u8fd9\u91cc'} />
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}

type MdkTabProps = {
  adapters: MdkAdapter[]
  tool: string
  setTool: (value: string) => void
  filename: string
  setFilename: (value: string) => void
  content: string
  setContent: (value: string) => void
  parseResult: MdkParseResponse | null
  importJob: MdkImportJob | null
  commit: boolean
  setCommit: (value: boolean) => void
  message: string
  setMessage: (value: string) => void
  onRefreshAdapters: () => void
  onParse: (content?: string, filename?: string, tool?: string) => void
  onCreateJob: () => void
  onApplyJob: () => void
  busy: string
}

type AssistantTabProps = {
  messages: AiChatMessage[]
  question: string
  setQuestion: (value: string) => void
  onAsk: () => void
  busy: string
}

function AssistantTab(props: AssistantTabProps) {
  const examples = [
    '\u5f53\u524d\u6a21\u578b\u6709\u54ea\u4e9b\u9700\u6c42\u8fd8\u6ca1\u6709\u9a8c\u8bc1\u95ed\u73af\uff1f',
    '\u89e3\u91ca\u4e00\u4e0b\u8fd9\u4e2a\u7cfb\u7edf\u7684\u8ffd\u6eaf\u77e9\u9635\u3002',
    '\u54ea\u4e9b\u6a21\u578b\u5143\u7d20\u9002\u5408\u5199\u8fdb\u7cfb\u7edf\u67b6\u6784\u7ae0\u8282\uff1f',
    '\u8fd9\u4e2a\u6a21\u578b\u76ee\u524d\u6700\u5927\u7684\u8d28\u91cf\u98ce\u9669\u662f\u4ec0\u4e48\uff1f',
  ]

  return (
    <div className='grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]'>
      <Card className='sysml-card'>
        <CardHeader>
          <div className='flex items-center gap-2'>
            <div className='flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground'>
              <Sparkles className='size-4' />
            </div>
            <div>
              <CardTitle>SysML Assistant</CardTitle>
              <CardDescription>{'\u57fa\u4e8e MMS \u6a21\u578b\u7684\u95ee\u7b54\u52a9\u624b'}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className='space-y-4'>
          <div className='space-y-2'>
            <div className='text-xs font-medium uppercase text-muted-foreground'>
              {'\u63a8\u8350\u95ee\u9898'}
            </div>
            {examples.map((example) => (
              <button
                key={example}
                type='button'
                className='w-full rounded-md border bg-background px-3 py-2 text-left text-sm leading-5 transition-colors hover:bg-muted'
                onClick={() => props.setQuestion(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className='sysml-card overflow-hidden'>
        <CardHeader className='border-b bg-muted/20'>
          <div className='flex items-center justify-between gap-3'>
            <div className='flex items-center gap-3'>
              <div className='flex size-10 items-center justify-center rounded-md border bg-background'>
                <MessageCircle className='size-5 text-primary' />
              </div>
              <div>
                <CardTitle>{'\u6a21\u578b\u95ee\u7b54\u7ebf\u7a0b'}</CardTitle>
                <CardDescription>{'\u8be2\u95ee\u9700\u6c42\u3001\u6a21\u5757\u3001\u8ffd\u8e2a\u5173\u7cfb\u6216\u6587\u6863\u751f\u6210\u6d41\u7a0b'}</CardDescription>
              </div>
            </div>
            <Badge variant='secondary'>Assistant</Badge>
          </div>
        </CardHeader>
        <CardContent className='grid h-[680px] grid-rows-[1fr_auto] gap-0 p-0'>
          <ScrollArea className='min-h-0 p-5'>
            {props.messages.length || props.busy === 'ai-chat' ? (
              <div className='space-y-5'>
                {props.messages.map((message, index) => (
                  <AssistantMessageBubble
                    key={`${message.role}-${index}`}
                    message={message}
                  />
                ))}
                {props.busy === 'ai-chat' ? <AssistantLoadingBubble /> : null}
              </div>
            ) : (
              <div className='flex h-[460px] items-center justify-center'>
                <div className='max-w-md text-center'>
                  <div className='mx-auto flex size-12 items-center justify-center rounded-md border bg-background'>
                    <Sparkles className='size-5 text-primary' />
                  </div>
                  <h3 className='mt-4 text-base font-semibold'>{'\u5f00\u59cb\u8be2\u95ee\u6a21\u578b'}</h3>
                  <p className='mt-2 text-sm text-muted-foreground'>
                    {'\u4f8b\u5982\u8be2\u95ee\u54ea\u4e9b\u9700\u6c42\u672a\u95ed\u73af\u3001\u67d0\u4e2a\u5143\u7d20\u7684\u4f9d\u636e\u3001\u6216\u8005\u5982\u4f55\u89e3\u91ca\u8ffd\u8e2a\u77e9\u9635\u3002'}
                  </p>
                </div>
              </div>
            )}
          </ScrollArea>
          <div className='border-t bg-background p-4'>
            <div className='rounded-lg border bg-muted/20 p-2'>
              <Textarea
                rows={3}
                value={props.question}
                onChange={(event) => props.setQuestion(event.target.value)}
                placeholder={'\u4f8b\u5982\uff1a\u54ea\u4e9b\u9700\u6c42\u8fd8\u6ca1\u6709\u6d4b\u8bd5\u7528\u4f8b\uff1f'}
                className='min-h-[86px] resize-none border-0 bg-transparent shadow-none focus-visible:ring-0'
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                    event.preventDefault()
                    props.onAsk()
                  }
                }}
              />
              <div className='flex items-center justify-between gap-2 px-2 pb-1'>
                <span className='text-xs text-muted-foreground'>{'Ctrl + Enter \u53d1\u9001'}</span>
                <Button
                  type='button'
                  onClick={props.onAsk}
                  disabled={props.busy === 'ai-chat'}
                >
                  {props.busy === 'ai-chat' ? (
                    <Loader2 className='size-4 animate-spin' />
                  ) : (
                    <Send className='size-4' />
                  )}
                  {'\u53d1\u9001'}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function AssistantMessageBubble({ message }: { message: AiChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-3', isUser && 'justify-end')}>
      {!isUser ? (
        <div className='flex size-9 shrink-0 items-center justify-center rounded-md border bg-background'>
          <Sparkles className='size-4 text-primary' />
        </div>
      ) : null}
      <div
        className={cn(
          'max-w-[82%] rounded-lg border px-4 py-3 text-sm leading-6 shadow-sm',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-background'
        )}
      >
        <div className='mb-2 flex items-center gap-2 text-xs font-medium opacity-80'>
          <span>{isUser ? '\u4f60' : 'Assistant'}</span>
          {!isUser ? <Badge variant='outline'>{'\u6a21\u578b\u4e0a\u4e0b\u6587'}</Badge> : null}
        </div>
        {isUser ? (
          <div className='whitespace-pre-wrap'>{message.content}</div>
        ) : (
          <MarkdownMessage content={message.content} compact />
        )}
      </div>
    </div>
  )
}

function AssistantLoadingBubble() {
  return (
    <div className='flex gap-3'>
      <div className='flex size-9 shrink-0 items-center justify-center rounded-md border bg-background'>
        <Sparkles className='size-4 text-primary' />
      </div>
      <div className='max-w-[82%] rounded-lg border bg-background px-4 py-3 shadow-sm'>
        <div className='mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground'>
          <Loader2 className='size-3.5 animate-spin' />
          Assistant {'\u6b63\u5728\u5206\u6790'}
        </div>
      </div>
    </div>
  )
}

function MdkTab(props: MdkTabProps) {
  const selectedAdapter = props.adapters.find((adapter) => adapter.id === props.tool)
  const report = props.parseResult?.mapping_report
  const canApply = Boolean(props.importJob && props.importJob.status === 'parsed')

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    const text = await file.text()
    const adapter = adapterFromFilename(file.name, props.adapters)
    const nextTool = adapter?.id || props.tool
    props.setFilename(file.name)
    props.setContent(text)
    if (adapter) props.setTool(adapter.id)
    event.target.value = ''
    props.onParse(text, file.name, nextTool)
  }

  return (
    <div className='grid gap-4 xl:grid-cols-[minmax(360px,0.42fr)_minmax(560px,0.58fr)]'>
      <div className='space-y-4'>
        <Card className='sysml-card'>
          <CardHeader>
            <div className='flex items-center justify-between gap-3'>
              <div>
                <CardTitle>外部工具适配器</CardTitle>
                <CardDescription>
                  Cameo / Jupyter / MATLAB / JSON / XMI 的统一接入能力
                </CardDescription>
              </div>
              <Button
                variant='outline'
                size='sm'
                onClick={props.onRefreshAdapters}
                disabled={props.busy === 'mdk-adapters'}
              >
                {props.busy === 'mdk-adapters' ? (
                  <Loader2 className='size-4 animate-spin' />
                ) : (
                  <RefreshCw className='size-4' />
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {props.adapters.length ? (
              <div className='grid gap-3'>
                {props.adapters.map((adapter) => (
                  <button
                    key={adapter.id}
                    type='button'
                    onClick={() => props.setTool(adapter.id)}
                    className={cn(
                      'rounded-md border p-3 text-left transition-colors hover:bg-muted/50',
                      props.tool === adapter.id && 'border-primary bg-muted'
                    )}
                  >
                    <div className='flex flex-wrap items-center justify-between gap-2'>
                      <div>
                        <div className='font-medium'>{adapter.label}</div>
                        <div className='font-mono text-xs text-muted-foreground'>
                          {adapter.id} / {adapter.vendor || 'SysML DocGen'} / v{adapter.version || '1.0.0'}
                        </div>
                      </div>
                      <Badge variant={adapter.can_write ? 'secondary' : 'outline'}>
                        {adapter.can_write ? 'read/write' : 'read only'}
                      </Badge>
                    </div>
                    <div className='mt-3 flex flex-wrap gap-1.5'>
                      <CapabilityBadge enabled={adapter.can_read} label='读' />
                      <CapabilityBadge enabled={adapter.can_write} label='写' />
                      <CapabilityBadge enabled={adapter.can_validate} label='校验' />
                      <CapabilityBadge enabled={adapter.can_commit} label='提交' />
                      <CapabilityBadge enabled={adapter.can_rollback} label='回滚' />
                    </div>
                    {adapter.limitations?.length ? (
                      <p className='mt-2 line-clamp-2 text-xs text-muted-foreground'>
                        {adapter.limitations.join('；')}
                      </p>
                    ) : null}
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState title='未加载适配器' description='点击刷新读取服务端能力声明' />
            )}
          </CardContent>
        </Card>

        <Card className='sysml-card'>
          <CardHeader>
            <CardTitle>导入设置</CardTitle>
            <CardDescription>
              解析成功后可导入当前项目分支，并选择是否自动提交
            </CardDescription>
          </CardHeader>
          <CardContent className='space-y-4'>
            <Field label='适配器'>
              <Select value={props.tool} onValueChange={props.setTool}>
                <SelectTrigger className='w-full'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {props.adapters.map((adapter) => (
                    <SelectItem key={adapter.id} value={adapter.id}>
                      {adapter.label}
                    </SelectItem>
                  ))}
                  {!props.adapters.length && <SelectItem value='json'>JSON</SelectItem>}
                </SelectContent>
              </Select>
            </Field>
            <Field label='文件名'>
              <Input
                value={props.filename}
                onChange={(event) => props.setFilename(event.target.value)}
                placeholder='model.json / model.xmi / analysis.ipynb'
              />
            </Field>
            <label className='flex items-center gap-2 text-sm'>
              <Checkbox
                checked={props.commit}
                onCheckedChange={(checked) => props.setCommit(Boolean(checked))}
              />
              导入后自动提交
            </label>
            <Field label='提交说明'>
              <Input
                value={props.message}
                onChange={(event) => props.setMessage(event.target.value)}
                disabled={!props.commit}
              />
            </Field>
            {selectedAdapter && (
              <Alert>
                <Wrench className='size-4' />
                <AlertTitle>{selectedAdapter.label}</AlertTitle>
                <AlertDescription>
                  扩展名：{(selectedAdapter.supported_extensions || selectedAdapter.formats).join(', ')}
                  ；能力：{adapterCapabilityText(selectedAdapter)}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>

      <div className='space-y-4'>
        <Card className='sysml-card'>
          <CardHeader>
            <div className='flex items-center justify-between gap-3'>
              <div>
                <CardTitle>模型内容解析</CardTitle>
                <CardDescription>上传文件或粘贴 JSON、XMI、Notebook、MATLAB 标记内容</CardDescription>
              </div>
              <div className='flex gap-2'>
                <Button variant='outline' asChild>
                  <label>
                    <Upload className='size-4' />
                    上传并解析
                    <input
                      type='file'
                      className='hidden'
                      accept='.json,.xmi,.xml,.ipynb,.m,.mlx'
                      onChange={handleFileChange}
                    />
                  </label>
                </Button>
                <Button
                  variant='outline'
                  onClick={() => props.onParse()}
                  disabled={props.busy === 'mdk-parse'}
                >
                  {props.busy === 'mdk-parse' ? (
                    <Loader2 className='size-4 animate-spin' />
                  ) : (
                    <Search className='size-4' />
                  )}
                  重新解析
                </Button>
                <Button
                  variant='outline'
                  onClick={props.onCreateJob}
                  disabled={props.busy === 'mdk-job'}
                >
                  {props.busy === 'mdk-job' ? (
                    <Loader2 className='size-4 animate-spin' />
                  ) : (
                    <Archive className='size-4' />
                  )}
                  创建任务
                </Button>
                <Button
                  onClick={props.onApplyJob}
                  disabled={!canApply || props.busy === 'mdk-apply'}
                >
                  {props.busy === 'mdk-apply' ? (
                    <Loader2 className='size-4 animate-spin' />
                  ) : (
                    <Save className='size-4' />
                  )}
                  确认导入
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className='space-y-4'>
            <Textarea
              className='min-h-[340px] font-mono text-xs'
              value={props.content}
              onChange={(event) => props.setContent(event.target.value)}
            />
            {props.parseResult && (
              <div className='grid gap-3 sm:grid-cols-4'>
                <MdkMetric label='元素' value={props.parseResult.parsed_model.element_count} />
                <MdkMetric label='跳过' value={report?.skipped.length || 0} />
                <MdkMetric label='转换' value={report?.converted.length || 0} />
                <MdkMetric label='降级' value={report?.downgraded.length || 0} />
              </div>
            )}
          </CardContent>
        </Card>

        {props.importJob && (
          <Card className='sysml-card'>
            <CardHeader>
              <div className='flex items-center justify-between gap-3'>
                <div>
                  <CardTitle>导入任务</CardTitle>
                  <CardDescription>{props.importJob.id}</CardDescription>
                </div>
                <Badge variant={props.importJob.status === 'applied' ? 'secondary' : 'outline'}>
                  {props.importJob.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className='grid gap-3 text-sm sm:grid-cols-2'>
              <div>
                <span className='text-muted-foreground'>目标：</span>
                {props.importJob.project} / {props.importJob.branch}
              </div>
              <div>
                <span className='text-muted-foreground'>来源：</span>
                {props.importJob.adapter} / {props.importJob.filename || '-'}
              </div>
              <div>
                <span className='text-muted-foreground'>创建：</span>
                {props.importJob.created_by} / {props.importJob.created_at}
              </div>
              <div>
                <span className='text-muted-foreground'>应用：</span>
                {props.importJob.applied_at || '等待确认'}
              </div>
            </CardContent>
          </Card>
        )}

        <Card className='sysml-card'>
          <CardHeader>
            <div className='flex items-center justify-between gap-3'>
              <div>
                <CardTitle>映射报告</CardTitle>
                <CardDescription>
                  {props.parseResult
                    ? `${props.parseResult.parsed_model.adapter} / ${props.parseResult.parsed_model.type}`
                    : '解析后显示转换、跳过和降级详情'}
                </CardDescription>
              </div>
              {props.parseResult && (
                <Badge variant='secondary'>
                  imported {props.parseResult.mapping_report.imported}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {props.parseResult ? (
              <div className='grid gap-4 xl:grid-cols-2'>
                <MappingReportGroup
                  title='跳过'
                  items={props.parseResult.mapping_report.skipped}
                  empty='没有跳过的内容'
                />
                <MappingReportGroup
                  title='转换'
                  items={props.parseResult.mapping_report.converted}
                  empty='没有需要转换的内容'
                />
                <MappingReportGroup
                  title='降级'
                  items={props.parseResult.mapping_report.downgraded}
                  empty='没有降级内容'
                />
                <div className='rounded-md border p-3'>
                  <h3 className='mb-2 text-sm font-semibold'>警告</h3>
                  {props.parseResult.mapping_report.warnings.length ? (
                    <div className='space-y-2 text-sm'>
                      {props.parseResult.mapping_report.warnings.map((warning) => (
                        <div key={warning} className='rounded-md bg-muted p-2'>
                          {warning}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className='text-sm text-muted-foreground'>没有警告</p>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState title='等待解析' description='粘贴外部模型内容后点击解析' />
            )}
          </CardContent>
        </Card>

        {props.parseResult?.parsed_model.elements.length ? (
          <Card className='sysml-card'>
            <CardHeader>
              <CardTitle>解析出的元素</CardTitle>
              <CardDescription>
                {props.parseResult.parsed_model.elements.length} 个元素将导入当前分支
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className='h-[220px] rounded-md border'>
                <div className='divide-y'>
                  {props.parseResult.parsed_model.elements.map((element) => (
                    <div key={element.id} className='px-3 py-2 text-sm'>
                      <div className='flex items-center justify-between gap-2'>
                        <span className='font-mono font-semibold'>{element.id}</span>
                        <Badge variant='outline'>{labelType(element.type)}</Badge>
                      </div>
                      <p className='truncate text-muted-foreground'>
                        {element.name || '未命名元素'}
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className='grid gap-2'>
      <Label>{label}</Label>
      {children}
    </div>
  )
}

function CapabilityBadge({ enabled, label }: { enabled: boolean; label: string }) {
  return (
    <Badge variant={enabled ? 'secondary' : 'outline'} className='rounded-sm'>
      {label}
    </Badge>
  )
}

function MdkMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className='rounded-md border bg-muted/25 p-3'>
      <div className='text-xs text-muted-foreground'>{label}</div>
      <div className='mt-1 text-2xl font-semibold'>{value}</div>
    </div>
  )
}

function MappingReportGroup({
  title,
  items,
  empty,
}: {
  title: string
  items: Record<string, unknown>[]
  empty: string
}) {
  return (
    <div className='rounded-md border p-3'>
      <h3 className='mb-2 text-sm font-semibold'>{title}</h3>
      {items.length ? (
        <ScrollArea className='h-[180px]'>
          <div className='space-y-2 pr-3 text-xs'>
            {items.map((item, index) => (
              <pre
                key={`${title}-${index}`}
                className='overflow-x-auto rounded-md bg-muted p-2 font-mono'
              >
                {JSON.stringify(item, null, 2)}
              </pre>
            ))}
          </div>
        </ScrollArea>
      ) : (
        <p className='text-sm text-muted-foreground'>{empty}</p>
      )}
    </div>
  )
}

function adapterCapabilityText(adapter: MdkAdapter) {
  const labels = [
    adapter.can_read && '读',
    adapter.can_write && '写',
    adapter.can_validate && '校验',
    adapter.can_commit && '提交',
    adapter.can_rollback && '回滚',
  ].filter(Boolean)
  return labels.join('、') || '无'
}

function adapterFromFilename(filename: string, adapters: MdkAdapter[]) {
  const lowerName = filename.toLowerCase()
  return adapters.find((adapter) =>
    (adapter.supported_extensions || adapter.formats).some((extension) => {
      const normalized = extension.startsWith('.') ? extension : `.${extension}`
      return lowerName.endsWith(normalized.toLowerCase())
    })
  )
}

function tabFromHash(hash: string): WorkbenchTab {
  const value = hash.replace(/^#/, '')
  return workbenchTabs.includes(value as WorkbenchTab)
    ? (value as WorkbenchTab)
    : 'model'
}

function EmptyState({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className='flex min-h-[180px] flex-col items-center justify-center gap-2 p-8 text-center'>
      <Braces className='size-8 text-muted-foreground' />
      <div className='font-medium'>{title}</div>
      <p className='max-w-sm text-sm text-muted-foreground'>{description}</p>
    </div>
  )
}

function TraceBadge({ status }: { status: TraceabilityRow['status'] }) {
  const classes = {
    closed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    partial: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    open: 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300',
  }
  const labels = {
    closed: '闭环',
    partial: '部分',
    open: '未闭环',
  }
  return (
    <span className={cn('inline-flex rounded-md px-2 py-1 text-xs font-medium', classes[status])}>
      {labels[status]}
    </span>
  )
}

function formatRefs(refs: { id: string; name: string }[]) {
  if (!refs.length) return <span className='text-muted-foreground'>-</span>
  return (
    <div className='space-y-1'>
      {refs.map((ref) => (
        <div key={ref.id}>
          <span className='font-mono font-medium'>{ref.id}</span>{' '}
          <span className='text-muted-foreground'>{ref.name}</span>
        </div>
      ))}
    </div>
  )
}

function labelType(type: string) {
  return displayTypeNames[type] || typeNames[type] || type
}

function labelRelation(type: string) {
  return displayRelationNames[type] || relationNames[type] || type
}

function countBy<T>(items: T[], getKey: (item: T) => string) {
  return items.reduce<Record<string, number>>((acc, item) => {
    const key = getKey(item)
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
}

function includedElementIds(attributesText: string) {
  const attributes = parseJsonSafe<Record<string, unknown>>(attributesText, {})
  const values = Array.isArray(attributes.included_elements)
    ? attributes.included_elements
    : []
  return new Set(values.map(String))
}

function stringList(value: unknown) {
  if (Array.isArray(value)) return value.map(String).filter(Boolean)
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }
  return []
}

function elementsTypes(elements: SysmlElement[]) {
  return Array.from(new Set(elements.map((element) => element.type)))
    .filter((type) => type !== 'View')
    .sort()
}

function parseJson<T>(value: string, label: string, fallback: T): T {
  try {
    return (value.trim() ? JSON.parse(value) : fallback) as T
  } catch {
    throw new Error(`${label} 格式不正确`)
  }
}

function parseJsonSafe<T>(value: string, fallback: T): T {
  try {
    return (value.trim() ? JSON.parse(value) : fallback) as T
  } catch {
    return fallback
  }
}

function notifyError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error)
  toast.error(message)
}

function downloadText(filename: string, text: string, type: string) {
  const blob = new Blob([text], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function downloadBase64(filename: string, base64Text: string, type: string) {
  const binary = atob(base64Text)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  const blob = new Blob([bytes], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function shortLabel(value: string, maxLength: number) {
  if (value.length <= maxLength) return value
  return `${value.slice(0, Math.max(0, maxLength - 1))}…`
}

function MarkdownMessage({
  content,
  compact,
}: {
  content: string
  compact?: boolean
}) {
  const blocks = parseMarkdownBlocks(content)
  return (
    <div className={cn('space-y-3 leading-6', compact ? 'text-sm' : 'text-[15px]')}>
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          const HeadingTag = block.level === 2 ? 'h3' : 'h4'
          return (
            <HeadingTag
              key={`${block.type}-${index}`}
              className={cn(
                'font-semibold tracking-normal text-foreground',
                block.level === 2 ? 'text-base' : 'text-sm'
              )}
            >
              {renderInlineMarkdown(block.text)}
            </HeadingTag>
          )
        }
        if (block.type === 'list') {
          return (
            <ul key={`${block.type}-${index}`} className='space-y-1.5'>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`} className='flex gap-2'>
                  <CheckCircle2 className='mt-1 size-3.5 shrink-0 text-emerald-600' />
                  <span>{renderInlineMarkdown(item)}</span>
                </li>
              ))}
            </ul>
          )
        }
        if (block.type === 'table') {
          return (
            <div
              key={`${block.type}-${index}`}
              className='overflow-x-auto rounded-md border'
            >
              <Table>
                <TableHeader>
                  <TableRow>
                    {block.headers.map((header, headerIndex) => (
                      <TableHead key={`${header}-${headerIndex}`}>
                        {renderInlineMarkdown(header)}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {block.rows.map((row, rowIndex) => (
                    <TableRow key={`row-${rowIndex}`}>
                      {block.headers.map((_, cellIndex) => (
                        <TableCell key={`cell-${rowIndex}-${cellIndex}`}>
                          {renderInlineMarkdown(row[cellIndex] || '')}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )
        }
        return (
          <p key={`${block.type}-${index}`} className='text-muted-foreground'>
            {renderInlineMarkdown(block.text)}
          </p>
        )
      })}
    </div>
  )
}

type MarkdownBlock =
  | { type: 'heading'; level: number; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] }

function parseMarkdownBlocks(content: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = []
  let paragraph: string[] = []
  let listItems: string[] = []
  let tableRows: string[][] = []

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: 'paragraph', text: paragraph.join(' ') })
      paragraph = []
    }
  }
  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: 'list', items: listItems })
      listItems = []
    }
  }
  const flushTable = () => {
    if (tableRows.length >= 2) {
      const [headers, separator, ...rows] = tableRows
      if (isMarkdownTableSeparator(separator)) {
        blocks.push({ type: 'table', headers, rows })
      } else {
        paragraph.push(...tableRows.map((row) => `| ${row.join(' | ')} |`))
      }
    } else if (tableRows.length) {
      paragraph.push(...tableRows.map((row) => `| ${row.join(' | ')} |`))
    }
    tableRows = []
  }

  content.split(/\r?\n/).forEach((rawLine) => {
    const line = rawLine.trim()
    if (!line) {
      flushTable()
      flushParagraph()
      flushList()
      return
    }
    if (isMarkdownTableRow(line)) {
      flushParagraph()
      flushList()
      tableRows.push(splitMarkdownTableRow(line))
      return
    }
    flushTable()
    const heading = line.match(/^(#{2,4})\s+(.+)$/)
    if (heading) {
      flushParagraph()
      flushList()
      blocks.push({
        type: 'heading',
        level: heading[1].length,
        text: heading[2].trim(),
      })
      return
    }
    const list = line.match(/^[-*]\s+(.+)$/)
    if (list) {
      flushParagraph()
      listItems.push(list[1].trim())
      return
    }
    flushList()
    paragraph.push(line)
  })
  flushTable()
  flushParagraph()
  flushList()
  return blocks
}

function isMarkdownTableRow(line: string) {
  return line.startsWith('|') && line.endsWith('|') && line.includes('|')
}

function splitMarkdownTableRow(line: string) {
  return line
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function isMarkdownTableSeparator(row: string[]) {
  return row.length > 0 && row.every((cell) => /^:?-{3,}:?$/.test(cell.trim()))
}

function renderInlineMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={index}
          className='rounded bg-muted px-1 py-0.5 font-mono text-[0.9em]'
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    return <span key={index}>{part}</span>
  })
}
