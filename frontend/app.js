// ---- Config: point this at your deployed FastAPI backend ----
const API_BASE = "https://YOUR-BACKEND.onrender.com";

// ---- State ----
let token = localStorage.getItem("token") || null;
let role = localStorage.getItem("role") || null;
let editingItemNo = null; // null = creating new item

// ---- Helpers ----
function authHeaders(extra = {}) {
  return token ? { Authorization: `Bearer ${token}`, ...extra } : extra;
}

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, options);
  if (res.status === 401) { logout(); throw new Error("Session expired, please log in again"); }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.status === 204 ? null : res.json();
}

function $(id) { return document.getElementById(id); }

// ---- Auth screens ----
$("tabLogin").onclick = () => switchTab("login");
$("tabRegister").onclick = () => switchTab("register");
function switchTab(which) {
  $("tabLogin").classList.toggle("active", which === "login");
  $("tabRegister").classList.toggle("active", which === "register");
  $("loginForm").classList.toggle("hidden", which !== "login");
  $("registerForm").classList.toggle("hidden", which !== "register");
}

$("loginForm").onsubmit = async (e) => {
  e.preventDefault();
  $("loginMsg").textContent = "";
  try {
    const data = await api("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("loginUsername").value,
        password: $("loginPassword").value,
      }),
    });
    token = data.access_token;
    role = data.role;
    localStorage.setItem("token", token);
    localStorage.setItem("role", role);
    enterApp();
  } catch (err) {
    $("loginMsg").textContent = err.message;
  }
};

$("registerForm").onsubmit = async (e) => {
  e.preventDefault();
  $("regMsg").textContent = "";
  try {
    await api("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("regUsername").value,
        email: $("regEmail").value,
        password: $("regPassword").value,
      }),
    });
    $("regMsg").style.color = "#0a7d34";
    $("regMsg").textContent = "Account created — you can log in now.";
    switchTab("login");
  } catch (err) {
    $("regMsg").style.color = "#c0392b";
    $("regMsg").textContent = err.message;
  }
};

function logout() {
  token = null; role = null;
  localStorage.removeItem("token"); localStorage.removeItem("role");
  $("authScreen").classList.remove("hidden");
  $("appScreen").classList.add("hidden");
  $("userBar").innerHTML = "";
}

function enterApp() {
  $("authScreen").classList.add("hidden");
  $("appScreen").classList.remove("hidden");
  $("userBar").innerHTML = `${role === "admin" ? "👑 admin" : "staff"} <button id="logoutBtn">Log out</button>`;
  $("logoutBtn").onclick = logout;
  $("pendingBtn").classList.toggle("hidden", role !== "admin");
  loadItems();
}

// ---- Item list & search ----
$("searchBtn").onclick = () => {
  const q = $("searchInput").value.trim();
  q ? searchItems(q) : loadItems();
};
$("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") $("searchBtn").click(); });

async function loadItems() {
  $("pendingList").classList.add("hidden");
  $("itemList").classList.remove("hidden");
  try {
    const items = await api("/items", { headers: authHeaders() });
    renderItems(items);
  } catch (err) { alert(err.message); }
}

async function searchItems(q) {
  $("pendingList").classList.add("hidden");
  $("itemList").classList.remove("hidden");
  try {
    const items = await api(`/items/search?q=${encodeURIComponent(q)}`, { headers: authHeaders() });
    renderItems(items);
  } catch (err) { alert(err.message); }
}

function renderItems(items) {
  const list = $("itemList");
  list.innerHTML = "";
  if (!items.length) { list.innerHTML = "<p>No items found.</p>"; return; }
  for (const it of items) {
    const img = (it.images && it.images[0]) || "";
    const card = document.createElement("div");
    card.className = "item-card";
    card.innerHTML = `
      ${img ? `<img src="${img}">` : `<div class="item-card img"></div>`}
      <div class="info">
        <h3>${it.name} <span class="meta">#${it.item_no}</span></h3>
        <div class="price">Rs. ${Number(it.price).toFixed(2)}</div>
        <div class="meta">${it.category}</div>
        <div class="actions">
          <button data-edit="${it.item_no}">Edit</button>
          <button data-del="${it.item_no}" class="secondary">Delete</button>
        </div>
      </div>`;
    list.appendChild(card);
  }
  list.querySelectorAll("[data-edit]").forEach(btn =>
    btn.onclick = () => openEditModal(btn.dataset.edit, items));
  list.querySelectorAll("[data-del]").forEach(btn =>
    btn.onclick = () => deleteItem(btn.dataset.del));
}

// ---- Pending changes (admin) ----
$("pendingBtn").onclick = loadPending;
async function loadPending() {
  $("itemList").classList.add("hidden");
  $("pendingList").classList.remove("hidden");
  try {
    const changes = await api("/pending", { headers: authHeaders() });
    renderPending(changes);
  } catch (err) { alert(err.message); }
}

function renderPending(changes) {
  const list = $("pendingList");
  list.innerHTML = "";
  if (!changes.length) { list.innerHTML = "<p>No pending changes 🎉</p>"; return; }
  for (const c of changes) {
    const card = document.createElement("div");
    card.className = "item-card pending";
    card.innerHTML = `
      <div class="info">
        <h3><span class="badge">${c.action.toUpperCase()}</span> ${c.item_no || "(new item)"}</h3>
        <div class="meta">by user #${c.submitted_by} · ${new Date(c.submitted_at).toLocaleString()}</div>
        <pre class="meta" style="white-space:pre-wrap">${JSON.stringify(c.payload, null, 1)}</pre>
        <div class="actions">
          <button data-approve="${c.id}">Approve</button>
          <button data-reject="${c.id}" class="secondary">Reject</button>
        </div>
      </div>`;
    list.appendChild(card);
  }
  list.querySelectorAll("[data-approve]").forEach(btn =>
    btn.onclick = () => reviewChange(btn.dataset.approve, true));
  list.querySelectorAll("[data-reject]").forEach(btn =>
    btn.onclick = () => reviewChange(btn.dataset.reject, false));
}

async function reviewChange(id, approve) {
  try {
    await api(`/pending/${id}/review`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ approve }),
    });
    loadPending();
  } catch (err) { alert(err.message); }
}

// ---- Item modal (create/edit) ----
let uploadedImageUrl = "";

$("newItemBtn").onclick = () => openEditModal(null, []);
$("itemFormCancel").onclick = () => $("itemModal").classList.add("hidden");

function openEditModal(item_no, currentItems) {
  editingItemNo = item_no;
  uploadedImageUrl = "";
  $("itemFormMsg").textContent = "";
  $("f_image_preview").innerHTML = "";
  const existing = currentItems.find(i => i.item_no === item_no);

  $("itemModalTitle").textContent = item_no ? `Edit ${item_no}` : "New Item";
  $("f_item_no").value = existing ? existing.item_no : "";
  $("f_item_no").disabled = !!item_no;
  $("f_category").value = existing ? existing.category : "";
  $("f_name").value = existing ? existing.name : "";
  $("f_price").value = existing ? existing.price : "";
  $("f_description").value = existing ? existing.description : "";
  $("f_keywords").value = existing ? (existing.keywords || []).join(", ") : "";
  if (existing && existing.images && existing.images[0]) uploadedImageUrl = existing.images[0];

  $("itemModal").classList.remove("hidden");
}

$("f_image").onchange = async () => {
  const file = $("f_image").files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch(API_BASE + "/items/upload-image", {
      method: "POST",
      headers: authHeaders(),
      body: fd,
    });
    if (!res.ok) throw new Error("Image upload failed");
    const data = await res.json();
    uploadedImageUrl = data.url;
    $("f_image_preview").innerHTML = `<img src="${uploadedImageUrl}">`;
  } catch (err) {
    $("itemFormMsg").textContent = err.message;
  }
};

$("itemForm").onsubmit = async (e) => {
  e.preventDefault();
  $("itemFormMsg").textContent = "";

  const keywords = $("f_keywords").value.split(",").map(s => s.trim()).filter(Boolean);
  const body = {
    category: $("f_category").value,
    name: $("f_name").value,
    price: parseFloat($("f_price").value),
    description: $("f_description").value,
    keywords,
    images: uploadedImageUrl ? [uploadedImageUrl] : [],
  };

  try {
    if (editingItemNo) {
      const result = await api(`/items/${editingItemNo}`, {
        method: "PUT",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
      });
      finishSave(result);
    } else {
      body.item_no = $("f_item_no").value;
      const result = await api("/items", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
      });
      finishSave(result);
    }
  } catch (err) {
    $("itemFormMsg").textContent = err.message;
  }
};

function finishSave(result) {
  $("itemModal").classList.add("hidden");
  if (result.status === "pending_approval") {
    alert("Submitted — waiting for admin approval.");
  }
  loadItems();
}

async function deleteItem(item_no) {
  if (!confirm(`Delete ${item_no}?`)) return;
  try {
    const result = await api(`/items/${item_no}`, { method: "DELETE", headers: authHeaders() });
    if (result.status === "pending_approval") alert("Delete request submitted for admin approval.");
    loadItems();
  } catch (err) { alert(err.message); }
}

// ---- Boot ----
if (token) enterApp();
