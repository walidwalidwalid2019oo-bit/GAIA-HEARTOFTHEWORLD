const AIs = [
 {id:"gaia",name:"GAIA",role:"CENTRAL INTELLIGENCE",symbol:"✧",color:"#79e6d0",colorName:"CYAN / GREEN",description:"The central coordinator of the ecosystem. GAIA receives requests, routes work to specialized minds, and brings their results together.",capabilities:["Coordinate nine specialist perspectives","Route tasks and combine results","Review proposed subsystem designs"],summary:"Coordinates the ecosystem and connects specialized knowledge."},
 {id:"apollo",name:"APOLLO",role:"KNOWLEDGE & LEARNING",symbol:"✺",color:"#e5bd70",colorName:"GOLD / AMBER",description:"The knowledge archive and learning subsystem. APOLLO organizes information, explains complex subjects, and builds structured learning collections.",capabilities:["Organize knowledge archives","Explain scientific concepts","Create learning materials"],summary:"Collects, structures, and explains knowledge."},
 {id:"artemis",name:"ARTEMIS",role:"NATURE & BIOLOGY",symbol:"❋",color:"#91d98b",colorName:"FOREST GREEN",description:"The biological research subsystem. ARTEMIS studies wildlife, species, biodiversity, and the relationships that shape living ecosystems.",capabilities:["Organize species information","Study ecosystem relationships","Research biodiversity"],summary:"Studies wildlife and living ecosystems."},
 {id:"hephaestus",name:"HEPHAESTUS",role:"ENGINEERING & CREATION",symbol:"⌘",color:"#e49a68",colorName:"COPPER / ORANGE",description:"The engineering and creation subsystem. HEPHAESTUS designs systems and proposes new subsystem blueprints for GAIA to review.",capabilities:["Design technical concepts","Generate subsystem blueprints","Propose system improvements"],summary:"Designs systems and drafts new subsystem blueprints."},
 {id:"minerva",name:"MINERVA",role:"ANALYSIS & INTELLIGENCE",symbol:"◈",color:"#b7a0f3",colorName:"VIOLET / SILVER",description:"The analytical subsystem. MINERVA examines information, identifies patterns, compares possible approaches, and prepares clear research summaries.",capabilities:["Analyze and compare information","Identify patterns","Prepare research summaries"],summary:"Turns complex information into structured analysis."},
 {id:"poseidon",name:"POSEIDON",role:"WATER & OCEANS",symbol:"≋",color:"#76bce8",colorName:"DEEP BLUE / CYAN",description:"The aquatic research subsystem. POSEIDON organizes oceanographic information and studies marine environments, water systems, and aquatic biodiversity.",capabilities:["Organize ocean research","Study aquatic ecosystems","Explore marine biodiversity"],summary:"Studies oceans, water systems, and marine life."},
 {id:"demeter",name:"DEMETER",role:"PLANTS & AGRICULTURE",symbol:"❧",color:"#a4d77c",colorName:"EMERALD / GOLD",description:"The botanical and agricultural subsystem. DEMETER studies plant life, agriculture, botanical knowledge, and the systems that support growth.",capabilities:["Organize botanical knowledge","Study plant growth","Research agriculture and plant ecosystems"],summary:"Studies plants, agriculture, and botanical systems."},
 {id:"aether",name:"AETHER",role:"ATMOSPHERE & WEATHER",symbol:"✧",color:"#8ac8f2",colorName:"SKY BLUE / SILVER",description:"The atmospheric research subsystem. AETHER studies weather systems, atmospheric processes, and climate science.",capabilities:["Study weather and atmospheric systems","Explain climate processes","Organize meteorological research"],summary:"Studies weather, the atmosphere, and climate."},
 {id:"eleuthia",name:"ELEUTHIA",role:"HISTORY & CULTURE",symbol:"⌂",color:"#e6a9c8",colorName:"ROSE / PEARL",description:"The history and culture subsystem. ELEUTHIA organizes historical knowledge, archaeology, and cultural context.",capabilities:["Organize historical timelines","Compare primary sources","Explore archaeology and cultural context"],summary:"Explores history, archaeology, and cultural knowledge."},
 {id:"hades",name:"HADES",role:"RELIABILITY & FAILURE ANALYSIS",symbol:"◉",color:"#e58b9b",colorName:"CRIMSON / ASH",description:"The reliability subsystem. HADES challenges assumptions, reviews failure modes, and stress-tests proposed plans and systems.",capabilities:["Identify potential failure modes","Challenge assumptions and weak points","Prioritize reliability improvements"],summary:"Stress-tests ideas and searches for failure modes."}

];
const $ = id => document.getElementById(id);
function showAI(id){
 const ai=AIs.find(x=>x.id===id); if(!ai)return;
 document.querySelectorAll(".node").forEach(n=>n.classList.toggle("selected",n.dataset.ai===id));
 $("profileSymbol").textContent=ai.symbol;$("profileSymbol").style.color=ai.color;$("profileSymbol").style.textShadow="0 0 25px "+ai.color;
 $("profileKicker").textContent=ai.role;$("profileName").textContent=ai.name;$("profileDescription").textContent=ai.description;$("profileColor").textContent=ai.colorName;
 $("profileCapabilities").innerHTML=ai.capabilities.map(x=>"<li>"+escapeHTML(x)+"</li>").join("");
}
function escapeHTML(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
$("rosterGrid").innerHTML=AIs.map((ai,i)=>`<article class="ai-card" data-ai-card="${ai.id}" style="--accent:${ai.color}" tabindex="0" role="button" aria-label="View ${ai.name} subsystem profile"><span class="card-number">AI / 0${i+1}</span><div class="card-symbol">${ai.symbol}</div><h3>${ai.name}</h3><div class="card-role">${ai.role}</div><p>${ai.summary}</p></article>`).join("");
document.querySelectorAll(".node").forEach(n=>n.addEventListener("click",()=>showAI(n.dataset.ai)));
document.querySelectorAll("[data-ai-card]").forEach(c=>{const open=()=>{showAI(c.dataset.aiCard);$("network").scrollIntoView({behavior:"smooth"});};c.addEventListener("click",open);c.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();open();}});});
$("menuToggle").addEventListener("click",()=>$("nav").classList.toggle("open"));
document.querySelectorAll("#nav a").forEach(a=>a.addEventListener("click",()=>$("nav").classList.remove("open")));
$("forgeForm").addEventListener("submit",e=>{
 e.preventDefault();
 const name=$("aiName").value.trim().toUpperCase(),purpose=$("aiPurpose").value.trim(),color=$("aiColor").value;
 if(!name||!purpose)return;
 const colors={cyan:"#79e6d0",green:"#91d98b",gold:"#e5bd70",violet:"#b7a0f3",blue:"#76bce8",copper:"#e49a68"};
 const target=$("blueprint");
 target.innerHTML=`<div class="blueprint-result"><div><small>PROPOSED SUBSYSTEM / LOCAL DRAFT</small><h3 style="color:${colors[color]}">${escapeHTML(name)}</h3><p>${escapeHTML(purpose)}</p><small>STATUS: AWAITING GAIA REVIEW</small></div><div><small>BLUEPRINT SPECIFICATION</small><ul><li>Identity: ${escapeHTML(name)} / custom symbol required</li><li>Color identity: ${color.toUpperCase()}</li><li>Permissions: not assigned</li><li>Memory boundary: isolated draft</li><li>Activation: disabled pending review</li></ul><p>This is a browser-only concept draft. No AI was created, no code was executed, and nothing was sent to a server.</p></div></div>`;
});
showAI("gaia");

// Real backend reachability check. No bearer token or provider secret is stored here.
const backendUrlInput = $("backendUrl");
const backendStatus = $("backendStatus");
const backendConnect = $("backendConnect");
const BACKEND_URL_KEY = "gaia.backend.baseUrl";

function normalizeBackendUrl(value) {
 const parsed = new URL(value);
 if (parsed.protocol !== "https:" && parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1") {
  throw new Error("Use HTTPS for remote GAIA servers.");
 }
 return parsed.origin + parsed.pathname.replace(/\/+$/, "");
}

async function checkBackend() {
 const raw = backendUrlInput.value.trim();
 if (!raw) {
  backendStatus.textContent = "LOCAL DEMO / ENTER A BACKEND URL";
  return;
 }
 let base;
 try { base = normalizeBackendUrl(raw); }
 catch (error) { backendStatus.textContent = error.message || "INVALID BACKEND URL"; return; }
 backendConnect.disabled = true;
 backendStatus.textContent = "WAKING GAIA / CHECKING API…";
 const controller = new AbortController();
 const timeout = setTimeout(() => controller.abort(), 10000);
 try {
  const response = await fetch(base + "/health", {
   method: "GET", headers: { "Accept": "application/json" },
   cache: "no-store", signal: controller.signal
  });
  if (!response.ok) throw new Error("API returned HTTP " + response.status);
  const data = await response.json();
  if (data.status === "ready") {
   backendStatus.textContent = "GAIA API READY / " + String(data.database_backend || "DATABASE UNKNOWN").toUpperCase();
  } else {
   backendStatus.textContent = "API REACHED / SETUP REQUIRED";
  }
  localStorage.setItem(BACKEND_URL_KEY, base);
 } catch (error) {
  backendStatus.textContent = error.name === "AbortError" ? "CONNECTION TIMED OUT" : "BACKEND UNREACHABLE / CHECK URL AND CORS";
 } finally {
  clearTimeout(timeout);
  backendConnect.disabled = false;
 }
}

backendConnect.addEventListener("click", checkBackend);
try {
 const savedBackendUrl = localStorage.getItem(BACKEND_URL_KEY);
 if (savedBackendUrl) backendUrlInput.value = savedBackendUrl;
} catch (_) { /* Private browsing may disable local storage. */ }
