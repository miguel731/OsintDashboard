import React, { useEffect, useState } from "react";
import "chart.js/auto";
import { Bar } from "react-chartjs-2";
import Cytoscape from "cytoscape";

const API = import.meta.env.VITE_API_BASE || `${window.location.protocol}//${window.location.hostname}:8000`;

export default function App() {
  const [clients, setClients] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [target, setTarget] = useState("");
  const [tools, setTools] = useState(["subfinder","theharvester"]); // hibp para emails
  const [scans, setScans] = useState([]);
  const [findings, setFindings] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [scheduleInterval, setScheduleInterval] = useState(60);
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  const [editingSchedule, setEditingSchedule] = useState(null);

    const fmtDTLocal = (iso) => {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const startEditSchedule = (s) => {
    setEditingScheduleId(s.id);
    setEditingSchedule({
      tools: [...(s.tools || [])],
      interval_minutes: s.interval_minutes,
      next_run_at: s.next_run_at
    });
  };

  const cancelEditSchedule = () => {
    setEditingScheduleId(null);
    setEditingSchedule(null);
  };

  const saveEditSchedule = async (id) => {
    const payload = {};
    if (editingSchedule?.tools) payload.tools = editingSchedule.tools;
    if (editingSchedule?.interval_minutes) payload.interval_minutes = Number(editingSchedule.interval_minutes);
    if (editingSchedule?.next_run_at) payload.next_run_at = new Date(editingSchedule.next_run_at).toISOString();

    const res = await fetch(`${API}/api/schedules/${id}`, {
      method:"PATCH",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(payload)
    });
    const updated = await res.json();
    setSchedules(schedules.map(x => x.id === id ? updated : x));
    cancelEditSchedule();
  };
  // Filtros
  const [filterTool, setFilterTool] = useState("all");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [search, setSearch] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [logScanId, setLogScanId] = useState(null);
  const [logs, setLogs] = useState([]);
  const pendingController = React.useRef(null);

  const fetchScans = async (projectId, signal) => {
    const qs = projectId ? `?project_id=${projectId}&limit=100` : `?limit=100`;
    const res = await fetch(`${API}/api/scans${qs}`, { signal });
    const data = await res.json();
    setScans(data);
  };

  useEffect(() => {
    fetch(`${API}/api/projects`).then(r=>r.json()).then(setProjects);
    const ac = new AbortController();
    fetchScans(selectedProject, ac.signal);
    fetch(`${API}/api/schedules`).then(r=>r.json()).then(setSchedules);
    return () => ac.abort();
  }, []); // carga inicial

  useEffect(() => {
    if (!autoRefresh) return;
    const load = () => {
      const ac = new AbortController();
      try { pendingController.current?.abort(); } catch {}
      pendingController.current = ac;
      fetchScans(selectedProject, ac.signal);
      fetch(`${API}/api/schedules`).then(r=>r.json()).then(setSchedules);
    };
    load();
    const id = setInterval(load, 8000);
    return () => { clearInterval(id); try { pendingController.current?.abort(); } catch {} };
  }, [autoRefresh, selectedProject]);

  useEffect(() => {
    const load = async () => {
      const all = await fetch(`${API}/api/scans`).then(r=>r.json());
      setScans(all);
    };
    load();
    if (!autoRefresh) return;
    const id = setInterval(load, 8000);
    return () => clearInterval(id);
  }, [autoRefresh]);

  const filteredFindings = findings.filter(f => {
    const byTool = filterTool === "all" || f.tool === filterTool;
    const byCat = filterCategory === "all" || f.category === filterCategory;
    const bySev = filterSeverity === "all" || f.severity === filterSeverity;
    const bySearch = !search || (f.value?.toLowerCase().includes(search.toLowerCase()));
    return byTool && byCat && bySev && bySearch;
  });

  const chartData = (items = filteredFindings) => {
    const counts = items.reduce((acc, f) => {
      acc[f.category] = (acc[f.category]||0)+1;
      return acc;
    }, {});
    return {
      labels: Object.keys(counts),
      datasets: [{ label:"Hallazgos", data:Object.values(counts), backgroundColor:"#4f46e5" }]
    };
  };

  const visibleScans = selectedProject ? scans.filter(s => s.project_id === selectedProject) : scans;

  const createProject = async () => {
    const name = prompt("Nombre del proyecto:");
    if (!name) return;
    const res = await fetch(`${API}/api/projects`, {
      method:"POST", headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ name })
    });
    const p = await res.json();
    setProjects([p, ...projects]);
  };

  const startScan = async () => {
    if (!selectedProject || !target) return alert("Selecciona proyecto y objetivo");
    const res = await fetch(`${API}/api/scans`, {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ project_id: selectedProject, target, tools })
    });
    const s = await res.json();
    setScans([s, ...scans]);
    setTarget("");
  };

  const createSchedule = async () => {
    if (!selectedProject) return alert("Selecciona un proyecto para programar");
    if (!target) return alert("Define el objetivo del schedule");
    const body = { project_id: selectedProject, target, tools, interval_minutes: Number(scheduleInterval) || 60 };
    const res = await fetch(`${API}/api/schedules`, {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(body)
    });
    const s = await res.json();
    setSchedules([s, ...schedules]);
  };

  const toggleSchedule = async (id, enabled) => {
    const res = await fetch(`${API}/api/schedules/${id}`, {
      method:"PATCH",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ enabled })
    });
    const s = await res.json();
    setSchedules(schedules.map(x => x.id === id ? s : x));
  };

  const deleteSchedule = async (id) => {
    if (!confirm(`¿Eliminar schedule #${id}?`)) return;
    const res = await fetch(`${API}/api/schedules/${id}`, { method:"DELETE" });
    if (res.status === 204) setSchedules(schedules.filter(x => x.id !== id));
  };

  const deleteProject = async () => {
    if (!selectedProject) return;
    if (!confirm("¿Eliminar proyecto seleccionado?")) return;
    await fetch(`${API}/api/projects/${selectedProject}`, { method: "DELETE" });
    setProjects(projects.filter(p => p.id !== selectedProject));
    setSelectedProject(null);
    setScans(scans.filter(s => s.project_id !== selectedProject));
  };

  const stopScan = async (scanId) => {
    await fetch(`${API}/api/scans/${scanId}/stop`, { method: "POST" });
    setScans(scans.map(s => s.id === scanId ? { ...s, status: "stopping" } : s));
  };

  const rerunScan = async (scanId) => {
    const s = await fetch(`${API}/api/scans/${scanId}`).then(r => r.json());
    const res = await fetch(`${API}/api/scans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: s.project_id, target: s.target, tools: s.tools })
    });
    const newScan = await res.json();
    setScans([newScan, ...scans]);
  };

  const openLogs = (scanId) => { setLogScanId(scanId); setLogs([]); };
  const closeLogs = () => { setLogScanId(null); setLogs([]); };

  const viewFindings = async (scanId) => {
    const res = await fetch(`${API}/api/scans/${scanId}/findings`);
    const f = await res.json();
    setFindings(f);
    renderGraph(f);
  };

  const renderGraph = (f) => {
    const container = document.getElementById("graph");
    container.innerHTML = "";
    const cy = Cytoscape({ container, style: [{ selector: "node", style: { label: "data(id)" } }] });
    const nodes = new Set();
    const edges = [];
    for (const item of f) {
      if (item.category === "subdomain" || item.category === "host") {
        nodes.add(item.value);
        edges.push({ data: { id: `${item.value}->root`, source: item.value, target: "root" } });
      }
    }
    nodes.add("root");
    cy.add([...nodes].map(n => ({ data: { id: n } })));
    cy.add(edges);
    cy.layout({ name:"cose" }).run();
  };

  useEffect(() => {
    if (!logScanId) return;
    const wsUrl = (API.startsWith("http") ? API.replace(/^http/, "ws") : `ws://${location.hostname}:8000`) + `/ws/scans/${logScanId}/logs`;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (e) => setLogs(prev => [...prev, e.data]);
    ws.onerror = () => { try { ws.close(); } catch {} };
    return () => { try { ws.close(); } catch {} };
  }, [logScanId]);

  return (
    <div style={{ padding: 20, fontFamily:"system-ui" }}>
      <h2>Dashboard OSINT</h2>

      <div style={{ display:"flex", gap:20, marginBottom:20 }}>
        <div>
          <button onClick={createProject}>Nuevo proyecto</button>{" "}
          <button onClick={deleteProject} disabled={!selectedProject}>Eliminar proyecto</button>
          <div style={{ marginTop:10 }}>
            <select value={selectedProject||""} onChange={e=>setSelectedProject(Number(e.target.value))}>
              <option value="">Seleccione proyecto</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        </div>
        <div>
          <input placeholder="Dominio/IP/Email" value={target} onChange={e=>setTarget(e.target.value)} />
          <div>
            {/* Amass eliminado */}
            {/* Subfinder */}
            <label><input type="checkbox" checked={tools.includes("subfinder")} onChange={e=>{
              const v = "subfinder"; setTools(e.target.checked ? [...tools,v] : tools.filter(t=>t!==v));
            }} /> Subfinder</label>
            {/* TheHarvester */}
            <label><input type="checkbox" checked={tools.includes("theharvester")} onChange={e=>{
              const v = "theharvester"; setTools(e.target.checked ? [...tools,v] : tools.filter(t=>t!==v));
            }} /> TheHarvester</label>
            {/* HIBP eliminado */}
          </div>
          <button onClick={startScan}>Iniciar escaneo</button>
          <div style={{ marginTop:8 }}>
            <input type="number" min="1" style={{ width:120 }} value={scheduleInterval} onChange={e=>setScheduleInterval(e.target.value)} />
            <button onClick={createSchedule} style={{ marginLeft:8 }}>Programar cada N minutos</button>
          </div>
        </div>
      </div>

      <h3>Programaciones</h3>
      <table border="1" cellPadding="6" width="100%">
        <thead><tr><th>ID</th><th>Proyecto</th><th>Objetivo</th><th>Herramientas</th><th>Intervalo</th><th>Próxima</th><th>Habilitado</th><th>Acciones</th></tr></thead>
        <tbody>
          {schedules.map(s => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td>{s.project_id ?? "-"}</td>
              <td>{s.target}</td>
              <td>
                {editingScheduleId === s.id ? (
                  <div style={{ display:"flex", gap:8 }}>
                    <label>
                      <input
                        type="checkbox"
                        checked={editingSchedule.tools.includes("subfinder")}
                        onChange={e => {
                          const v = "subfinder";
                          setEditingSchedule(ed => ({
                            ...ed,
                            tools: e.target.checked ? [...ed.tools, v] : ed.tools.filter(t => t !== v)
                          }));
                        }}
                      /> Subfinder
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={editingSchedule.tools.includes("theharvester")}
                        onChange={e => {
                          const v = "theharvester";
                          setEditingSchedule(ed => ({
                            ...ed,
                            tools: e.target.checked ? [...ed.tools, v] : ed.tools.filter(t => t !== v)
                          }));
                        }}
                      /> TheHarvester
                    </label>
                  </div>
                ) : (
                  (s.tools||[]).join(", ")
                )}
              </td>
              <td>
                {editingScheduleId === s.id ? (
                  <input
                    type="number"
                    min="1"
                    value={editingSchedule.interval_minutes}
                    onChange={e => setEditingSchedule(ed => ({ ...ed, interval_minutes: e.target.value }))}
                    style={{ width: 100 }}
                  />
                ) : (
                  `${s.interval_minutes}m`
                )}
              </td>
              <td>
                {editingScheduleId === s.id ? (
                  <input
                    type="datetime-local"
                    value={fmtDTLocal(editingSchedule.next_run_at || new Date().toISOString())}
                    onChange={e => setEditingSchedule(ed => ({ ...ed, next_run_at: e.target.value }))}
                  />
                ) : (
                  new Date(s.next_run_at).toLocaleString()
                )}
              </td>
              <td>{s.enabled ? "Sí" : "No"}</td>
              <td>
                {editingScheduleId === s.id ? (
                  <>
                    <button onClick={() => saveEditSchedule(s.id)}>Guardar</button>{" "}
                    <button onClick={cancelEditSchedule}>Cancelar</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => toggleSchedule(s.id, !s.enabled)}>{s.enabled ? "Deshabilitar" : "Habilitar"}</button>{" "}
                    <button onClick={() => startEditSchedule(s)}>Editar</button>{" "}
                    <button onClick={() => deleteSchedule(s.id)}>Eliminar</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Escaneos</h3>
      <table border="1" cellPadding="6">
        <thead><tr><th>ID</th><th>Proyecto</th><th>Objetivo</th><th>Estado</th><th>Herramientas</th><th>Acciones</th></tr></thead>
        <tbody>
          {visibleScans.map(s => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td>{s.project_id}</td>
              <td>{s.target}</td>
              <td>{s.status}</td>
              <td>{(s.tools||[]).join(", ")}</td>
              <td>
                <button onClick={() => viewFindings(s.id)}>Ver</button>{" "}
                <button onClick={() => openLogs(s.id)}>Logs</button>{" "}
                <button onClick={() => stopScan(s.id)}>Detener</button>{" "}
                <button onClick={() => rerunScan(s.id)}>Reiniciar</button>{" "}
                <button onClick={async () => {
                  if (!confirm(`¿Eliminar scan #${s.id}?`)) return;
                  const res = await fetch(`${API}/api/scans/${s.id}`, { method: "DELETE" });
                  if (!res.ok && res.status !== 204) {
                    const txt = await res.text();
                    alert(`No se pudo eliminar: ${res.status} ${txt}`);
                    return;
                  }
                  setScans(scans.filter(x => x.id !== s.id));
                }}>Eliminar</button>{" "}
                <a href={`${API}/api/exports/${s.id}.csv`} target="_blank" rel="noreferrer">CSV</a>{" "}
                <a href={`${API}/api/exports/${s.id}.pdf`} target="_blank" rel="noreferrer">PDF</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 style={{ marginTop:20 }}>Hallazgos</h3>

      <div style={{ display:"flex", gap:12, marginBottom:10 }}>
        <select value={filterTool} onChange={e=>setFilterTool(e.target.value)}>
          <option value="all">Herramienta: Todas</option>
          {[...new Set(findings.map(f=>f.tool))].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={filterCategory} onChange={e=>setFilterCategory(e.target.value)}>
          <option value="all">Categoría: Todas</option>
          {[...new Set(findings.map(f=>f.category))].map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filterSeverity} onChange={e=>setFilterSeverity(e.target.value)}>
          <option value="all">Severidad: Todas</option>
          {[...new Set(findings.map(f=>f.severity))].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input placeholder="Buscar valor..." value={search} onChange={e=>setSearch(e.target.value)} />
        <label style={{ display:"flex", alignItems:"center", gap:6 }}>
          <input type="checkbox" checked={autoRefresh} onChange={e=>setAutoRefresh(e.target.checked)} />
          Auto-refresh escaneos
        </label>
      </div>

      <div style={{ display:"flex", gap:20 }}>
        <div style={{ flex:1 }}>
          <Bar data={chartData(filteredFindings)} />
        </div>
        <div id="graph" style={{ flex:1, height: 400, border:"1px solid #ddd" }} />
      </div>

      {logScanId && (
        <div style={{ marginTop:20 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <h3 style={{ margin:0 }}>Logs Scan #{logScanId}</h3>
            <button onClick={closeLogs}>Cerrar</button>
          </div>
          <pre style={{ background:"#0b1022", color:"#9efc9e", padding:10, height:240, overflow:"auto" }}>{logs.join("\n")}</pre>
        </div>
      )}

      <div style={{ marginTop:20 }}>
        <table border="1" cellPadding="6" width="100%">
          <thead><tr><th>Herramienta</th><th>Categoría</th><th>Valor</th><th>Severidad</th></tr></thead>
          <tbody>
            {filteredFindings.map(f => (
              <tr key={f.id}>
                <td>{f.tool}</td>
                <td>{f.category}</td>
                <td>{f.value}</td>
                <td>{f.severity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}