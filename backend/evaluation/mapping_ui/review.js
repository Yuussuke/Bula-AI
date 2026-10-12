/* Offline explicit human mapping. No fetch, model, retrieval or automatic approval. */
(() => {
  "use strict";
  const checks = ["document_identity", "variant_equivalence", "semantic_support", "local_scope", "necessary_qualifiers", "required_information", "table_relationships"];
  const labels = {document_identity: "PDF-alvo e apresentação", variant_equivalence: "Equivalência scoped/cross", semantic_support: "Suporte semântico", local_scope: "Contexto e população", necessary_qualifiers: "Qualificadores indispensáveis", required_information: "Informação necessária", table_relationships: "Relações da tabela"};
  const same = (first, second) => JSON.stringify(first.slice().sort()) === JSON.stringify(second.slice().sort());
  function summarize(payload, events) {
    const latest = new Map(events.map(event => [event.question_id, event]));
    const result = {total: payload.cases.length, human_reviewed: latest.size, approved: 0, rejected: 0, pending: payload.cases.length - latest.size, with_doubts: 0};
    for (const event of latest.values()) {result[event.decision] += 1; if (Object.values(event.checks).includes("doubt")) result.with_doubts += 1;}
    return result;
  }
  function validateEvent(payload, event) {
    const record = payload.cases.find(record => record.question_id === event.question_id);
    const fields = ["question_id", "record_sha256", "input_sha256", "package_sha256", "reviewer_id", "reviewed_at", "decision", "checks", "references", "justification"];
    if (!record || !same(Object.keys(event), fields) || event.package_sha256 !== payload.package_sha256 || event.record_sha256 !== record.record_sha256 || event.input_sha256 !== record.mapping.input_sha256) throw new Error("Registro, versão ou snapshot incompatível.");
    if (!event.reviewer_id?.trim() || !event.justification?.trim() || Number.isNaN(Date.parse(event.reviewed_at)) || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(event.reviewed_at)) throw new Error("Informe revisor, justificativa e data com fuso.");
    if (!["approved", "rejected", "pending"].includes(event.decision) || !same(Object.keys(event.checks), checks)) throw new Error("Decisão ou checklist incompleto.");
    for (const [key, value] of Object.entries(event.checks)) if (!["yes", "no", "doubt", "not_applicable"].includes(value) || (value === "not_applicable" && key !== "table_relationships")) throw new Error("Preencha todos os itens de conferência.");
    if (!Array.isArray(event.references) || !same(event.references.map(reference => reference.reference_id), record.references.map(reference => reference.reference_id))) throw new Error("Todas as referências precisam ser examinadas.");
    for (const reference of event.references) {
      if (!same(Object.keys(reference), ["reference_id", "chunk_ids", "status", "rationale"]) || !reference.rationale?.trim() || !Array.isArray(reference.chunk_ids) || new Set(reference.chunk_ids).size !== reference.chunk_ids.length || !reference.chunk_ids.every(id => record.document_chunk_ids.includes(id))) throw new Error("Justificativa, IDs ou documento inválidos na referência.");
      if (!["complete", "partial", "absent", "excluded_complementary"].includes(reference.status)) throw new Error("Informe o resultado de cada referência.");
      if (["complete", "partial"].includes(reference.status) !== (reference.chunk_ids.length > 0)) throw new Error("Referência com suporte exige IDs. Ausente/complementar excluída não recebe IDs.");
    }
    if (event.decision === "approved") {
      if (!Object.values(event.checks).every(value => ["yes", "not_applicable"].includes(value)) || !event.references.every(reference => ["complete", "excluded_complementary"].includes(reference.status)) || !event.references.some(reference => reference.status === "complete")) throw new Error("Não aprove com dúvidas, falhas ou suporte incompleto.");
      if (record.risk_flags.includes("table") && event.checks.table_relationships !== "yes") throw new Error("A tabela exige conferência explícita das relações.");
    }
    return event;
  }
  function orderCases(cases) {
    const priority = {absent: 0, partial: 1, ambiguous: 2, complete: 3};
    return cases.slice().sort((first, second) => priority[first.mapping.status] - priority[second.mapping.status] || first.question_id.localeCompare(second.question_id));
  }
  function quickProposal(record) {
    if (record.mapping.status !== "complete") return null;
    const proposal = [];
    for (const reference of record.references) {
      const full = record.candidates[reference.reference_id].filter(candidate => candidate.token_coverage === 1 && candidate.source_role === "source_text" && ["literal_token_sequence", "adjacent_literal_token_sequence"].includes(candidate.method));
      if (full.length !== 1) return null;
      proposal.push({reference_id: reference.reference_id, chunk_ids: full[0].chunk_ids.slice()});
    }
    return proposal.length ? proposal : null;
  }
  function quickEvent(payload, record, reviewer) {
    const proposal = quickProposal(record);
    if (!proposal) throw new Error("Este caso exige revisão detalhada.");
    // Called only by the explicit per-record approval button, never on render.
    return validateEvent(payload, {question_id: record.question_id, record_sha256: record.record_sha256, input_sha256: record.mapping.input_sha256, package_sha256: payload.package_sha256, reviewer_id: reviewer.trim(), reviewed_at: new Date().toISOString(), decision: "approved", checks: Object.fromEntries(checks.map(key => [key, key === "table_relationships" && !record.risk_flags.includes("table") ? "not_applicable" : "yes"])), references: proposal.map(reference => ({...reference, status: "complete", rationale: "Aprovação rápida explícita: conferi a comparação textual, o contexto e os qualificadores desta associação."})), justification: "Revisão rápida com confirmação humana conjunta de identidade/apresentação, variantes, suporte, contexto, qualificadores, informação necessária e relações de tabela quando aplicáveis."});
  }
  if (typeof module !== "undefined" && module.exports) {module.exports = {summarize, validateEvent, orderCases, quickProposal, quickEvent}; return;}
  const payload = JSON.parse(document.getElementById("payload").textContent);
  const reviewCases = orderCases(payload.cases);
  let events = [], dirty = false, unexported = false;
  const navigation = document.getElementById("navigation");
  const node = (tag, text, parent) => {const element = document.createElement(tag); element.textContent = text; parent.append(element); return element;};
  const message = text => {document.getElementById("message").textContent = text;};
  const refresh = () => {const count = summarize(payload, events); document.getElementById("summary").textContent = `${navigation.selectedIndex + 1}/${count.total} · ${count.approved} aprovados · ${count.pending} pendentes · ${count.rejected} rejeitados · ${count.with_doubts} com dúvidas`;};
  const priorityCount = reviewCases.filter(record => record.mapping.status !== "complete").length;
  document.getElementById("queue-note").textContent = `${priorityCount} prioritários primeiro · ${reviewCases.length - priorityCount} com revisão rápida · nenhuma decisão automática`;
  for (const record of reviewCases) node("option", `${record.mapping.status === "complete" ? "Rápida" : "Prioritário"} · ${record.question_id} — ${record.medication}`, navigation).value = record.question_id;
  function commitEvent(event, shouldAdvance) {
    events.push(validateEvent(payload, event)); dirty = false; unexported = true; refresh();
    if (shouldAdvance) {navigation.selectedIndex = Math.min(reviewCases.length - 1, navigation.selectedIndex + 1); currentIndex = navigation.selectedIndex; render();}
    message("Decisão salva por sua ação. Exporte antes de fechar.");
  }
  function renderQuick(record, latest, root) {
    const proposal = quickProposal(record);
    if (!proposal) return false;
    const panel = node("section", "", root); panel.className = "panel quick-panel";
    node("h3", "Revisão rápida — proposta ainda não aprovada", panel);
    node("p", record.question_scoped, panel).className = "question";
    node("small", `Cross-bula: ${record.question_cross_bula}`, panel);
    const essential = node("div", "", panel); essential.className = "essential";
    node("strong", "Indispensável: ", essential); node("span", record.human_question_annotation.required_information || record.expected_information, essential);
    const qualifiers = node("ul", "", essential); for (const qualifier of record.required_qualifiers) node("li", qualifier, qualifiers);
    for (const selected of proposal) {
      const reference = record.references.find(reference => reference.reference_id === selected.reference_id);
      const row = node("div", "", panel); row.className = "comparison";
      const original = node("section", "", row); node("strong", `${reference.reference_id} · referência original · p. ${reference.pdf_page}`, original);
      const link = node("a", " Abrir página do PDF ↗", original); link.href = `${record.pdf_link}#page=${reference.pdf_page}`; link.target = "_blank"; link.rel = "noopener";
      node("small", reference.section, original); node("blockquote", reference.quote, original);
      const indexed = node("section", "", row); node("strong", "Chunks propostos — texto original", indexed);
      for (const id of selected.chunk_ids) {
        const chunk = payload.chunk_catalog[id];
        node("small", `#${chunk.index} · ${chunk.section_title} · ${chunk.parser_version} · ${id}`, indexed);
        if (chunk.metadata?.fallback_reason) node("small", `Origem fallback: ${chunk.metadata.fallback_reason}`, indexed).className = "risk";
        const pre = node("pre", "", indexed);
        const start = chunk.text.toLocaleLowerCase("pt-BR").indexOf(reference.quote.toLocaleLowerCase("pt-BR"));
        if (start >= 0) {pre.append(document.createTextNode(chunk.text.slice(0, start))); node("mark", chunk.text.slice(start, start + reference.quote.length), pre); pre.append(document.createTextNode(chunk.text.slice(start + reference.quote.length)));}
        else {pre.textContent = chunk.text; node("small", "Correspondência após normalização de formatação; confira o texto integral.", indexed);}
      }
    }
    if (record.risk_flags.includes("table")) node("p", "Tabela: confira cabeçalhos, unidades e associação entre células antes de aprovar.", panel).className = "risk";
    node("p", "O botão confirma conjuntamente: PDF/apresentação, equivalência das perguntas, suporte e contexto, qualificadores, informação necessária e tabela quando houver. Não declara leitura do PDF completo.", panel).className = "muted";
    const error = node("p", "", panel); error.className = "error"; error.setAttribute("role", "alert");
    const approve = node("button", "Conferi evidências e qualificadores — aprovar e próxima", panel); approve.className = "primary";
    if (latest) {approve.disabled = true; node("p", `Já existe decisão ${latest.decision}. Use a revisão detalhada para modificá-la; o histórico será preservado.`, panel);}
    approve.onclick = () => {try {if (dirty) throw new Error("Há edições detalhadas não salvas. Salve-as ou descarte antes da aprovação rápida."); commitEvent(quickEvent(payload, record, document.getElementById("reviewer").value), true);} catch (failure) {error.textContent = failure.message;}};
    return true;
  }
  function render() {
    const record = reviewCases[navigation.selectedIndex];
    const latest = events.filter(event => event.question_id === record.question_id).at(-1);
    const root = document.getElementById("record"); root.replaceChildren();
    node("h2", `${record.question_id} — ${record.medication}`, root);
    node("p", `Corpus ${record.corpus_id} · PDF ${record.document_id} · revisão original ${record.source_revision} / derivada ${record.derived_revision} · lexical: ${record.mapping.status}`, root);
    let detailedParent = root;
    if (renderQuick(record, latest, root)) {detailedParent = node("details", "", root); detailedParent.className = "detailed-review"; node("summary", "Revisão detalhada / ajustar os IDs / registrar ressalva", detailedParent);}
    else node("p", "Prioritário: confira alternativas, trechos incompletos ou ausentes. Não há aprovação rápida neste caso.", root).className = "risk";
    const grid = node("div", "", detailedParent); grid.className = "grid";
    const info = node("section", "", grid); info.className = "panel";
    const decisions = node("section", "", grid); decisions.className = "panel";
    const link = (text, page, parent) => {const anchor = node("a", text, parent); anchor.href = record.pdf_link + (page ? `#page=${page}` : ""); anchor.target = "_blank"; anchor.rel = "noopener";};
    link("Abrir PDF original completo ↗", null, info);
    node("h3", "Pergunta por bula", info); node("p", record.question_scoped, info);
    node("h3", "Pergunta cross-bula", info); node("p", record.question_cross_bula, info);
    node("h3", "Informação esperada original", info); node("p", record.expected_information, info);
    node("h3", "Indispensável anotado na revisão da pergunta", info); node("p", record.human_question_annotation.required_information || "Não preenchido", info);
    if (record.human_question_annotation.complementary_information) {node("h3", "Complementar", info); node("p", record.human_question_annotation.complementary_information, info);}
    node("h3", "Qualificadores", info); node("p", record.required_qualifiers.join("; "), info);
    node("p", `Alertas: ${record.risk_flags.join(", ")}`, info).className = "risk";
    if (record.authorship_flags.length) node("p", `Alertas de autoria: ${JSON.stringify(record.authorship_flags)}`, info);
    node("small", `Registro ${record.record_sha256}\nPDF ${record.pdf_sha256}\nEntrada ${record.mapping.input_sha256}`, info);
    const referenceControls = [];
    const select = (title, choices, parent, current = "") => {const control = node("select", "", node("label", title, parent)); control.setAttribute("aria-label", title); node("option", "Escolha", control).value = ""; for (const [value, label] of choices) node("option", label, control).value = value; control.value = current; return control;};
    for (const reference of record.references) {
      const section = node("section", "", info); section.className = "ref";
      node("h3", `${reference.reference_id} · página física ${reference.pdf_page} · ${reference.section}`, section);
      if (reference.source_region) node("p", reference.source_region, section);
      link("Conferir página original ↗", reference.pdf_page, section);
      node("blockquote", reference.quote, section);
      const candidates = record.candidates[reference.reference_id];
      const diagnostic = record.documentary_checks.find(check => check.reference_id === reference.reference_id);
      node("small", `Conferência textual: ${diagnostic.diagnostic}. Apenas metadados não equivalem a prova documental; a página do chunk não foi inferida.`, section);
      for (const candidate of candidates) node("small", `${candidate.method} · cobertura textual ${(candidate.token_coverage * 100).toFixed(0)}% · seção concordante: ${candidate.section_agreement ? "sim" : "não"} · ${candidate.rationale}`, section);
      if (!candidates.length) node("p", "Sem candidato automático. Examine os demais chunks do PDF antes de concluir ausência.", section).className = "risk";
      const previous = latest?.references.find(row => row.reference_id === reference.reference_id);
      const boxes = new Map();
      function showChunk(id, parent) {
        if (boxes.has(id)) return;
        const chunk = payload.chunk_catalog[id];
        const card = node("div", "", parent); card.className = "chunk";
        const label = node("label", "", card); const box = node("input", "", label); box.type = "checkbox"; box.checked = previous?.chunk_ids.includes(id) || false; box.setAttribute("aria-label", `${reference.reference_id}: ${id}`);
        node("span", `Selecionar #${chunk.index} — ${chunk.section_title}`, label);
        node("small", `${id}\n${chunk.parser_version} · ${chunk.method} · ${chunk.metadata?.content_role || "papel não registrado"}\nPágina do chunk: não registrada; conferir no PDF.`, card);
        if (chunk.metadata?.fallback_reason) node("small", `Fallback determinístico: ${chunk.metadata.fallback_reason}. Motivo da substituição do chunking primário; não comprova perda de evidência neste chunk.`, card).className = "risk";
        node("pre", chunk.text, card); boxes.set(id, box);
        const context = node("details", "", card); node("summary", "Contexto vizinho (não selecionado automaticamente)", context);
        for (const offset of [-1, 1]) {const neighborId = record.document_chunk_ids[chunk.index + offset]; if (neighborId) {const neighbor = payload.chunk_catalog[neighborId]; node("small", `#${neighbor.index} · ${neighborId} · ${neighbor.section_title}`, context); node("pre", neighbor.text, context);}}
      }
      for (const id of new Set(candidates.flatMap(candidate => candidate.chunk_ids))) showChunk(id, section);
      const others = node("details", "", section); node("summary", "Inspecionar todos os chunks do PDF / selecionar contexto adicional", others);
      for (const id of record.document_chunk_ids) showChunk(id, others);
      const status = select("Resultado humano desta referência", [["complete", "Suporte completo"], ["partial", "Suporte parcial"], ["absent", "Sem suporte localizado"], ["excluded_complementary", "Complementar: excluir com justificativa"]], section, previous?.status);
      const rationale = node("textarea", "", node("label", "Justificativa desta associação / limitação", section)); rationale.setAttribute("aria-label", "Justificativa desta associação / limitação"); rationale.value = previous?.rationale || "";
      referenceControls.push({reference, boxes, status, rationale});
    }
    node("h3", "Conferência humana do mapeamento", decisions);
    const checkGrid = node("div", "", decisions); checkGrid.className = "checks";
    const controls = {};
    for (const key of checks) controls[key] = select(labels[key], [["yes", "Sim"], ["no", "Não"], ["doubt", "Dúvida"], ...(key === "table_relationships" ? [["not_applicable", "Sem tabela aplicável"]] : [])], checkGrid, latest?.checks[key]);
    const decision = select("Decisão do mapeamento", [["approved", "Aprovar"], ["pending", "Pendente"], ["rejected", "Rejeitar"]], decisions, latest?.decision);
    const justification = node("textarea", "", node("label", "Justificativa geral", decisions)); justification.setAttribute("aria-label", "Justificativa geral"); justification.value = latest?.justification || "";
    const status = node("p", latest ? `${latest.decision} — evento humano importado/salvo` : "Pendente — sem decisão humana", decisions); status.id = "record-status";
    const error = node("p", "", decisions); error.className = "error"; error.setAttribute("role", "alert");
    const save = shouldAdvance => {
      try {
        const event = {question_id: record.question_id, record_sha256: record.record_sha256, input_sha256: record.mapping.input_sha256, package_sha256: payload.package_sha256, reviewer_id: document.getElementById("reviewer").value.trim(), reviewed_at: new Date().toISOString(), decision: decision.value, checks: Object.fromEntries(checks.map(key => [key, controls[key].value])), references: referenceControls.map(control => ({reference_id: control.reference.reference_id, chunk_ids: [...control.boxes].filter(([, box]) => box.checked).map(([id]) => id), status: control.status.value, rationale: control.rationale.value})), justification: justification.value};
        commitEvent(event, shouldAdvance); error.textContent = ""; status.textContent = `${event.decision} — salvo; exporte para guardar`;
      } catch (failure) {error.textContent = failure.message; message("Não salvo: confira os campos da revisão.");}
    };
    node("button", "Salvar decisão", decisions).onclick = () => save(false);
    node("button", "Salvar e próxima →", decisions).onclick = () => save(true); decisions.lastElementChild.className = "primary";
    root.querySelectorAll("input,select,textarea").forEach(control => control.addEventListener("input", () => {dirty = true;}));
    refresh(); window.scrollTo({top: 0, behavior: "instant"});
  }
  let currentIndex = 0;
  function navigate(index) {if (dirty && !window.confirm("Há campos ainda não salvos. Descartar essas edições?")) {navigation.selectedIndex = currentIndex; return;} navigation.selectedIndex = index; currentIndex = index; dirty = false; render();}
  navigation.onchange = () => navigate(navigation.selectedIndex);
  document.getElementById("previous").onclick = () => navigate(Math.max(0, currentIndex - 1));
  document.getElementById("next").onclick = () => navigate(Math.min(reviewCases.length - 1, currentIndex + 1));
  document.getElementById("export").onclick = () => {const exported = {schema_version: 1, package_sha256: payload.package_sha256, events, summary: summarize(payload, events)}; const url = URL.createObjectURL(new Blob([JSON.stringify(exported, null, 2)], {type: "application/json"})); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `mapping-decisions-${payload.package_sha256.slice(0, 12)}-${Date.now()}.json`; anchor.click(); URL.revokeObjectURL(url); unexported = false; message(dirty ? "Histórico exportado; existem campos não salvos." : "Histórico exportado.");};
  document.getElementById("import").onchange = async event => {
    try {if (dirty) throw new Error("Salve ou descarte as edições antes de importar."); const imported = JSON.parse(await event.target.files[0].text()); if (imported.schema_version !== 1 || imported.package_sha256 !== payload.package_sha256 || !Array.isArray(imported.events)) throw new Error("Exportação de outro pacote."); imported.events.forEach(item => validateEvent(payload, item)); if (JSON.stringify(imported.events.slice(0, events.length)) !== JSON.stringify(events) || JSON.stringify(imported.summary) !== JSON.stringify(summarize(payload, imported.events))) throw new Error("Não é permitido remover histórico ou alterar contagens."); events = imported.events; unexported = false; render(); message("Histórico importado; nenhuma nova decisão foi criada.");} catch (failure) {message(failure.message);}
  };
  window.addEventListener("beforeunload", event => {if (dirty || unexported) {event.preventDefault(); event.returnValue = "";}});
  render();
})();
