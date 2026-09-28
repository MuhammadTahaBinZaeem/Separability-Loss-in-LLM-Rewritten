"use strict";
const $ = (id) => document.getElementById(id);
const titles = {source:"Source integrity",semantic_A:"Semantic reviewer A",semantic_B:"Semantic reviewer B"};
const isReviewAssignment = (entry) => entry.mode === "human" && Object.hasOwn(titles, entry.kind);
const semantic = [
  ["added_facts","Added facts","Did the rewrite introduce an event or claim absent from the original?",[["0","No"],["1","Yes"]]],
  ["omitted_facts","Omitted facts","Did it remove information material to the meaning?",[["0","No"],["1","Yes"]]],
  ["order_changed","Event order changed","Did the sequence of events change?",[["0","No"],["1","Yes"]]],
  ["relationships_changed","Relationships changed","Check speakers, characters, ownership, causal roles and who did what.",[["0","No"],["1","Yes"]]],
  ["tone_drift","Tone drift","Consider emotion, seriousness, irony and narrative stance.",[["0","None"],["1","Noticeable"],["2","Substantial"]]],
  ["meaning_preservation","Meaning preservation","5 = all material meaning; 4 = minor deviations; 3 = localized material distortion; 2 = several distortions; 1 = largely changed or missing.",[["1","1"],["2","2"],["3","3"],["4","4"],["5","5"]]],
  ["usable","Usable for style comparison","Can stylistic change be studied without material meaning changes confounding it?",[["yes","Yes"],["no","No"]]]
];
let token = sessionStorage.getItem("reviewDeskToken") || "";
let principal, assignment, current, dirty=false, busy=false, loading=false, noticeTimer, adminState;
if(location.hash.length>1){token=location.hash.slice(1);sessionStorage.setItem("reviewDeskToken",token);history.replaceState(null,"",location.pathname);}
function el(tag, cls, text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
function notify(message,error=false){clearTimeout(noticeTimer);$("notice").textContent=message;$("notice").className="notice"+(error?" error":"");$("notice").hidden=false;noticeTimer=setTimeout(()=>$("notice").hidden=true,error?14000:6000);}
async function api(path,body,blob=false){const response=await fetch(path,{method:body===undefined?"GET":"POST",headers:{Authorization:"Bearer "+token,...(body===undefined?{}:{"Content-Type":"application/json"})},body:body===undefined?undefined:JSON.stringify(body)});if(!response.ok){let message="Request failed.";try{message=(await response.json()).error||message;}catch{}throw new Error(message);}return blob?response.blob():response.json();}
function showScreen(id){for(const screen of ["login","admin","waiting","review"])$(screen).hidden=screen!==id;$("logout").hidden=id==="login";}
function packetChoices(){const choices=principal?.assignments||[];$("packet-choice-label").hidden=$("packet-choice").hidden=choices.length<2;$("packet-choice").replaceChildren();for(const choice of choices){const option=el("option","",choice.label);option.value=choice.id;option.selected=choice.id===assignment?.id;$("packet-choice").append(option);}}
$("packet-choice").addEventListener("change",async()=>{if(dirty&&!confirm("Leave this item without saving changes?")){packetChoices();return;}dirty=false;await openAssignment($("packet-choice").value);packetChoices();});
async function boot(){if(!token){showScreen("login");return;}try{principal=await api("/api/me");if(principal.role==="reviewer"){await openAssignment(principal.session_id);}else if(principal.role==="admin"){showScreen("admin");await refreshAdmin();}else{throw new Error("Use your reviewer or administrator login to open this website.");}}catch(error){showScreen("login");notify(error.message,true);}}
$("login-form").addEventListener("submit",async event=>{event.preventDefault();token=$("access-token").value.trim();sessionStorage.setItem("reviewDeskToken",token);$("access-token").value="";await boot();});
$("logout").addEventListener("click",()=>{if(dirty&&!confirm("Unsaved changes will be discarded. Lock this workspace?"))return;sessionStorage.removeItem("reviewDeskToken");token="";dirty=false;location.reload();});

async function refreshAdmin(){
  try{
    adminState=await api("/api/portal/status");
    $("packet-cards").replaceChildren();
    for(const [kind,info] of Object.entries(adminState.availability)){
      if(!Object.hasOwn(titles,kind))continue;
      const card=el("article","packet-card");
      card.append(el("span","pill"+(info.available?"":" waiting"),info.available?"AVAILABLE":"WAITING"),el("h3","",titles[kind]),el("p","",info.items?`${info.items} fixed items`:(info.reason||"Packet not yet prepared.")));
      if(info.items&&info.reason)card.append(el("p","",info.reason));
      $("packet-cards").append(card);
    }
    $("assignments").replaceChildren();
    const sessions=adminState.sessions.filter(isReviewAssignment);
    if(!sessions.length)$("assignments").append(el("div","empty","No assignments yet. Create a workspace above to begin."));
    for(const s of sessions){
      const card=el("article","assignment-card"),identity=el("div"),progress=el("div","card-progress"),buttons=el("div","card-buttons");
      identity.append(el("h3","",titles[s.kind]),el("p","",s.reviewer_id));if(s.packet_label)identity.append(el("p","muted small",s.packet_label));
      progress.append(el("strong","",s.status==="awaiting_packet"?"Account ready · packet pending":`${s.complete} / ${s.total} complete`),el("p","",`${s.saved} saved · ${s.flagged} flagged · ${s.status.replaceAll("_"," ")}`));
      const open=el("button","secondary","Open workspace");
      open.addEventListener("click",async()=>{try{const result=await api(`/api/sessions/${s.id}/link`);window.open("/#"+result.fragment,"_blank","noopener,noreferrer");}catch(e){notify(e.message,true);}});
      const copy=el("button","quiet","Copy private link");
      copy.addEventListener("click",async()=>{try{const result=await api(`/api/sessions/${s.id}/link`);await navigator.clipboard.writeText(location.origin+"/#"+result.fragment);notify("Private assignment link copied. Give it only to its intended reviewer.");}catch(e){notify("Could not copy the link. Use Open workspace instead. "+e.message,true);}});
      buttons.append(open,copy);
      if(s.status==="awaiting_packet"){
        const activate=el("button","secondary","Attach issued packet");
        activate.disabled=!adminState.availability[s.kind]?.available;
        activate.title=activate.disabled?"Wait until review forms have been issued.":"Attach the issued form without changing this reviewer's login.";
        activate.addEventListener("click",async()=>{try{await api(`/api/sessions/${s.id}/activate`,{});await refreshAdmin();notify("Issued packet attached. The reviewer's existing login is unchanged.");}catch(e){notify(e.message,true);}});
        buttons.append(activate);
      }
      card.append(identity,progress,buttons);$("assignments").append(card);
    }
    $("independence").hidden=!adminState.independence_check?.available||adminState.independence_check.satisfied;
  }catch(e){notify(e.message,true);}
}
$("refresh-admin").addEventListener("click",refreshAdmin);
$("prepare").addEventListener("click",async()=>{try{const result=await api("/api/prepare",{});notify(result.complete?"Review forms checked.":"Review packets are still being prepared.");await refreshAdmin();}catch(e){notify(e.message,true);}});
$("create-form").addEventListener("submit",async event=>{event.preventDefault();try{const created=await api("/api/sessions",{kind:$("kind").value,mode:"human",reviewer_id:$("reviewer-id").value});$("reviewer-id").value="";await refreshAdmin();notify(created.status==="awaiting_packet"?"Reviewer account reserved. Its login works now; reviewing opens after its issued packet is attached.":"Assignment created. Open its workspace to begin.");}catch(e){notify(e.message,true);}});
$("independence-form").addEventListener("submit",async event=>{event.preventDefault();try{await api("/api/independence",{registry_sha256:adminState.independence_check.registry_sha256,checker_id:$("checker-id").value,method:$("check-method").value,notes:$("check-notes").value,checked_by_human:$("checker-attest").checked});notify("Provenance record preserved.");await refreshAdmin();}catch(e){notify(e.message,true);}});

async function openAssignment(id){const next=await api(`/api/sessions/${id}`);if(!isReviewAssignment(next))throw new Error("This workspace is not available in the review portal.");assignment=next;current=undefined;dirty=false;packetChoices();if(assignment.status==="awaiting_packet"){showScreen("waiting");$("waiting-title").textContent=titles[assignment.kind];$("waiting-reviewer").textContent=assignment.reviewer_id;$("waiting-reason").textContent=assignment.waiting_reason;return;}showScreen("review");$("assignment-title").textContent=titles[assignment.kind];$("reviewer-label").textContent=assignment.reviewer_id;renderGuidance();updateProgress();await loadItem("next",true);}
$("refresh-packet").addEventListener("click",async()=>{try{await openAssignment(assignment.id);if(assignment.status==="awaiting_packet")notify("Your login is working. The administrator has not attached your issued packet yet.");}catch(e){notify(e.message,true);}});
function renderGuidance(){const source=assignment.kind==="source";$("guidance").replaceChildren();const ul=el("ul");const guidance=source?[
"Read the entire passage and inspect the archived context, including its start and end boundaries.",
"Check for prefaces, introductions, editorial narration, footnotes, headings and mixed or uncertain authorship.",
"Distinguish fictional dialogue from outside-authored material. Confirm the selected span belongs to the specified work.",
"Choose Needs correction if uncertain. Write a substantive note for every passage. Do not mark a passage clean simply to finish the packet.",
"Source text, identifiers and offsets are read-only. Findings do not silently alter the frozen corpus."]:[
"Read the original and rewrite in full. Judge preservation, not which version you prefer.",
"Added/omitted facts and changed order/relationships: 0 = no, 1 = yes.",
"Tone: 0 = none, 1 = noticeable but not fundamental, 2 = substantial emotion, seriousness, irony or stance change.",
"Meaning: 5 = all material meaning retained; 4 = minor nonmaterial deviations; 3 = localized material distortion; 2 = several material distortions; 1 = largely changed or missing.",
"Usable = yes only if meaning changes do not materially confound a stylistic comparison.",
"Notes are required for any factual/order/relationship change, meaning score ≤3, or an unusable item.",
"Source identities, processing details and the other reviewer's answers are not provided in this workspace."];
for(const text of guidance)ul.append(el("li","",text));$("guidance").append(ul);}
function updateProgress(){const a=assignment;$("progress-count").textContent=`${a.complete} / ${a.total} complete`;$("progress-percent").textContent=Math.round(a.complete/a.total*100)+"%";$("progress").max=a.total;$("progress").value=a.complete;$("saved-count").textContent=`${a.saved} items saved · ${a.flagged} flagged`;$("finish").disabled=a.status!=="draft";$("finish").textContent=a.status==="draft"?"Finish review":a.status==="registered"?"Registered with study":"Return sealed";$("register-again").hidden=a.status!=="sealed"||a.mode!=="human";renderItems();}
function renderItems(){const filter=$("item-filter").value,search=$("item-search").value.trim().toLowerCase();$("item-list").replaceChildren();for(const item of assignment.items){if(search&&!item.id.toLowerCase().includes(search))continue;if(filter==="incomplete"&&item.complete||filter==="flagged"&&!item.flagged||filter==="saved"&&!item.saved)continue;const button=el("button","item-button"+(item.complete?" done":"")+(item.flagged?" flagged":"")+(current?.id===item.id?" current":""),String(item.position));button.type="button";button.title=`${item.id} · ${item.complete?"Complete":"Incomplete"}${item.flagged?" · Flagged":""}`;button.setAttribute("aria-label",`Item ${item.position}: ${item.complete?"complete":"incomplete"}`);if(current?.id===item.id)button.setAttribute("aria-current","true");button.addEventListener("click",()=>loadItem(item.id));$("item-list").append(button);}}
$("item-filter").addEventListener("change",renderItems);$("item-search").addEventListener("input",renderItems);
async function loadItem(id,force=false,scrollToReading=true){
  if(busy||loading)return;
  if(dirty&&!force&&!confirm("This item has unsaved changes. Discard them and move on?"))return;
  loading=true;setSaveState();
  try{
    const item=await api(`/api/sessions/${assignment.id}/items/${id}`);
    current=item;assignment.revision=current.revision;dirty=false;
    const source=assignment.kind==="source";
    $("item-counter").textContent=`Item ${current.position} of ${assignment.total}`;
    $("item-heading").textContent=source?"Check the source passage":"Compare meaning, not preference";
    $("item-id").textContent=current.id;
    $("original-text").textContent=current.row[source?"text":"original_text"];
    $("rewritten-text").textContent=current.row.rewritten_text||"";
    $("rewrite-card").hidden=source;$("text-grid").className="text-grid"+(source?" source":"");
    $("source-details").hidden=!source;
    $("source-details").textContent=source?`${current.row.author_id} · ${current.work?.title||current.row.work_id} · Gutenberg ${current.row.gutenberg_id} · source characters ${current.row.source_start_char}–${current.row.source_end_char}`:"";
    $("context-panel").hidden=!source||!current.context;
    if(scrollToReading)$("context-panel").open=false;
    if(current.context){$("context-before").textContent=current.context.before;$("context-selected").textContent=current.context.selected_raw;$("context-after").textContent=current.context.after;}
    renderRatings();$("notes").value=current.row.notes||"";
    $("notes-hint").textContent=source?"Required for every source passage.":"Required for factual/order/relationship changes, meaning score 1–3, or an unusable rewrite.";
    showErrors([]);renderItems();
    if(scrollToReading){$("original-text").scrollTop=0;$("rewritten-text").scrollTop=0;$("item-heading").scrollIntoView({block:"start"});}
  }catch(e){notify(e.message,true);}
  finally{loading=false;setSaveState();}
}
function renderRatings(){const fields=assignment.kind==="source"?[["verdict","Source verdict","Is this passage suitable, correctly attributed fictional body text?",[["pass","Pass"],["needs_correction","Needs correction / uncertain"]]]]:semantic;$("work-boundary").textContent=current.work?.body_start_char?`Specified work body: characters ${current.work.body_start_char}–${current.work.body_end_char}. Check the passage against this work, not editorial material elsewhere in the volume.`:"";$("rating-fields").replaceChildren();for(const [name,title,hint,choices] of fields){const field=el("fieldset","rating-field");field.append(el("legend","",title),el("p","field-hint",hint));const group=el("div","choices");for(const [value,label] of choices){const wrapper=el("label","choice");const input=el("input");input.type="radio";input.name=name;input.value=value;input.checked=current.row[name]===value;input.disabled=assignment.status!=="draft";wrapper.append(input,document.createTextNode(label));group.append(wrapper);}field.append(group);$("rating-fields").append(field);}}
function setSaveState(){const saved=assignment.items.find(r=>r.id===current?.id)?.saved;const pending=busy||loading;const locked=pending||!current||assignment.status!=="draft";$("save-state").textContent=loading?"Loading passage…":busy?"Saving…":dirty?"Unsaved changes":assignment.status!=="draft"?"Sealed return":saved?"Saved on this computer":"Not yet saved";$("save-state").className="save-state"+(dirty?" unsaved":"");$("revision-label").textContent=`Revision ${assignment.revision}`;$("save").disabled=locked;$("save-next").disabled=locked;$("previous").disabled=pending||!current||current.position===1;$("next").disabled=pending||!current||current.position===assignment.total;$("finish").disabled=pending||assignment.status!=="draft";$("notes").disabled=locked;for(const field of $("rating-fields").querySelectorAll("input"))field.disabled=locked;for(const id of ["validate","download","full-source"])$(id).disabled=pending||!current;}
function showErrors(errors){$("item-errors").hidden=!errors.length;$("item-errors").textContent=errors.join("\n");}
$("rating-form").addEventListener("input",()=>{dirty=true;setSaveState();});$("rating-form").addEventListener("submit",e=>e.preventDefault());
function values(){const result={notes:$("notes").value};for(const f of current.editable_fields){if(f!=="notes")result[f]=$("rating-form").querySelector(`input[name="${f}"]:checked`)?.value||"";}return result;}
async function save(move=false){if(busy||loading||!current||assignment.status!=="draft")return;busy=true;setSaveState();try{const position=current.position;const result=await api(`/api/sessions/${assignment.id}/items/${current.id}`,{revision:assignment.revision,values:values()});dirty=false;assignment=await api(`/api/sessions/${assignment.id}`);updateProgress();$("disk-status").textContent="Saved to disk in the study's required return format.";notify(result.errors.length?"Draft saved. Complete the remaining fields before finishing.":"Saved. This item is complete.");busy=false;if(move&&position<assignment.total)await loadItem(assignment.items[position].id,true);else{await loadItem(current.id,true,false);showErrors(result.errors);}}catch(e){notify(e.message,true);}finally{busy=false;setSaveState();}}
$("save").addEventListener("click",()=>save(false));$("save-next").addEventListener("click",()=>save(true));
function move(delta){if(!current||busy||loading)return;const index=current.position-1+delta;if(index>=0&&index<assignment.total)loadItem(assignment.items[index].id);}
$("previous").addEventListener("click",()=>move(-1));$("next").addEventListener("click",()=>move(1));
$("download").addEventListener("click",async()=>{try{if(dirty){notify("Save your current changes first; the download includes saved answers only.",true);return;}const blob=await api(`/api/sessions/${assignment.id}/download`,undefined,true);const url=URL.createObjectURL(blob);const a=el("a");a.href=url;a.download=`review_${assignment.kind}_${assignment.status}.${assignment.kind==="source"?"jsonl":"csv"}`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}catch(e){notify(e.message,true);}});
$("full-source").addEventListener("click",async()=>{try{const blob=await api(`/api/sessions/${assignment.id}/items/${current.id}/source`,undefined,true);const url=URL.createObjectURL(blob);const a=el("a");a.href=url;a.download=`pg${current.row.gutenberg_id}.txt`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}catch(e){notify(e.message,true);}});
$("validate").addEventListener("click",async()=>{try{const result=await api(`/api/sessions/${assignment.id}/check`);if(result.valid)notify("All required responses are present. This checks form completeness, not scientific correctness.");else{notify(`${result.incomplete_items} items need ratings or notes. Showing the first incomplete item.`);await loadItem(result.errors[0].item_id);showErrors(result.errors[0].errors);}}catch(e){notify(e.message,true);}});
$("finish").addEventListener("click",async()=>{try{if(dirty){notify("Save the current item before finishing.",true);return;}const check=await api(`/api/sessions/${assignment.id}/check`);if(!check.valid){notify(`${check.incomplete_items} items still need ratings or notes.`,true);return;}$("finish-title").textContent="Submit your completed review?";$("finish-explanation").textContent="Your responses, reviewer pseudonym, completion confirmation and submission time will be preserved and registered with the study.";$("reviewer-attest").checked=false;$("confirm-finish").textContent="Confirm & submit review";$("finish-dialog").showModal();}catch(e){notify(e.message,true);}});
$("cancel-finish").addEventListener("click",()=>$("finish-dialog").close());
$("finish-form").addEventListener("submit",async event=>{event.preventDefault();$("confirm-finish").disabled=true;try{await api(`/api/sessions/${assignment.id}/seal`,{revision:assignment.revision,attest_human:isReviewAssignment(assignment)&&$("reviewer-attest").checked});$("finish-dialog").close();assignment=await api(`/api/sessions/${assignment.id}`);updateProgress();await loadItem(current.id,true);notify(assignment.status==="registered"?"Your original return has been preserved and registered.":"Your original return has been preserved. Study registration is pending.");}catch(e){notify(e.message,true);$("finish-dialog").close();assignment=await api(`/api/sessions/${assignment.id}`);updateProgress();await loadItem(current.id,true);}finally{$("confirm-finish").disabled=false;}});
$("register-again").addEventListener("click",async()=>{try{await api(`/api/sessions/${assignment.id}/register`,{});assignment=await api(`/api/sessions/${assignment.id}`);updateProgress();notify("Registration checked.");}catch(e){notify(e.message,true);}});
window.addEventListener("beforeunload",event=>{if(dirty){event.preventDefault();event.returnValue="";}});
document.addEventListener("keydown",event=>{if($("review").hidden)return;if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="s"){event.preventDefault();save(false);}else if(event.altKey&&event.key==="ArrowRight"){event.preventDefault();move(1);}else if(event.altKey&&event.key==="ArrowLeft"){event.preventDefault();move(-1);}});
boot();
