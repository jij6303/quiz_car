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

// 정답 공개: 원본 전체 사진 + 단서 영역 표시
function showPhoto(i) {
  const p = state.photos[i];
  $("photo-img").src = `/api/photo/${i}?v=${state.nonce}`;

  const boxes = $("photo-boxes");
  boxes.innerHTML = "";
  p.clues.forEach((c) => {
    const [x0, y0, x1, y1] = c.box;
    const s = document.createElement("span");
    s.dataset.n = c.number;
    s.title = `단서 ${c.number} · ${c.label}`;
    Object.assign(s.style, {
      left: `${x0 * 100}%`, top: `${y0 * 100}%`,
      width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%`,
    });
    boxes.appendChild(s);
  });

  const credit = $("photo-credit");
  credit.innerHTML = "";
  const a = document.createElement("a");
  a.href = p.source.page;
  a.target = "_blank";
  a.rel = "noopener";
  a.textContent = p.source.author || "작성자 미상";
  credit.append("사진: ", a, ` · ${p.source.license}`);

  $("photo-tabs").querySelectorAll("button").forEach((b, j) => b.classList.toggle("active", j === i));
}

function renderPhotoTabs() {
  const tabs = $("photo-tabs");
  tabs.innerHTML = "";
  if (state.photos.length < 2) return;
  state.photos.forEach((_, i) => {
    const b = document.createElement("button");
    b.textContent = `사진 ${i + 1}`;
    b.onclick = () => showPhoto(i);
    tabs.appendChild(b);
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

  state.photos = r.photos;
  renderPhotoTabs();
  showPhoto(0);

  $("submit-btn").hidden = true;
  $("result").hidden = false;
  $("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
};

$("next-btn").onclick = newQuestion;

newQuestion();
