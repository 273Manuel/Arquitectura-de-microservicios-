import { useCallback, useEffect, useRef, useState } from 'react'

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE'
type ServiceId = 'productos' | 'clientes' | 'pedidos'
type TopTab = 'Dashboard' | 'Proxy' | 'Repeater' | 'Logs'

type Service = {
  id: ServiceId
  host: string
  port: number
  online: boolean
  registros: number
}

type EventItem = {
  id: string
  time: string
  method: Method
  path: string
  result: string
  duration: string
}

const serviceDefinitions: Record<ServiceId, { host: string; port: number }> = {
  productos: { host: 'productos.local', port: 8001 },
  clientes: { host: 'clientes.local', port: 8002 },
  pedidos: { host: 'pedidos.local', port: 8003 },
}

const initialServices: Service[] = (Object.keys(serviceDefinitions) as ServiceId[]).map((id) => ({
  id,
  ...serviceDefinitions[id],
  online: false,
  registros: 0,
}))

const requestBodies: Record<ServiceId, string> = {
  productos: `{
  "nombre": "Teclado mecánico",
  "sku": "KB-2025-02",
  "precio": 129.90,
  "stock": 24,
  "activo": true
}`,
  clientes: `{
  "nombre": "Ana García",
  "email": "ana.nueva@example.com",
  "plan": "student",
  "activo": true
}`,
  pedidos: `{
  "clienteId": 42,
  "productoId": 18,
  "cantidad": 2,
  "confirmado": false
}`,
}

const initialResponse = `{
  "message": "Envía una solicitud para ver la respuesta real del microservicio"
}`

const statusLabels: Record<number, string> = {
  200: 'OK',
  201: 'CREATED',
  204: 'NO CONTENT',
  400: 'BAD REQUEST',
  404: 'NOT FOUND',
  409: 'CONFLICT',
  422: 'VALIDATION ERROR',
  500: 'SERVER ERROR',
  502: 'BAD GATEWAY',
  503: 'SERVICE UNAVAILABLE',
}

function ToolIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M20 11a8 8 0 1 0-2.34 5.66" />
      <path d="M20 4v7h-7" />
    </svg>
  )
}

function SyntaxLine({ line }: { line: string }) {
  const tokens = line.split(/("(?:\\.|[^"])*")|(\b(?:true|false|null)\b)|(-?\d+(?:\.\d+)?)/g)
  return (
    <>
      {tokens.filter((token) => token !== undefined && token !== '').map((token, index) => {
        if (token.startsWith('"')) {
          const isKey = line.slice(line.indexOf(token) + token.length).trimStart().startsWith(':')
          return <span className={isKey ? 'json-key' : 'json-string'} key={`${index}-${token}`}>{token}</span>
        }
        if (/^(true|false|null)$/.test(token)) return <span className="json-boolean" key={`${index}-${token}`}>{token}</span>
        if (/^-?\d+(?:\.\d+)?$/.test(token)) return <span className="json-number" key={`${index}-${token}`}>{token}</span>
        return <span key={`${index}-${token}`}>{token}</span>
      })}
    </>
  )
}

function JsonCode({ value, editable = false, onChange }: { value: string; editable?: boolean; onChange?: (value: string) => void }) {
  return (
    <div className={`json-code ${editable ? 'json-editable' : ''}`}>
      <div className="line-numbers" aria-hidden="true">
        {value.split('\n').map((_, index) => <span key={index}>{index + 1}</span>)}
      </div>
      <pre
        contentEditable={editable}
        suppressContentEditableWarning
        spellCheck={false}
        onBlur={(event) => onChange?.(event.currentTarget.innerText)}
        aria-label={editable ? 'Editor JSON del request' : 'Respuesta JSON'}
      >
        {value.split('\n').map((line, index) => (
          <span className="json-line" key={`${index}-${line}`}><SyntaxLine line={line} />{'\n'}</span>
        ))}
      </pre>
    </div>
  )
}

function resultClass(result: string) {
  if (result.startsWith('2')) return 'text-success'
  if (result.startsWith('4')) return 'text-warning'
  return 'text-error'
}

function eventTime() {
  const now = new Date()
  return `${now.toLocaleTimeString('es-CO', { hour12: false })}.${String(now.getMilliseconds()).padStart(3, '0')}`
}

function App() {
  const [services, setServices] = useState(initialServices)
  const [selectedId, setSelectedId] = useState<ServiceId>('productos')
  const [topTab, setTopTab] = useState<TopTab>('Repeater')
  const [requestTab, setRequestTab] = useState('Body')
  const [responseTab, setResponseTab] = useState('Pretty')
  const [method, setMethod] = useState<Method>('POST')
  const [url, setUrl] = useState('/api/productos')
  const [bodies, setBodies] = useState(requestBodies)
  const [response, setResponse] = useState(initialResponse)
  const [result, setResult] = useState('READY')
  const [responseTime, setResponseTime] = useState('0ms')
  const [events, setEvents] = useState<EventItem[]>([])
  const [drawerOpen, setDrawerOpen] = useState(true)
  const [split, setSplit] = useState(50)
  const [sending, setSending] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [changingService, setChangingService] = useState(false)
  const workspaceRef = useRef<HTMLDivElement>(null)
  const nextId = useRef(1)

  const selectedService = services.find((service) => service.id === selectedId) ?? services[0]

  const actualizarEstados = useCallback(async () => {
    const estados = await Promise.all((Object.keys(serviceDefinitions) as ServiceId[]).map(async (id) => {
      try {
        const respuesta = await fetch(`/api/${id}/salud`, { cache: 'no-store', signal: AbortSignal.timeout(4000) })
        const datos = await respuesta.json()
        return { id, online: respuesta.ok && datos.estado === 'online', registros: Number(datos.registros ?? 0) }
      } catch {
        return { id, online: false, registros: 0 }
      }
    }))
    setServices((current) => current.map((service) => {
      const estado = estados.find((item) => item.id === service.id)
      return estado ? { ...service, ...estado } : service
    }))
  }, [])

  useEffect(() => {
    void actualizarEstados()
    const interval = window.setInterval(() => void actualizarEstados(), 5000)
    return () => window.clearInterval(interval)
  }, [actualizarEstados])

  function selectService(id: ServiceId) {
    setSelectedId(id)
    setUrl(`/api/${id}`)
    setResult('READY')
    setTopTab('Repeater')
  }

  async function restart() {
    setRestarting(true)
    try {
      await Promise.all((Object.keys(serviceDefinitions) as ServiceId[]).map((id) =>
        fetch(`/api/${id}/control/reiniciar`, { method: 'POST' }),
      ))
      setSelectedId('productos')
      setMethod('POST')
      setUrl('/api/productos')
      setBodies(requestBodies)
      setResponse(initialResponse)
      setResult('READY')
      setResponseTime('0ms')
      setEvents([])
      await actualizarEstados()
    } finally {
      setRestarting(false)
    }
  }

  async function toggleSelected() {
    setChangingService(true)
    try {
      await fetch(`/api/${selectedId}/control/estado`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ online: !selectedService.online }),
      })
      await actualizarEstados()
    } finally {
      setChangingService(false)
    }
  }

  async function sendRequest() {
    if (sending) return
    const destination = url.trim()
    if (!destination) {
      setResult('400 BAD REQUEST')
      setResponse('{\n  "detail": "La URL es obligatoria"\n}')
      return
    }
    setSending(true)
    const started = performance.now()
    const serviceInUrl = (Object.keys(serviceDefinitions) as ServiceId[]).find((id) => destination.includes(`/api/${id}`)) ?? selectedId
    let nextResult = 'NETWORK ERROR'
    let path = destination
    try {
      path = new URL(destination, window.location.origin).pathname
      const options: RequestInit = { method }
      if (method === 'POST' || method === 'PUT') {
        options.headers = { 'Content-Type': 'application/json' }
        options.body = bodies[serviceInUrl]
      }
      const apiResponse = await fetch(destination, options)
      const elapsed = Math.round(performance.now() - started)
      const raw = await apiResponse.text()
      nextResult = `${apiResponse.status} ${statusLabels[apiResponse.status] ?? apiResponse.statusText}`.trim()
      setResult(nextResult)
      setResponseTime(`${elapsed}ms`)
      if (!raw) {
        setResponse(`{\n  "message": "La operación terminó con estado ${apiResponse.status} y sin contenido"\n}`)
      } else {
        try {
          setResponse(JSON.stringify(JSON.parse(raw), null, 2))
        } catch {
          setResponse(raw)
        }
      }
      setEvents((current) => [{
        id: `event-${Date.now()}-${nextId.current}`,
        time: eventTime(),
        method,
        path,
        result: nextResult,
        duration: `${elapsed}ms`,
      }, ...current])
    } catch (error) {
      const elapsed = Math.round(performance.now() - started)
      const message = error instanceof SyntaxError
        ? 'El cuerpo de la solicitud no contiene JSON válido'
        : error instanceof Error ? error.message : 'No fue posible completar la solicitud'
      setResult(nextResult)
      setResponseTime(`${elapsed}ms`)
      setResponse(JSON.stringify({ detail: message, codigo: 'NETWORK_ERROR' }, null, 2))
      setEvents((current) => [{
        id: `event-${Date.now()}-${nextId.current}`,
        time: eventTime(),
        method,
        path,
        result: nextResult,
        duration: `${elapsed}ms`,
      }, ...current])
    } finally {
      nextId.current += 1
      setSending(false)
      void actualizarEstados()
    }
  }

  function startResize(event: React.PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function resize(event: React.PointerEvent<HTMLDivElement>) {
    if (!event.currentTarget.hasPointerCapture(event.pointerId) || !workspaceRef.current) return
    const bounds = workspaceRef.current.getBoundingClientRect()
    const nextSplit = ((event.clientX - bounds.left) / bounds.width) * 100
    setSplit(Math.min(72, Math.max(28, nextSplit)))
  }

  const statusClass = result === 'READY' ? 'text-muted' : resultClass(result)

  return (
    <div className="tool-shell">
      <header className="topbar">
        <button className="wordmark" onClick={() => setTopTab('Dashboard')}>MicroSim</button>
        <nav className="top-tabs" aria-label="Secciones principales">
          {(['Dashboard', 'Proxy', 'Repeater', 'Logs'] as TopTab[]).map((tab) => (
            <button className={topTab === tab ? 'active' : ''} key={tab} onClick={() => setTopTab(tab)}>{tab}</button>
          ))}
        </nav>
        <div className="top-actions">
          <span className="connection-label">API REAL</span>
          <button aria-label="Reiniciar datos y servicios" title="Reiniciar datos y servicios" onClick={() => void restart()} disabled={restarting}>
            <ToolIcon />
          </button>
        </div>
      </header>

      <div className={`content-shell ${drawerOpen && topTab !== 'Logs' ? '' : 'drawer-collapsed'}`}>
        <aside className="target-tree">
          <div className="tree-title">TARGET</div>
          <div className="tree-row root-row"><span className="caret">▾</span><span>Target</span></div>
          <div className="tree-row folder-row"><span className="branch">└─</span><span className="caret">▾</span><span>Tienda Virtual</span></div>
          <div className="service-tree">
            {services.map((service, index) => (
              <button
                className={`tree-row service-row ${selectedId === service.id ? 'selected' : ''}`}
                onClick={() => selectService(service.id)}
                key={service.id}
              >
                <span className="branch">{index === services.length - 1 ? '└─' : '├─'}</span>
                <span className={`status-bullet ${service.online ? 'online' : 'offline'}`} />
                <span>{service.host}</span>
              </button>
            ))}
          </div>
          <div className="tree-details">
            <div><span>HOST</span><strong>{selectedService.host}</strong></div>
            <div><span>PORT</span><strong>{selectedService.port}</strong></div>
            <div><span>STATE</span><strong className={selectedService.online ? 'text-success' : 'text-error'}>{selectedService.online ? 'ONLINE' : 'OFFLINE'}</strong></div>
            <div><span>RECORDS</span><strong>{selectedService.registros}</strong></div>
            <button onClick={() => void toggleSelected()} disabled={changingService}>
              {changingService ? 'Aplicando cambio...' : selectedService.online ? 'Simular fallo del servicio' : 'Restablecer servicio'}
            </button>
          </div>
        </aside>

        <main className={`work-area ${topTab === 'Logs' ? 'full-height' : ''}`} ref={workspaceRef}>
          {topTab === 'Repeater' && (
            <>
              <section className="request-panel" style={{ width: `${split}%` }}>
                <div className="panel-title"><span>REQUEST</span><span>#{nextId.current.toString().padStart(4, '0')}</span></div>
                <div className="request-bar">
                  <select value={method} onChange={(event) => setMethod(event.target.value as Method)} aria-label="Método HTTP">
                    <option>GET</option><option>POST</option><option>PUT</option><option>DELETE</option>
                  </select>
                  <input value={url} onChange={(event) => setUrl(event.target.value)} aria-label="URL del request" />
                  <button className="send-button" onClick={() => void sendRequest()} disabled={sending}>{sending ? 'Sending...' : 'Send'}</button>
                </div>
                <div className="panel-tabs">
                  {['Params', 'Headers', 'Body', 'Auth'].map((tab) => (
                    <button className={requestTab === tab ? 'active' : ''} key={tab} onClick={() => setRequestTab(tab)}>{tab}</button>
                  ))}
                </div>
                <div className="panel-content">
                  {requestTab === 'Body' ? (
                    <JsonCode
                      editable
                      value={bodies[selectedId]}
                      onChange={(value) => setBodies((current) => ({ ...current, [selectedId]: value }))}
                    />
                  ) : (
                    <div className="empty-state">
                      <span>{requestTab.toUpperCase()}</span>
                      <p>No {requestTab.toLowerCase()} configured for this request.</p>
                    </div>
                  )}
                </div>
              </section>

              <div
                className="resize-gutter"
                role="separator"
                aria-orientation="vertical"
                aria-label="Redimensionar paneles"
                onPointerDown={startResize}
                onPointerMove={resize}
              />

              <section className="response-panel" style={{ width: `${100 - split}%` }}>
                <div className="response-heading">
                  <span>RESPONSE</span>
                  <div><strong className={statusClass}>{result}</strong><span>{responseTime}</span></div>
                </div>
                <div className="panel-tabs">
                  {['Pretty', 'Raw', 'Preview'].map((tab) => (
                    <button className={responseTab === tab ? 'active' : ''} key={tab} onClick={() => setResponseTab(tab)}>{tab}</button>
                  ))}
                </div>
                <div className="panel-content">
                  {responseTab === 'Preview' ? (
                    <div className="empty-state"><span>PREVIEW</span><p>No visual preview is available for application/json.</p></div>
                  ) : responseTab === 'Raw' ? (
                    <pre className="raw-response">{response}</pre>
                  ) : (
                    <JsonCode value={response} />
                  )}
                </div>
              </section>
            </>
          )}

          {topTab === 'Dashboard' && (
            <section className="dashboard-panel">
              <div className="view-heading"><span>SYSTEM OVERVIEW</span><strong>Tienda virtual distribuida</strong></div>
              <div className="service-summary">
                {services.map((service) => (
                  <button className="summary-row" key={service.id} onClick={() => selectService(service.id)}>
                    <span className={`status-bullet ${service.online ? 'online' : 'offline'}`} />
                    <span><strong>{service.id.toUpperCase()}</strong><small>{service.host}:{service.port}</small></span>
                    <span className="summary-records">{service.registros}<small>registros</small></span>
                    <span className={service.online ? 'text-success' : 'text-error'}>{service.online ? 'ONLINE' : 'OFFLINE'}</span>
                  </button>
                ))}
              </div>
              <div className="architecture-note">
                <span>COMUNICACIÓN</span>
                <p>La interfaz consume las API mediante el gateway. Al crear un pedido, el servicio de pedidos valida el cliente y el producto con llamadas HTTP internas.</p>
              </div>
              <div className="architecture-note">
                <span>PRUEBA DE FALLO</span>
                <p>Selecciona un servicio en TARGET y usa “Simular fallo del servicio”. Los procesos independientes seguirán atendiendo sus propias rutas. Si detienes productos, los pedidos nuevos devolverán 503.</p>
              </div>
            </section>
          )}

          {topTab === 'Proxy' && (
            <section className="dashboard-panel">
              <div className="view-heading"><span>GATEWAY ROUTES</span><strong>Rutas públicas y procesos internos</strong></div>
              <div className="route-table" role="table" aria-label="Rutas del gateway">
                <div className="route-row route-header" role="row"><span>Ruta pública</span><span>Proceso destino</span><span>Función</span></div>
                {([
                  ['/api/productos/*', 'productos:8001', 'Catálogo y existencias'],
                  ['/api/clientes/*', 'clientes:8002', 'Registro y consulta de clientes'],
                  ['/api/pedidos/*', 'pedidos:8003', 'Órdenes y validación de dependencias'],
                ] as const).map((route) => (
                  <div className="route-row" role="row" key={route[0]}><code>{route[0]}</code><code>{route[1]}</code><span>{route[2]}</span></div>
                ))}
              </div>
              <div className="architecture-note"><span>ALCANCE</span><p>El gateway solo dirige el tráfico. Las reglas de negocio y los datos permanecen dentro de cada microservicio.</p></div>
            </section>
          )}

          {topTab === 'Logs' && (
            <section className="logs-panel">
              <div className="view-heading"><span>REQUEST HISTORY</span><strong>{events.length} solicitudes ejecutadas</strong></div>
              {events.length === 0 ? (
                <div className="empty-state"><span>SIN EVENTOS</span><p>Envía una solicitud desde Repeater para registrar aquí el resultado real.</p></div>
              ) : (
                <div className="event-list logs-full">
                  {events.map((event) => (
                    <div className="event-line" key={event.id}>
                      <span className="event-time">[{event.time}]</span>
                      <span className={`event-method method-${event.method.toLowerCase()}`}>{event.method}</span>
                      <span className="event-path">{event.path}</span>
                      <span className="event-arrow">→</span>
                      <span className={resultClass(event.result)}>{event.result}</span>
                      <span className="event-duration">{event.duration}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </main>

        {topTab !== 'Logs' && (
          <section className="event-drawer">
            <button className="drawer-heading" onClick={() => setDrawerOpen((open) => !open)} aria-expanded={drawerOpen}>
              <span>EVENT LOG</span>
              <span>{events.length} events&nbsp;&nbsp; {drawerOpen ? '▼' : '▲'}</span>
            </button>
            {drawerOpen && (
              <div className="event-list">
                {events.length === 0 ? <div className="event-empty">No requests yet.</div> : events.map((event) => (
                  <div className="event-line" key={event.id}>
                    <span className="event-time">[{event.time}]</span>
                    <span className={`event-method method-${event.method.toLowerCase()}`}>{event.method}</span>
                    <span className="event-path">{event.path}</span>
                    <span className="event-arrow">→</span>
                    <span className={resultClass(event.result)}>{event.result}</span>
                    <span className="event-duration">{event.duration}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}

export default App
