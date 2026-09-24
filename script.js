const form = document.querySelector("#broadcast-form");
const topicInput = document.querySelector("#topic");
const chips = document.querySelectorAll("[data-topic]");
const panel = document.querySelector("#generation-panel");
const steps = [...document.querySelectorAll(".step")];
const resultPanel = document.querySelector("#result-panel");
const resultTitle = document.querySelector("#result-title");
const scriptPreview = document.querySelector("#script-preview");
const musicList = document.querySelector("#music-list");
const playButton = document.querySelector(".play-button");
const audioTime = document.querySelector(".audio-time");

const stepLabels = ["대본 작성 중", "TTS 변환 중", "음악 탐색 중", "믹싱 완료"];
const doneLabels = ["대본 완료", "음성 완료", "추천 완료", "완성"];
let activeTimers = [];
let playing = false;

const demoMusic = [
  { title: "Midnight Seoul Keys", mood: "lo-fi jazz" },
  { title: "Warm City Drive", mood: "future pop" },
  { title: "Soft Newsroom Pulse", mood: "ambient beat" },
];

chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    topicInput.value = chip.dataset.topic;
    topicInput.focus();
  });
});

function clearTimers() {
  activeTimers.forEach((timer) => window.clearTimeout(timer));
  activeTimers = [];
}

function resetDemo() {
  clearTimers();
  resultPanel.classList.remove("show");
  steps.forEach((step) => {
    step.classList.remove("active", "done");
    step.querySelector("small").textContent = "대기 중";
  });
  playing = false;
  playButton.textContent = "▶";
  audioTime.textContent = "00:00";
}

function buildScript(topic) {
  return [
    `안녕하세요, On-AI-r의 AI DJ 루나입니다. 오늘의 방송 주제는 "${topic}"입니다.`,
    "먼저 핵심 내용을 쉽고 짧게 정리하고, 이어서 지금 듣기 좋은 분위기의 음악을 함께 추천해드릴게요.",
    "오늘의 포인트는 정보는 가볍게, 분위기는 선명하게입니다. 잠시 뒤 추천 트랙과 함께 완성된 AI 방송으로 이어집니다.",
  ].join(" ");
}

function renderResult(topic) {
  resultTitle.textContent = `${topic} 방송`;
  scriptPreview.textContent = buildScript(topic);
  musicList.innerHTML = demoMusic
    .map((music) => `<li><strong>${music.title}</strong><em>${music.mood}</em></li>`)
    .join("");
  resultPanel.classList.add("show");
}

function runStep(index, topic) {
  steps.forEach((step, stepIndex) => {
    step.classList.toggle("active", stepIndex === index);
    step.classList.toggle("done", stepIndex < index);
    const label = step.querySelector("small");
    if (stepIndex < index) label.textContent = doneLabels[stepIndex];
    if (stepIndex === index) label.textContent = stepLabels[stepIndex];
    if (stepIndex > index) label.textContent = "대기 중";
  });

  if (index === steps.length - 1) {
    activeTimers.push(
      window.setTimeout(() => {
        steps[index].querySelector("small").textContent = doneLabels[index];
        renderResult(topic);
      }, 650),
    );
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim() || "오늘의 서울 날씨와 주말 나들이 코스";
  topicInput.value = topic;
  resetDemo();
  panel.classList.add("show");

  steps.forEach((_, index) => {
    activeTimers.push(
      window.setTimeout(() => {
        runStep(index, topic);
      }, index * 780),
    );
  });
});

playButton.addEventListener("click", () => {
  playing = !playing;
  playButton.textContent = playing ? "Ⅱ" : "▶";
  audioTime.textContent = playing ? "00:17" : "00:00";
});
