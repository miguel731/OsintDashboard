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
  const [tools, setTools] = useState(["amass","subfinder","theharvester"]); // hibp para emails
  const [scans, setScans] = useState([]);
  const [findings, setFindings] = useState([]);

  // Filtros
  const [filterTool, setFilterTool] = useState("all");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [search, setSearch] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [logScanId, setLogScanId] = useState(null);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/projects`).then(r=>r.json()).then(setProjects);
    fetch(`${API}/api/scans`).then(r=>r.json()).then(setScans);
  }, []);

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
            <label><input type="checkbox" checked={tools.includes("amass")} onChange={e=>{
              const v = "amass"; setTools(e.target.checked ? [...tools,v] : tools.filter(t=>t!==v));
            }} /> Amass</label>
            <label><input type="checkbox" checked={tools.includes("subfinder")} onChange={e=>{
              const v = "subfinder"; setTools(e.target.checked ? [...tools,v] : tools.filter(t=>t!==v));
            }} /> Subfinder</label>
            <label><input type="checkbox" checked={tools.includes("theharvester")} onChange={e=>{
              const v = "theharvester"; setTools(e.target.checked ? [...tools,v] : tools.filter(t=>t!==v));
            }} /> TheHarvester</label>
            <label><input type="checkbox" checked={tools.includes("hibp")} onChange={e=>{
              const v = "hibp"; setTools(e.target.checked ? [...tools,v] : tools.filter(t=>t!==v));
            }} /> HIBP (email)</label>
          </div>
          <button onClick={startScan}>Iniciar escaneo</button>
        </div>
      </div>

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