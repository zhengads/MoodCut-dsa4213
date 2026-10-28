"use strict";
const tabs = document.getElementById("stories");
const players = document.getElementById("players");
const panel = document.getElementById("comparison");
let stories = [];
function showStory(number) {
  const story = stories.find(item => item.number === number) || stories[0];
  for (const video of players.querySelectorAll("video")) video.pause();
  players.replaceChildren();
  document.getElementById("story-title").textContent = `${story.number}. ${story.title}`;
  document.getElementById("story-meta").textContent = `${story.emotion} · ${story.characters.join(" & ")} · ${story.language}`;
  document.getElementById("story-brief").textContent = story.brief;
  panel.setAttribute("aria-labelledby", `story-${story.number}`);
  for (const tab of tabs.children) {
    const selected = tab.dataset.number === story.number;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  }
  for (const condition of story.conditions) {
    const card = document.createElement("article");
    card.className = "condition"; card.dataset.condition = condition.id;
    const header = document.createElement("header");
    const title = document.createElement("h3"); title.textContent = condition.label; header.append(title);
    const stage = document.createElement("div"); stage.className = "video-stage";
    const video = document.createElement("video");
    video.controls = true; video.playsInline = true; video.preload = "metadata"; video.src = condition.video;
    video.setAttribute("aria-label", `${story.number}: ${condition.label}`);
    video.addEventListener("play", () => {
      for (const other of players.querySelectorAll("video")) if (other !== video) other.pause();
    });
    const error = document.createElement("p"); error.className = "error"; error.hidden = true;
    error.setAttribute("role", "alert");
    error.textContent = "This video could not be loaded. Please use the release download below.";
    video.addEventListener("error", () => { error.hidden = false; });
    stage.append(video);
    const note = document.createElement("p"); note.className = "video-note"; note.textContent = condition.note;
    card.append(header, stage, note, error); players.append(card);
  }
}
async function start() {
  const response = await fetch("data.json");
  if (!response.ok) throw new Error("Story data unavailable");
  stories = (await response.json()).scenarios;
  if (stories.length !== 12) throw new Error("Incomplete story catalog");
  for (const story of stories) {
    const button = document.createElement("button");
    button.type = "button"; button.id = `story-${story.number}`; button.dataset.number = story.number;
    button.setAttribute("role", "tab"); button.setAttribute("aria-controls", "comparison");
    button.setAttribute("aria-label", `${story.number}. ${story.title}: ${story.emotion}`);
    button.textContent = `${story.number} · ${story.emotion}`;
    button.addEventListener("click", () => {
      if (location.hash === `#${story.number}`) showStory(story.number);
      else location.hash = story.number;
    });
    tabs.append(button);
  }
  tabs.addEventListener("keydown", event => {
    const buttons = [...tabs.children]; const current = buttons.indexOf(document.activeElement);
    if (current < 0) return;
    let next;
    if (event.key === "ArrowRight") next = (current + 1) % buttons.length;
    else if (event.key === "ArrowLeft") next = (current + buttons.length - 1) % buttons.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = buttons.length - 1;
    else return;
    event.preventDefault(); buttons[next].focus(); buttons[next].click();
  });
  window.addEventListener("hashchange", () => showStory(location.hash.slice(1)));
  showStory(location.hash.slice(1));
}
start().catch(() => { document.getElementById("load-error").hidden = false; });
