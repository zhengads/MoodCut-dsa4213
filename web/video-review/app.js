"use strict";

const players = document.querySelector("#players");
const tabs = [...document.querySelectorAll("[data-experiment]")];
let experiments = [];
let currentId = null;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function pauseAll(except) {
  for (const video of players.querySelectorAll("video")) {
    if (video !== except) video.pause();
  }
}

function makeCondition(condition, baseline, speakerNames) {
  const card = element("article");
  card.className = "condition";
  card.dataset.condition = condition.id;
  const header = element("header");
  header.append(element("h2", condition.label), element("span", condition.status, "status"));
  const stage = element("div", undefined, "video-stage");
  if (condition.video) {
    const video = element("video");
    video.controls = true;
    video.preload = "auto";
    video.playsInline = true;
    video.src = condition.video;
    video.setAttribute("aria-label", condition.label + "原始视频，含原生音轨");
    video.append(element("p", "浏览器不支持视频播放，请使用下方原片存档链接。"));
    const play = element("button", undefined, "play-overlay");
    play.type = "button";
    play.setAttribute("aria-label", "播放" + condition.label);
    const playLabel = element("span", "▶ 播放");
    play.append(playLabel);
    const error = element("p", "视频暂时无法加载，请刷新，或从页面底部的原片存档下载。", "error");
    error.hidden = true;
    error.setAttribute("role", "alert");
    play.addEventListener("click", async () => {
      try {
        error.hidden = true;
        await video.play();
      } catch {
        error.hidden = false;
      }
    });
    video.addEventListener("play", () => {
      pauseAll(video);
      play.hidden = true;
    });
    video.addEventListener("pause", () => { play.hidden = false; });
    video.addEventListener("ended", () => {
      playLabel.textContent = "▶ 重播";
      play.hidden = false;
    });
    video.addEventListener("error", () => { error.hidden = false; });
    stage.append(video, play);
    card.append(header, stage, error);
  } else {
    stage.append(element("p", "未提交视频生成", "video-empty"));
    card.append(header, stage);
  }
  card.append(element("p", condition.note, "video-note"));
  const dialogue = element("div", undefined, "dialogue");
  for (const [index, line] of condition.dialogue.entries()) {
    const row = element("div", undefined, "line");
    const words = element("div");
    const original = baseline[index];
    if (original && original.text !== line.text) {
      words.append(element("del", original.text, "old-line"));
      const spoken = element("p", undefined, "spoken");
      spoken.append(element("mark", line.text, "changed"));
      words.append(spoken);
    } else {
      words.append(element("p", line.text, "spoken"));
    }
    row.append(element("span", speakerNames[line.character_id] || line.character_id, "speaker"), words);
    dialogue.append(row);
  }
  if (condition.id !== "baseline" && condition.dialogue.every((line, i) => line.text === baseline[i]?.text)) {
    dialogue.append(element("p", "台词与共同初稿相同", "unchanged"));
  }
  card.append(dialogue);
  return card;
}

function showExperiment(id) {
  const experiment = experiments.find(item => item.id === id) || experiments[0];
  if (!experiment || currentId === experiment.id) return;
  pauseAll();
  currentId = experiment.id;
  for (const tab of tabs) {
    const selected = tab.dataset.experiment === currentId;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  }
  document.querySelector("#comparison").setAttribute("aria-labelledby", "tab-" + currentId);
  document.querySelector("#experiment-description").textContent = experiment.description;
  document.querySelector("#story-title").textContent = experiment.title || "Anna 与 Elsa 的台词对照";
  document.querySelector("#story-intro").textContent = experiment.intro || "同一次还伞，看看台词修改落到表演里是什么样子。";
  document.querySelector("#scene-location").textContent = experiment.scene_location || "雨天的公交站";
  document.querySelector("#scene-tone").textContent = "目标氛围：" + (experiment.tone_label || "温暖、亲近");
  const speakerNames = experiment.speaker_names || {a: "Anna", b: "Elsa"};
  const baseline = experiment.conditions[0].dialogue;
  players.replaceChildren(...experiment.conditions.map(condition => makeCondition(condition, baseline, speakerNames)));
  document.querySelector("#observations").replaceChildren(...experiment.observations.map(text => element("li", text)));
  document.querySelector("#cost").textContent = "$" + experiment.cost;
  document.querySelector("#duration").textContent = experiment.duration || "请求 5 秒，原片约 5.26 秒";
  document.querySelector("#source-record").href = experiment.record;
  document.querySelector("#source-credit").textContent = experiment.source_credit || "角色参考来源：showlab/MovieAgent 固定版本的 FrozenII Anna / Elsa。图片及角色使用权仍未核清，署名不等于授权。";
  document.querySelector("#source-statement").href = experiment.source_statement_url || "https://github.com/zhengads/MoodCut-dsa4213/releases/download/pilot-anna-elsa-v3-20261024/SOURCE.md";
  const historicalArchive = "https://github.com/zhengads/MoodCut-dsa4213/releases/tag/pilot-anna-elsa-20261024";
  const archives = {global: historicalArchive, actors: historicalArchive,
    "v3-captured": "https://github.com/zhengads/MoodCut-dsa4213/releases/tag/pilot-anna-elsa-v3-20261024"};
  const archive = experiment.archive_url || archives[experiment.id];
  document.querySelector("#current-archive").hidden = !archive;
  if (archive) document.querySelector("#current-archive").href = archive;
  const unresolved = document.querySelector("#unresolved");
  unresolved.hidden = !experiment.unresolved;
  unresolved.open = false;
  const content = document.querySelector("#unresolved-content");
  content.replaceChildren();
  if (experiment.unresolved) {
    content.append(element("p", experiment.unresolved.summary));
    content.append(element("p", "编剧原始理由："));
    content.append(element("blockquote", experiment.unresolved.writerReason));
    content.append(element("p", "这条理由误指了说话人，也未证明较短的替代表述会超时。这里保留原话供人判断，不把意见记成已解决。"));
  }
}

for (const [index, tab] of tabs.entries()) {
  tab.addEventListener("click", () => {
    location.hash = tab.dataset.experiment;
    showExperiment(tab.dataset.experiment);
  });
  tab.addEventListener("keydown", event => {
    let target;
    if (event.key === "ArrowRight") target = tabs[(index + 1) % tabs.length];
    else if (event.key === "ArrowLeft") target = tabs[(index + tabs.length - 1) % tabs.length];
    else if (event.key === "Home") target = tabs[0];
    else if (event.key === "End") target = tabs[tabs.length - 1];
    if (target) {
      event.preventDefault();
      target.focus();
      target.click();
    }
  });
}
window.addEventListener("hashchange", () => {
  const id = location.hash.slice(1);
  if (experiments.some(experiment => experiment.id === id)) showExperiment(id);
});

fetch("data.json")
  .then(response => {
    if (!response.ok) throw new Error("Missing experiment records");
    return response.json();
  })
  .then(data => {
    experiments = data.experiments;
    showExperiment(location.hash.slice(1) || "s06");
  })
  .catch(() => {
    document.querySelector("#experiment-description").textContent = "实验记录未能载入。";
    const error = document.querySelector("#page-error");
    error.textContent = "请刷新页面，或前往仓库查看原始试跑记录与下载链接。";
    error.hidden = false;
  });
