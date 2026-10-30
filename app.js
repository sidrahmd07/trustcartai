const form = document.getElementById("chatForm");
const input = document.getElementById("userInput");
const chatArea = document.getElementById("chatArea");
const newChat = document.getElementById("newChat");
let conversationId = crypto.randomUUID();

const LABELS = {
  answer: ["verified", "✓ VERIFIED FROM CATALOGUE / POLICY"],
  clarify: ["clarify", "? CLARIFICATION NEEDED"],
  refuse: ["refuse", "! NOT IN CATALOGUE — REFUSED"],
};

function addMessage(role, text, result) {
  const empty = document.getElementById("emptyState");
  if (empty) empty.remove();
  const row = document.createElement("div");
  row.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "assistant" ? "TC" : "YOU";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (result) {
    const [cls, label] = LABELS[result.action];
    const status = document.createElement("div");
    status.className = `status ${cls}`;
    status.textContent = label;
    bubble.appendChild(status);
  }
  const content = document.createElement("div");
  content.textContent = text;
  bubble.appendChild(content);
  if (result) {
    const cites = [...result.cited_product_ids, ...result.cited_policy_sections.map(s => `policy ${s}`)];
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${cites.length ? "Sources: " + cites.join(", ") + " · " : ""}${result.latency_ms} ms · ${result.tokens_in + result.tokens_out} LLM tokens`;
    bubble.appendChild(meta);
  }
  row.append(avatar, bubble);
  chatArea.appendChild(row);
  chatArea.scrollTop = chatArea.scrollHeight;
}

async function ask(query) {
  addMessage("user", query);
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, conversation_id: conversationId }),
  });
  if (!response.ok) throw new Error("Server returned an error");
  const result = await response.json();
  addMessage("assistant", result.answer_text, result);
}

async function sendMessage(query, followUps = []) {
  const trimmed = query.trim();
  if (!trimmed) return;
  input.value = "";
  try {
    await ask(trimmed);
    for (const next of followUps) await ask(next);
  } catch (error) {
    addMessage("assistant", "I can't reach the local server. Start it with: python server.py", null);
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(input.value);
});
document.querySelectorAll("[data-query]").forEach(button => {
  button.addEventListener("click", () => {
    const followUps = button.dataset.multi ? button.dataset.multi.split("|") : [];
    if (followUps.length) conversationId = crypto.randomUUID();
    sendMessage(button.dataset.query, followUps);
  });
});
newChat.addEventListener("click", () => {
  conversationId = crypto.randomUUID();
  chatArea.innerHTML = '<div class="empty-state" id="emptyState"><h3>What are you looking for?</h3><p>Ask about a product, a price, stock or the store policy.</p></div>';
});
