import { useEffect, useMemo, useRef, useState } from 'react'
import type * as Monaco from 'monaco-editor'
import 'monaco-editor/min/vs/editor/editor.main.css'
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api.js'
import { AlertCircle, CheckCircle2, Sparkles } from 'lucide-react'
import type { SysmlElement, ValidationPayload } from '@/lib/sysml-api'
import { cn } from '@/lib/utils'

declare global {
  interface Window {
    MonacoEnvironment?: {
      getWorker(workerId: string, label: string): Worker
    }
  }
}

const languageId = 'docgen-template'
const modelUri = monaco.Uri.parse('inmemory://sysml-docgen/template.docgen')

window.MonacoEnvironment = {
  getWorker() {
    return new EditorWorker()
  },
}

type TemplateMarker = {
  message: string
  severity: Monaco.MarkerSeverity
  startLineNumber: number
  startColumn: number
  endLineNumber: number
  endColumn: number
}

type CompletionContext = {
  elements: SysmlElement[]
  validation: ValidationPayload | null
}

type RegisteredLanguage = {
  completion: Monaco.IDisposable
  hover: Monaco.IDisposable
}

let languageRegistered = false
let providers: RegisteredLanguage | null = null
let completionContext: CompletionContext = {
  elements: [],
  validation: null,
}

const templateTokens = [
  {
    name: 'element',
    syntax: '{{element:REQ-001.name}}',
    detail: 'Resolve a field from a model element',
  },
  {
    name: 'model',
    syntax: '{{model:summary}}',
    detail: 'Render the current model summary',
  },
  {
    name: 'table',
    syntax: '{{table:requirements}}',
    detail: 'Render a typed Markdown table',
  },
  {
    name: 'trace',
    syntax: '{{trace:matrix}}',
    detail: 'Render the traceability matrix',
  },
  {
    name: 'validation',
    syntax: '{{validation:issues}}',
    detail: 'Render repository validation issues',
  },
]

const tableNames = [
  'requirements',
  'blocks',
  'interfaces',
  'constraints',
  'tests',
  'states',
]

const modelNames = ['summary']
const traceNames = ['matrix']
const validationNames = ['issues']
const baseElementFields = ['id', 'name', 'type', 'stereotype', 'owner', 'description']

export function DocgenTemplateEditor({
  value,
  onChange,
  elements,
  validation,
}: {
  value: string
  onChange: (value: string) => void
  elements: SysmlElement[]
  validation: ValidationPayload | null
}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)
  const modelRef = useRef<Monaco.editor.ITextModel | null>(null)
  const onChangeRef = useRef(onChange)
  const markerContextRef = useRef({ elements, validation })
  const [markerCount, setMarkerCount] = useState(0)

  const stats = useMemo(() => {
    return {
      elements: elements.length,
      issues:
        (validation?.summary.errors || 0) + (validation?.summary.warnings || 0),
    }
  }, [elements.length, validation])

  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    completionContext = { elements, validation }
    markerContextRef.current = { elements, validation }
  }, [elements, validation])

  useEffect(() => {
    registerDocgenLanguage()
  }, [])

  useEffect(() => {
    if (!containerRef.current || editorRef.current) return

    const model =
      monaco.editor.getModel(modelUri) ||
      monaco.editor.createModel(value, languageId, modelUri)
    modelRef.current = model

    const editor = monaco.editor.create(containerRef.current, {
      model,
      automaticLayout: true,
      bracketPairColorization: { enabled: true },
      cursorBlinking: 'smooth',
      fontFamily:
        '"Cascadia Code", "JetBrains Mono", "Fira Code", Consolas, monospace',
      fontLigatures: true,
      fontSize: 13,
      glyphMargin: true,
      lineNumbersMinChars: 3,
      minimap: { enabled: false },
      padding: { top: 12, bottom: 12 },
      quickSuggestions: {
        other: true,
        comments: false,
        strings: true,
      },
      renderLineHighlight: 'gutter',
      scrollBeyondLastLine: false,
      smoothScrolling: true,
      suggest: {
        preview: true,
        showInlineDetails: true,
        snippetsPreventQuickSuggestions: false,
      },
      theme: getMonacoTheme(),
      wordWrap: 'on',
    })
    editorRef.current = editor

    const contentSubscription = model.onDidChangeContent(() => {
      const nextValue = model.getValue()
      const context = markerContextRef.current
      updateTemplateMarkers(model, context.elements, context.validation)
      onChangeRef.current(nextValue)
    })

    const markerSubscription = monaco.editor.onDidChangeMarkers((uris) => {
      if (!uris.some((uri) => uri.toString() === model.uri.toString())) return
      setMarkerCount(monaco.editor.getModelMarkers({ resource: model.uri }).length)
    })

    const resizeObserver = new ResizeObserver(() => {
      editor.layout()
    })
    resizeObserver.observe(containerRef.current)

    updateTemplateMarkers(model, elements, validation)

    return () => {
      resizeObserver.disconnect()
      markerSubscription.dispose()
      contentSubscription.dispose()
      editor.dispose()
      editorRef.current = null
    }
  }, [])

  useEffect(() => {
    const model = modelRef.current
    if (!model || model.getValue() === value) return
    model.pushEditOperations(
      [],
      [
        {
          range: model.getFullModelRange(),
          text: value,
        },
      ],
      () => null
    )
  }, [value])

  useEffect(() => {
    const model = modelRef.current
    if (!model) return
    updateTemplateMarkers(model, elements, validation)
  }, [elements, validation])

  useEffect(() => {
    const applyTheme = () => monaco.editor.setTheme(getMonacoTheme())
    applyTheme()

    const observer = new MutationObserver(applyTheme)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })
    return () => observer.disconnect()
  }, [])

  return (
    <div className='overflow-hidden rounded-md border bg-background'>
      <div
        ref={containerRef}
        className='h-[420px] min-h-[360px] w-full bg-background'
      />
      <div className='flex flex-wrap items-center justify-between gap-2 border-t bg-muted/35 px-3 py-2 text-xs text-muted-foreground'>
        <div className='flex flex-wrap items-center gap-3'>
          <span className='inline-flex items-center gap-1'>
            <Sparkles className='size-3.5' />
            DocGen Template
          </span>
          <span>{stats.elements} elements indexed</span>
          <span>{stats.issues} model issues</span>
        </div>
        <span
          className={cn(
            'inline-flex items-center gap-1 font-medium',
            markerCount ? 'text-destructive' : 'text-emerald-600'
          )}
        >
          {markerCount ? (
            <AlertCircle className='size-3.5' />
          ) : (
            <CheckCircle2 className='size-3.5' />
          )}
          {markerCount ? `${markerCount} editor issues` : 'No editor issues'}
        </span>
      </div>
    </div>
  )
}

function registerDocgenLanguage() {
  if (!languageRegistered) {
    monaco.languages.register({
      id: languageId,
      extensions: ['.docgen'],
      aliases: ['DocGen Template', 'docgen'],
    })

    monaco.languages.setLanguageConfiguration(languageId, {
      brackets: [
        ['{{', '}}'],
        ['[', ']'],
        ['(', ')'],
        ['{', '}'],
      ],
      autoClosingPairs: [
        { open: '{{', close: '}}' },
        { open: '{', close: '}' },
        { open: '[', close: ']' },
        { open: '(', close: ')' },
        { open: '"', close: '"' },
        { open: "'", close: "'" },
      ],
      surroundingPairs: [
        { open: '{{', close: '}}' },
        { open: '"', close: '"' },
        { open: "'", close: "'" },
        { open: '`', close: '`' },
      ],
    })

    monaco.languages.setMonarchTokensProvider(languageId, {
      defaultToken: '',
      tokenPostfix: '.docgen',
      brackets: [
        { open: '{{', close: '}}', token: 'delimiter.curly' },
        { open: '{', close: '}', token: 'delimiter.bracket' },
        { open: '[', close: ']', token: 'delimiter.square' },
        { open: '(', close: ')', token: 'delimiter.parenthesis' },
      ],
      tokenizer: {
        root: [
          [/```json\b/, 'string.delimiter', '@jsonBlock'],
          [/```[\w-]*/, 'string.delimiter', '@codeBlock'],
          [/{{\s*(element|model|table|trace|validation)\s*:/, 'keyword', '@token'],
          [/{{/, 'delimiter.curly', '@token'],
          [/^#{1,6}\s.+$/, 'type.identifier'],
          [/\*\*[^*]+\*\*/, 'strong'],
          [/`[^`]+`/, 'string'],
        ],
        token: [
          [/}}/, 'delimiter.curly', '@pop'],
          [/[A-Z][A-Z0-9_-]+(?=\.)/, 'type.identifier'],
          [/\b(name|id|type|owner|description|attributes|relations)\b/, 'attribute.name'],
          [/[.:]/, 'delimiter'],
          [/[a-zA-Z_][\w-]*/, 'identifier'],
        ],
        jsonBlock: [
          [/```/, 'string.delimiter', '@pop'],
          [/"(?:[^"\\]|\\.)*"(?=\s*:)/, 'attribute.name'],
          [/"(?:[^"\\]|\\.)*"/, 'string'],
          [/\b(true|false|null)\b/, 'constant'],
          [/-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/, 'number'],
          [/[{}[\],:]/, 'delimiter'],
        ],
        codeBlock: [[/```/, 'string.delimiter', '@pop']],
      },
    })

    monaco.editor.defineTheme('docgen-template-light', {
      base: 'vs',
      inherit: true,
      rules: [
        { token: 'keyword', foreground: '0f766e', fontStyle: 'bold' },
        { token: 'type.identifier', foreground: '1d4ed8' },
        { token: 'attribute.name', foreground: '9333ea' },
        { token: 'string', foreground: '166534' },
        { token: 'number', foreground: 'c2410c' },
        { token: 'delimiter.curly', foreground: 'be123c', fontStyle: 'bold' },
      ],
      colors: {
        'editor.background': '#ffffff',
        'editor.foreground': '#0f172a',
        'editorLineNumber.foreground': '#94a3b8',
        'editorLineNumber.activeForeground': '#334155',
        'editor.selectionBackground': '#bfdbfe',
        'editorSuggestWidget.background': '#ffffff',
        'editorSuggestWidget.border': '#e2e8f0',
      },
    })

    monaco.editor.defineTheme('docgen-template-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'keyword', foreground: '5eead4', fontStyle: 'bold' },
        { token: 'type.identifier', foreground: '93c5fd' },
        { token: 'attribute.name', foreground: 'c4b5fd' },
        { token: 'string', foreground: '86efac' },
        { token: 'number', foreground: 'fdba74' },
        { token: 'delimiter.curly', foreground: 'fda4af', fontStyle: 'bold' },
      ],
      colors: {
        'editor.background': '#020617',
        'editor.foreground': '#e2e8f0',
        'editorLineNumber.foreground': '#64748b',
        'editorLineNumber.activeForeground': '#cbd5e1',
        'editor.selectionBackground': '#1e40af',
        'editorSuggestWidget.background': '#0f172a',
        'editorSuggestWidget.border': '#334155',
      },
    })

    languageRegistered = true
  }

  if (providers) return

  providers = {
    completion: monaco.languages.registerCompletionItemProvider(languageId, {
      triggerCharacters: ['{', ':', '.', '"'],
      provideCompletionItems(model, position) {
        return {
          suggestions: buildCompletionItems(model, position, completionContext),
        }
      },
    }),
    hover: monaco.languages.registerHoverProvider(languageId, {
      provideHover(model, position) {
        return buildHover(model, position, completionContext)
      },
    }),
  }
}

function buildCompletionItems(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  context: CompletionContext
): Monaco.languages.CompletionItem[] {
  const word = model.getWordUntilPosition(position)
  const range = {
    startLineNumber: position.lineNumber,
    endLineNumber: position.lineNumber,
    startColumn: word.startColumn,
    endColumn: word.endColumn,
  }
  const prefix = model
    .getValueInRange({
      startLineNumber: position.lineNumber,
      startColumn: 1,
      endLineNumber: position.lineNumber,
      endColumn: position.column,
    })
    .slice(-160)

  const elementMatch = prefix.match(/{{\s*element\s*:\s*([A-Z0-9_-]*)$/i)
  if (elementMatch) {
    const elementRange = completionRange(position, elementMatch[1].length)
    return context.elements.map((element) => ({
      label: element.id,
      kind: monaco.languages.CompletionItemKind.Reference,
      detail: `${element.type} / ${element.name}`,
      documentation: element.description || element.owner || 'SysML element',
      insertText: `${element.id}.name}}`,
      range: elementRange,
    }))
  }

  const fieldMatch = prefix.match(/{{\s*element\s*:\s*([A-Z0-9_-]+)\.([\w.]*)$/i)
  if (fieldMatch) {
    const element = context.elements.find((item) => item.id === fieldMatch[1])
    const fieldRange = completionRange(position, fieldMatch[2].length)
    return elementFieldPaths(element).map((field) => ({
      label: field,
      kind: field.includes('.')
        ? monaco.languages.CompletionItemKind.Property
        : monaco.languages.CompletionItemKind.Field,
      detail: `{{element:${fieldMatch[1]}.${field}}}`,
      insertText: `${field}}}`,
      range: fieldRange,
    }))
  }

  const tokenMatch = prefix.match(/{{\s*(table|model|trace|validation)\s*:\s*([\w-]*)$/i)
  if (tokenMatch) {
    const valueRange = completionRange(position, tokenMatch[2].length)
    return tokenValues(tokenMatch[1]).map((item) => ({
      label: item,
      kind: monaco.languages.CompletionItemKind.Value,
      detail: `{{${tokenMatch[1]}:${item}}}`,
      insertText: `${item}}}`,
      range: valueRange,
    }))
  }

  return templateTokens.map((token) => ({
    label: token.syntax,
    kind: monaco.languages.CompletionItemKind.Snippet,
    detail: token.detail,
    insertText: token.syntax,
    range,
  }))
}

function completionRange(position: Monaco.Position, replaceLength: number) {
  return {
    startLineNumber: position.lineNumber,
    endLineNumber: position.lineNumber,
    startColumn: Math.max(1, position.column - replaceLength),
    endColumn: position.column,
  }
}

function buildHover(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  context: CompletionContext
): Monaco.languages.ProviderResult<Monaco.languages.Hover> {
  const tokenRange = findTokenRangeAt(model, position)
  if (!tokenRange) return null

  const tokenText = model.getValueInRange(tokenRange)
  const parsed = parseTemplateToken(tokenText)
  if (!parsed) return null

  if (parsed.kind === 'element') {
    const [elementId, ...pathParts] = parsed.expression.split('.')
    const element = context.elements.find((item) => item.id === elementId)
    const fieldPath = pathParts.join('.')

    return {
      range: tokenRange,
      contents: [
        { value: '**DocGen element placeholder**' },
        {
          value: element
            ? `${element.id} / ${element.type} / ${element.name}`
            : `Unresolved element: \`${elementId || 'missing'}\``,
        },
        { value: fieldPath ? `Field: \`${fieldPath}\`` : 'Field path is missing.' },
      ],
    }
  }

  return {
    range: tokenRange,
    contents: [
      { value: `**DocGen ${parsed.kind} placeholder**` },
      { value: `Expression: \`${parsed.expression || 'missing'}\`` },
    ],
  }
}

function updateTemplateMarkers(
  model: Monaco.editor.ITextModel,
  elements: SysmlElement[],
  validation: ValidationPayload | null
) {
  const text = model.getValue()
  const markers = [
    ...validateTemplateTokens(model, text, elements),
    ...validateJsonBlocks(model, text),
    ...validationSummaryMarkers(model, text, validation),
  ]
  monaco.editor.setModelMarkers(model, languageId, markers)
}

function validateTemplateTokens(
  model: Monaco.editor.ITextModel,
  text: string,
  elements: SysmlElement[]
): Monaco.editor.IMarkerData[] {
  const markers: TemplateMarker[] = []
  const tokenPattern = /{{([\s\S]*?)(}}|$)/g
  const elementMap = new Map(elements.map((element) => [element.id, element]))
  let match: RegExpExecArray | null

  while ((match = tokenPattern.exec(text))) {
    const tokenStart = match.index
    const tokenEnd = match.index + match[0].length
    const position = model.getPositionAt(tokenStart)
    const endPosition = model.getPositionAt(tokenEnd)
    const tokenText = match[0]

    if (!tokenText.endsWith('}}')) {
      markers.push({
        severity: monaco.MarkerSeverity.Error,
        message: 'DocGen placeholder is missing closing braces: }}',
        startLineNumber: position.lineNumber,
        startColumn: position.column,
        endLineNumber: endPosition.lineNumber,
        endColumn: Math.max(endPosition.column, position.column + 2),
      })
      break
    }

    const parsed = parseTemplateToken(tokenText)
    if (!parsed) {
      markers.push({
        severity: monaco.MarkerSeverity.Error,
        message:
          'Unknown DocGen placeholder. Use element, model, table, trace, or validation.',
        startLineNumber: position.lineNumber,
        startColumn: position.column,
        endLineNumber: endPosition.lineNumber,
        endColumn: endPosition.column,
      })
      continue
    }

    if (parsed.kind === 'element') {
      validateElementToken(parsed.expression, elementMap, markers, position, endPosition)
      continue
    }

    const allowed = tokenValues(parsed.kind)
    if (!parsed.expression || !allowed.includes(parsed.expression)) {
      markers.push({
        severity: monaco.MarkerSeverity.Warning,
        message: `Expected ${parsed.kind} expression: ${allowed.join(', ')}.`,
        startLineNumber: position.lineNumber,
        startColumn: position.column,
        endLineNumber: endPosition.lineNumber,
        endColumn: endPosition.column,
      })
    }
  }

  return markers
}

function validateElementToken(
  expression: string,
  elementMap: Map<string, SysmlElement>,
  markers: TemplateMarker[],
  start: Monaco.IPosition,
  end: Monaco.IPosition
) {
  const [elementId, ...pathParts] = expression.split('.')
  const path = pathParts.join('.')
  const element = elementMap.get(elementId)

  if (!elementId || !path) {
    markers.push({
      severity: monaco.MarkerSeverity.Warning,
      message: 'Element placeholders should look like {{element:REQ-001.name}}.',
      startLineNumber: start.lineNumber,
      startColumn: start.column,
      endLineNumber: end.lineNumber,
      endColumn: end.column,
    })
    return
  }

  if (!element) {
    markers.push({
      severity: monaco.MarkerSeverity.Error,
      message: `Element ${elementId} does not exist in the current branch.`,
      startLineNumber: start.lineNumber,
      startColumn: start.column,
      endLineNumber: end.lineNumber,
      endColumn: end.column,
    })
    return
  }

  if (!hasPath(element, path)) {
    markers.push({
      severity: monaco.MarkerSeverity.Warning,
      message: `Field path "${path}" is not available on ${elementId}.`,
      startLineNumber: start.lineNumber,
      startColumn: start.column,
      endLineNumber: end.lineNumber,
      endColumn: end.column,
    })
  }
}

function validateJsonBlocks(
  model: Monaco.editor.ITextModel,
  text: string
): Monaco.editor.IMarkerData[] {
  const markers: TemplateMarker[] = []
  const jsonBlockPattern = /```json\s*\r?\n([\s\S]*?)(?:\r?\n```|$)/gi
  let match: RegExpExecArray | null

  while ((match = jsonBlockPattern.exec(text))) {
    const jsonText = match[1]
    const jsonStart = match.index + match[0].indexOf(jsonText)
    const jsonEnd = jsonStart + jsonText.length

    if (!jsonText.trim()) continue

    try {
      JSON.parse(jsonText)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Invalid JSON.'
      const offsetMatch = message.match(/position (\d+)/i)
      const errorOffset = offsetMatch ? Number(offsetMatch[1]) : 0
      const start = model.getPositionAt(
        Math.min(jsonStart + errorOffset, Math.max(jsonStart, jsonEnd - 1))
      )

      markers.push({
        severity: monaco.MarkerSeverity.Error,
        message: `Invalid JSON block: ${message}`,
        startLineNumber: start.lineNumber,
        startColumn: start.column,
        endLineNumber: start.lineNumber,
        endColumn: start.column + 1,
      })
    }
  }

  return markers
}

function validationSummaryMarkers(
  model: Monaco.editor.ITextModel,
  text: string,
  validation: ValidationPayload | null
): Monaco.editor.IMarkerData[] {
  if (!validation?.summary.errors) return []

  const index = text.indexOf('{{validation:issues}}')
  if (index < 0) return []

  const start = model.getPositionAt(index)
  const end = model.getPositionAt(index + '{{validation:issues}}'.length)

  return [
    {
      severity: monaco.MarkerSeverity.Info,
      message: `Current model has ${validation.summary.errors} validation error(s). Generated output will include them.`,
      startLineNumber: start.lineNumber,
      startColumn: start.column,
      endLineNumber: end.lineNumber,
      endColumn: end.column,
    },
  ]
}

function parseTemplateToken(tokenText: string) {
  const match = tokenText.match(
    /^{{\s*(element|model|table|trace|validation)\s*:\s*([\s\S]*?)\s*}}$/i
  )
  if (!match) return null

  return {
    kind: match[1].toLowerCase(),
    expression: match[2].trim(),
  }
}

function findTokenRangeAt(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position
): Monaco.IRange | null {
  const offset = model.getOffsetAt(position)
  const text = model.getValue()
  const start = text.lastIndexOf('{{', offset)
  const end = text.indexOf('}}', offset)

  if (start < 0 || end < 0 || start > offset) return null

  return {
    startLineNumber: model.getPositionAt(start).lineNumber,
    startColumn: model.getPositionAt(start).column,
    endLineNumber: model.getPositionAt(end + 2).lineNumber,
    endColumn: model.getPositionAt(end + 2).column,
  }
}

function elementFieldPaths(element: SysmlElement | undefined) {
  if (!element) return baseElementFields

  const attributeFields = Object.keys(element.attributes || {}).map(
    (key) => `attributes.${key}`
  )
  const relationFields = element.relations?.length
    ? ['relations', 'relations.0.type', 'relations.0.target']
    : ['relations']

  return [...baseElementFields, ...attributeFields, ...relationFields]
}

function hasPath(element: SysmlElement, path: string) {
  return path.split('.').every((part, index, parts) => {
    const value = getPath(element, parts.slice(0, index + 1).join('.'))
    return value !== undefined && part !== ''
  })
}

function getPath(source: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((current, part) => {
    if (current == null) return undefined
    if (Array.isArray(current)) return current[Number(part)]
    if (typeof current === 'object') {
      return (current as Record<string, unknown>)[part]
    }
    return undefined
  }, source)
}

function tokenValues(kind: string) {
  if (kind === 'table') return tableNames
  if (kind === 'model') return modelNames
  if (kind === 'trace') return traceNames
  if (kind === 'validation') return validationNames
  return []
}

function getMonacoTheme() {
  return document.documentElement.classList.contains('dark')
    ? 'docgen-template-dark'
    : 'docgen-template-light'
}
