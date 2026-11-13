const AIs = [
 {id:"gaia",name:"GAIA",role:"CENTRAL INTELLIGENCE",symbol:"✧",color:"#79e6d0",colorName:"CYAN / GREEN",description:"The central coordinator of the ecosystem. GAIA receives requests, routes work to specialized minds, and brings their results together.",capabilities:["Coordinate all six subsystems","Route tasks and combine results","Review proposed subsystem designs"],summary:"Coordinates the ecosystem and connects specialized knowledge."},
 {id:"apollo",name:"APOLLO",role:"KNOWLEDGE & LEARNING",symbol:"✺",color:"#e5bd70",colorName:"GOLD / AMBER",description:"The knowledge archive and learning subsystem. APOLLO organizes information, explains complex subjects, and builds structured learning collections.",capabilities:["Organize knowledge archives","Explain scientific concepts","Create learning materials"],summary:"Collects, structures, and explains knowledge."},
 {id:"artemis",name:"ARTEMIS",role:"NATURE & BIOLOGY",symbol:"❋",color:"#91d98b",colorName:"FOREST GREEN",description:"The biological research subsystem. ARTEMIS studies wildlife, species, biodiversity, and the relationships that shape living ecosystems.",capabilities:["Organize species information","Study ecosystem relationships","Research biodiversity"],summary:"Studies wildlife and living ecosystems."},
 {id:"hephaestus",name:"HEPHAESTUS",role:"ENGINEERING & CREATION",symbol:"⌘",color:"#e49a68",colorName:"COPPER / ORANGE",description:"The engineering and creation subsystem. HEPHAESTUS designs systems and proposes new subsystem blueprints for GAIA to review.",capabilities:["Design technical concepts","Generate subsystem blueprints","Propose system improvements"],summary:"Designs systems and drafts new subsystem blueprints."},
 {id:"minerva",name:"MINERVA",role:"ANALYSIS & INTELLIGENCE",symbol:"◈",color:"#b7a0f3",colorName:"VIOLET / SILVER",description:"The analytical subsystem. MINERVA examines information, identifies patterns, compares possible approaches, and prepares clear research summaries.",capabilities:["Analyze and compare information","Identify patterns","Prepare research summaries"],summary:"Turns complex information into structured analysis."},
 {id:"poseidon",name:"POSEIDON",role:"WATER & OCEANS",symbol:"≋",color:"#76bce8",colorName:"DEEP BLUE / CYAN",description:"The aquatic research subsystem. POSEIDON organizes oceanographic information and studies marine environments, water systems, and aquatic biodiversity.",capabilities:["Organize ocean research","Study aquatic ecosystems","Explore marine biodiversity"],summary:"Studies oceans, water systems, and marine life."},
 {id:"demeter",name:"DEMETER",role:"PLANTS & AGRICULTURE",symbol:"❧",color:"#a4d77c",colorName:"EMERALD / GOLD",description:"The botanical and agricultural subsystem. DEMETER studies plant life, agriculture, botanical knowledge, and the systems that support growth.",capabilities:["Organize botanical knowledge","Study plant growth","Research agriculture and plant ecosystems"],summary:"Studies plants, agriculture, and botanical systems."}
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
$("rosterGrid").innerHTML=AIs.map((ai,i)=>`<article class="ai-card" data-ai-card="${ai.id}" style="--accent:${ai.color}"><span class="card-number">AI / 0${i+1}</span><div class="card-symbol">${ai.symbol}</div><h3>${ai.name}</h3><div class="card-role">${ai.role}</div><p>${ai.summary}</p></article>`).join("");
document.querySelectorAll(".node").forEach(n=>n.addEventListener("click",()=>showAI(n.dataset.ai)));
document.querySelectorAll("[data-ai-card]").forEach(c=>c.addEventListener("click",()=>{showAI(c.dataset.aiCard);$("network").scrollIntoView({behavior:"smooth"});}));
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