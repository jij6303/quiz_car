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

// ── 진행도 (10칸) ────────────────────────────
const MARK_CLASS = { "🟩": "m2", "🟨": "m1", "⬛": "m0" };

function renderProgress(marks, total, current) {
  const ol = $("progress");
  ol.innerHTML = "";
  for (let i = 0; i < total; i++) {
    const li = document.createElement("li");
    if (i < marks.length) li.className = MARK_CLASS[marks[i]];
    else if (i === current - 1) li.className = "current";
    ol.appendChild(li);
  }
}

async function newQuestion() {
  const res = await fetch("/api/new", { method: "POST" });
  if (res.status === 409) return showSummary(); // 이번 판이 이미 끝남
  if (!res.ok) throw new Error(`/api/new ${res.status}`);
  const q = await res.json();

  Object.assign(state, {
    clueCount: q.clue_count, clues: q.clues, model: null, year: null, answered: false, nonce: Date.now(),
  });
  $("round").textContent = `${q.round} / ${q.total}`;
  $("score").textContent = q.score;
  renderProgress(q.marks, q.total, q.round);
  renderChoices("model-choices", q.models, "model");
  renderChoices("year-choices", q.years, "year");
  $("submit-btn").disabled = true;
  $("submit-btn").hidden = false;
  $("result").hidden = true;
  $("summary").hidden = true;
  $("game").hidden = false;
  showClue(q.clues.length - 1);
}

// ── 결과 카드 ────────────────────────────────
async function showSummary() {
  const res = await fetch("/api/summary");
  if (!res.ok) return startGame();
  const s = await res.json();
  state.share = s.share;

  $("sum-rank").textContent = s.rank.name;
  $("sum-comment").textContent = s.rank.comment;
  $("sum-score").textContent = s.score;
  $("sum-max").textContent = `/ ${s.max_score}점`;
  $("sum-marks").textContent = s.marks;
  $("sum-model").textContent = `${s.model_correct} / ${s.played}`;
  $("sum-year").textContent = `${s.year_correct} / ${s.played}`;
  $("sum-perfect").textContent = `${s.perfect}`;
  $("sum-clues").textContent = `${s.avg_clues}개`;
  $("copy-status").textContent = "";

  const marks = [...s.marks]; // 이모지는 문자열 인덱스로 자르면 깨지므로 배열로
  const ol = $("sum-rows");
  ol.innerHTML = "";
  s.rows.forEach((r, i) => {
    const li = document.createElement("li");
    const mark = document.createElement("span");
    mark.className = "row-mark";
    mark.textContent = marks[i];
    const car = document.createElement("div");
    car.className = "row-car";
    const b = document.createElement("b");
    b.textContent = `${r.model} · ${r.year}`;
    const small = document.createElement("small");
    const mine = r.model_ok && r.year_ok ? "둘 다 정답"
      : `내 답: ${r.picked_model || "-"} · ${r.picked_year || "-"}`;
    small.textContent = `${mine} · 단서 ${r.clues}개`;
    car.append(b, small);
    const pts = document.createElement("span");
    pts.className = "row-pts";
    pts.textContent = `+${r.points}`;
    li.append(mark, car, pts);
    ol.appendChild(li);
  });

  renderProgress(marks, s.played, 0);
  $("round").textContent = "끝";
  $("score").textContent = s.score;
  $("game").hidden = true;
  $("summary").hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function startGame() {
  await api("/api/game");
  await newQuestion(); // 진행 중인 판이 있으면 이어서, 끝났으면 결과 카드
  window.scrollTo({ top: 0, behavior: "smooth" });
}

$("again-btn").onclick = startGame;

$("copy-btn").onclick = async () => {
  const text = `${state.share}
${location.href}`;
  try {
    await navigator.clipboard.writeText(text);
    $("copy-status").textContent = "결과를 복사했어요. 친구에게 붙여넣어 보내세요.";
  } catch {
    $("copy-status").textContent = text;
  }
};

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
  renderProgress(r.marks, r.total, 0);
  $("next-btn").textContent = r.game_over ? "결과 보기" : "다음 문제";
  state.gameOver = r.game_over;

  state.photos = r.photos;
  renderPhotoTabs();
  showPhoto(0);

  $("submit-btn").hidden = true;
  $("result").hidden = false;
  $("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
};

$("next-btn").onclick = () => (state.gameOver ? showSummary() : newQuestion());

newQuestion(); // 진행 중인 판이 있으면 이어서, 끝났으면 결과 카드
