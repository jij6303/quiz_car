const $ = (id) => document.getElementById(id);

const state = { clueCount: 0, clues: [], current: 0, model: null, year: null, answered: false, nonce: 0 };

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

function showClue(i) {
  state.current = i;
  const img = $("clue-img");
  img.classList.add("loading");
  img.onload = () => img.classList.remove("loading");
  img.src = `/api/clue/${i}?v=${state.nonce}`;
  $("clue-label").textContent = `단서 ${i + 1} · ${state.clues[i].label}`;
  renderTabs();
}

function renderTabs() {
  const tabs = $("clue-tabs");
  tabs.innerHTML = "";
  state.clues.forEach((c, i) => {
    const b = document.createElement("button");
    b.textContent = `단서 ${i + 1}`;
    b.className = i === state.current ? "active" : "";
    b.onclick = () => showClue(i);
    tabs.appendChild(b);
  });
  $("hint-btn").disabled = state.answered || state.clues.length >= state.clueCount;
}

function renderChoices(containerId, items, key) {
  const box = $(containerId);
  box.innerHTML = "";
  items.forEach((label) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.dataset.value = label;
    b.onclick = () => {
      if (state.answered) return;
      state[key] = label;
      box.querySelectorAll("button").forEach((x) => x.classList.toggle("selected", x === b));
      $("submit-btn").disabled = !(state.model && state.year);
    };
    box.appendChild(b);
  });
}

function markChoices(containerId, answer) {
  $(containerId).querySelectorAll("button").forEach((b) => {
    b.disabled = true;
    if (b.dataset.value === answer) b.classList.add("correct");
    else if (b.classList.contains("selected")) b.classList.add("wrong");
  });
}

async function newQuestion() {
  const q = await api("/api/new");
  Object.assign(state, {
    clueCount: q.clue_count, clues: q.clues, model: null, year: null, answered: false, nonce: Date.now(),
  });
  $("round").textContent = `${q.round}`;
  renderChoices("model-choices", q.models, "model");
  renderChoices("year-choices", q.years, "year");
  $("submit-btn").disabled = true;
  $("submit-btn").hidden = false;
  $("result").hidden = true;
  showClue(0);
}

$("hint-btn").onclick = async () => {
  const r = await api("/api/hint");
  state.clues = r.clues;
  showClue(state.clues.length - 1);
};

$("submit-btn").onclick = async () => {
  const r = await api("/api/answer", { model: state.model, year: state.year });
  state.answered = true;
  state.clues = r.clues;
  renderTabs();
  markChoices("model-choices", r.answer_model);
  markChoices("year-choices", r.answer_year);

  const title = r.model_ok && r.year_ok ? "완벽해요! 🎉"
    : r.model_ok ? "모델은 맞혔어요! 연식이 아쉽네요"
    : r.year_ok ? "연식만 맞혔어요"
    : "아쉬워요 😢";
  $("result-title").textContent = `${title}  +${r.points}점`;
  $("answer-model").textContent = r.answer_model;
  $("answer-year").textContent = r.answer_year;
  $("score").textContent = r.score;

  const list = $("credit-list");
  list.innerHTML = "";
  r.credits.forEach((c) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = c.page;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = c.title.replace(/^File:/, "");
    li.append(a, ` — ${c.author || "작성자 미상"}, ${c.license}`);
    list.appendChild(li);
  });

  $("submit-btn").hidden = true;
  $("result").hidden = false;
  $("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
};

$("next-btn").onclick = newQuestion;

newQuestion();
