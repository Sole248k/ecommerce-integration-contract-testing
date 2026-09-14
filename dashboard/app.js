/**
 * TestForge Dashboard Controller
 * Handles Theme Toggling (Light/Dark), API interactions, and Pytest Suite execution.
 */

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initTabs();
  initProducts();
  initOrders();
  initContracts();
  initTestRunner();
  initDeductModal();
});

/* ==========================================================================
   1. Light & Dark Mode Theming
   ========================================================================== */
function initTheme() {
  const themeToggleBtn = document.getElementById("theme-toggle");
  const themeText = document.getElementById("theme-text");
  
  // Check persisted preference or system preference
  const savedTheme = localStorage.getItem("testforge_theme");
  const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme = savedTheme || (systemPrefersDark ? "dark" : "light");

  applyTheme(initialTheme);

  themeToggleBtn.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
  });

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("testforge_theme", theme);
    if (themeText) {
      themeText.textContent = theme === "dark" ? "Dark Mode" : "Light Mode";
    }
  }
}

/* ==========================================================================
   2. Tab Navigation
   ========================================================================== */
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  const panes = document.querySelectorAll(".tab-pane");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = `tab-${tab.getAttribute("data-tab")}`;
      
      tabs.forEach(t => t.classList.remove("active"));
      panes.forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
      }
    });
  });
}

/* ==========================================================================
   3. Products Controller (Provider)
   ========================================================================== */
let cachedProducts = [];

function initProducts() {
  const productForm = document.getElementById("product-form");
  const refreshBtn = document.getElementById("btn-refresh-products");

  fetchProducts();

  if (refreshBtn) {
    refreshBtn.addEventListener("click", fetchProducts);
  }

  if (productForm) {
    productForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msgEl = document.getElementById("product-form-msg");
      const saveBtn = document.getElementById("btn-save-product");

      const name = document.getElementById("prod-name").value.trim();
      const price = parseFloat(document.getElementById("prod-price").value);
      const stock = parseInt(document.getElementById("prod-stock").value, 10);
      const id = document.getElementById("prod-id").value.trim() || undefined;
      const sku = document.getElementById("prod-sku").value.trim() || undefined;

      const payload = { name, price, stock };
      if (id) payload.id = id;
      if (sku) payload.sku = sku;

      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";
      msgEl.className = "form-msg";

      try {
        const res = await fetch("/api/v1/products", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
          msgEl.textContent = `✓ Product created: ${data.name} (${data.id})`;
          msgEl.className = "form-msg success";
          productForm.reset();
          fetchProducts();
        } else {
          msgEl.textContent = `✗ Error: ${data.detail || JSON.stringify(data)}`;
          msgEl.className = "form-msg error";
        }
      } catch (err) {
        msgEl.textContent = `✗ Network Error: ${err.message}`;
        msgEl.className = "form-msg error";
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save to Product Database";
      }
    });
  }
}

async function fetchProducts() {
  const tbody = document.getElementById("products-tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/v1/products");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const products = await res.json();
    cachedProducts = products;

    if (products.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No products found. Add one above!</td></tr>`;
      return;
    }

    tbody.innerHTML = products.map(p => `
      <tr>
        <td><code>${escapeHtml(p.id)}</code></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td><span class="badge badge-purple">${escapeHtml(p.sku)}</span></td>
        <td>$${p.price.toFixed(2)}</td>
        <td>
          <span class="badge ${p.stock > 5 ? 'badge-emerald' : p.stock > 0 ? 'badge-warning' : 'badge-danger'}">
            ${p.stock} units
          </span>
        </td>
        <td>
          <button class="btn btn-xs btn-secondary" onclick="openDeductModal('${p.id}', '${escapeHtml(p.name)}', ${p.stock})">
            - Deduct Stock
          </button>
        </td>
      </tr>
    `).join("");

    updateOrderProductDropdowns(products);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Failed to load products: ${err.message}</td></tr>`;
  }
}

function updateOrderProductDropdowns(products) {
  const selects = document.querySelectorAll(".order-prod-select");
  selects.forEach(select => {
    const currentVal = select.value;
    select.innerHTML = `<option value="">Choose a product...</option>` +
      products.map(p => `
        <option value="${p.id}" data-price="${p.price}" data-stock="${p.stock}">
          ${p.name} ($${p.price.toFixed(2)} - ${p.stock} in stock)
        </option>
      `).join("");
    if (currentVal) select.value = currentVal;
  });
}

/* ==========================================================================
   4. Orders Controller (Consumer)
   ========================================================================== */
function initOrders() {
  const orderForm = document.getElementById("order-form");
  const refreshBtn = document.getElementById("btn-refresh-orders");

  fetchOrders();

  if (refreshBtn) {
    refreshBtn.addEventListener("click", fetchOrders);
  }

  // Live order estimate listener
  document.addEventListener("change", (e) => {
    if (e.target.matches(".order-prod-select, .order-prod-qty")) {
      calculateEstimatedTotal();
    }
  });

  if (orderForm) {
    orderForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const customerId = document.getElementById("order-customer").value.trim();
      const select = document.querySelector(".order-prod-select");
      const qtyInput = document.querySelector(".order-prod-qty");
      const msgEl = document.getElementById("order-form-msg");
      const submitBtn = document.getElementById("btn-submit-order");

      if (!select.value) {
        alert("Please select a product!");
        return;
      }

      const payload = {
        customer_id: customerId,
        items: [
          { product_id: select.value, quantity: parseInt(qtyInput.value, 10) }
        ]
      };

      submitBtn.disabled = true;
      submitBtn.textContent = "Validating with Product Service...";
      msgEl.className = "form-msg";

      try {
        const res = await fetch("/api/v1/orders", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
          msgEl.textContent = `✓ Order placed: ${data.id} - Total: $${data.total_amount.toFixed(2)} (Status: ${data.status})`;
          msgEl.className = "form-msg success";
          fetchOrders();
        } else {
          msgEl.textContent = `✗ Order Rejected: ${data.detail || JSON.stringify(data)}`;
          msgEl.className = "form-msg error";
        }
      } catch (err) {
        msgEl.textContent = `✗ Order Error: ${err.message}`;
        msgEl.className = "form-msg error";
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Order (POST /api/v1/orders)";
      }
    });
  }
}

function calculateEstimatedTotal() {
  const select = document.querySelector(".order-prod-select");
  const qtyInput = document.querySelector(".order-prod-qty");
  const totalEl = document.getElementById("order-estimated-total");

  if (!select || !qtyInput || !totalEl) return;

  const selectedOpt = select.selectedOptions[0];
  if (!selectedOpt || !selectedOpt.dataset.price) {
    totalEl.textContent = "$0.00";
    return;
  }

  const price = parseFloat(selectedOpt.dataset.price);
  const qty = parseInt(qtyInput.value, 10) || 1;
  totalEl.textContent = `$${(price * qty).toFixed(2)}`;
}

async function fetchOrders() {
  const tbody = document.getElementById("orders-tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/v1/orders");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const orders = await res.json();

    if (orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No orders placed yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = orders.map(o => {
      const statusClass = o.status.toLowerCase();
      const itemsList = o.items.map(i => `${i.product_id} (×${i.quantity})`).join(", ");

      return `
        <tr>
          <td><code>${escapeHtml(o.id)}</code></td>
          <td>${escapeHtml(o.customer_id)}</td>
          <td><strong>$${o.total_amount.toFixed(2)}</strong></td>
          <td>
            <span class="order-status-badge ${statusClass}">
              ${escapeHtml(o.status)}
            </span>
          </td>
          <td><small>${escapeHtml(itemsList || "None")}</small></td>
          <td>
            ${o.status === "PENDING" ? `
              <button class="btn btn-xs btn-primary" onclick="updateOrderStatus('${o.id}', 'CONFIRMED')">
                Confirm & Deduct
              </button>
              <button class="btn btn-xs btn-outline" onclick="updateOrderStatus('${o.id}', 'CANCELLED')">
                Cancel
              </button>
            ` : `<span class="text-muted"><small>Finalized</small></span>`}
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Failed to load orders: ${err.message}</td></tr>`;
  }
}

window.updateOrderStatus = async function(orderId, newStatus) {
  try {
    const res = await fetch(`/api/v1/orders/${orderId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      fetchOrders();
      fetchProducts(); // Refresh inventory if deduction occurred
    } else {
      const data = await res.json();
      alert(`Status Update Failed: ${data.detail || "Unknown error"}`);
    }
  } catch (err) {
    alert(`Error updating order status: ${err.message}`);
  }
};

/* ==========================================================================
   5. Pact Contract Inspector
   ========================================================================== */
async function initContracts() {
  const codeEl = document.getElementById("raw-contract-code");
  const copyBtn = document.getElementById("btn-copy-contract");

  try {
    const res = await fetch("/api/contract");
    if (res.ok) {
      const contractJson = await res.json();
      const formatted = JSON.stringify(contractJson, null, 2);
      if (codeEl) codeEl.textContent = formatted;

      if (copyBtn) {
        copyBtn.addEventListener("click", () => {
          navigator.clipboard.writeText(formatted).then(() => {
            copyBtn.textContent = "✓ Copied!";
            setTimeout(() => { copyBtn.textContent = "📋 Copy JSON"; }, 2000);
          });
        });
      }
    } else {
      if (codeEl) codeEl.textContent = "// Contract file not yet generated. Run Pact tests to generate.";
    }
  } catch (err) {
    if (codeEl) codeEl.textContent = `// Error loading contract: ${err.message}`;
  }
}

/* ==========================================================================
   6. Live Test Runner
   ========================================================================== */
function initTestRunner() {
  const consoleEl = document.getElementById("test-console");
  const clearBtn = document.getElementById("btn-clear-console");

  const runAllBtn = document.getElementById("btn-run-all-tests");
  const runIntegrationBtn = document.getElementById("btn-run-integration");
  const runConsumerBtn = document.getElementById("btn-run-consumer");
  const runProviderBtn = document.getElementById("btn-run-provider");

  if (clearBtn && consoleEl) {
    clearBtn.addEventListener("click", () => {
      consoleEl.textContent = "Console cleared.\n";
    });
  }

  async function executeTestSuite(suiteType, label) {
    if (!consoleEl) return;
    consoleEl.textContent += `\n[${new Date().toLocaleTimeString()}] Starting ${label}...\n`;
    setAllTilesState("running");

    try {
      const res = await fetch(`/api/tests/run?suite=${suiteType}`, { method: "POST" });
      const data = await res.json();

      consoleEl.textContent += data.output || "No output returned.";
      if (data.exit_code === 0) {
        consoleEl.textContent += `\n\n[SUCCESS] ${label} PASSED WITH 100% COMPLIANCE!\n`;
        setAllTilesState("passed");
      } else {
        consoleEl.textContent += `\n\n[FAILURE] Suite exited with code ${data.exit_code}\n`;
      }
      initContracts(); // Refresh raw contract if newly generated
    } catch (err) {
      consoleEl.textContent += `\n[ERROR] Runner communication failed: ${err.message}\n`;
    }
  }

  function setAllTilesState(state) {
    document.querySelectorAll(".test-tile-status").forEach(badge => {
      badge.className = `test-tile-status ${state}`;
      badge.textContent = state.toUpperCase();
    });
  }

  if (runAllBtn) runAllBtn.addEventListener("click", () => executeTestSuite("all", "All 8 Verification Tests"));
  if (runIntegrationBtn) runIntegrationBtn.addEventListener("click", () => executeTestSuite("integration", "Integration Tests (IT-01 to IT-05)"));
  if (runConsumerBtn) runConsumerBtn.addEventListener("click", () => executeTestSuite("consumer", "Pact Consumer Contract Test"));
  if (runProviderBtn) runProviderBtn.addEventListener("click", () => executeTestSuite("provider", "Pact Provider Verification"));
}

/* ==========================================================================
   7. Deduction Modal
   ========================================================================== */
function initDeductModal() {
  const modal = document.getElementById("deduct-modal");
  const closeBtn = document.getElementById("btn-close-modal");
  const cancelBtn = document.getElementById("btn-cancel-modal");
  const deductForm = document.getElementById("deduct-form");

  if (!modal) return;

  const closeModal = () => modal.classList.add("hidden");
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

  if (deductForm) {
    deductForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const prodId = document.getElementById("deduct-prod-id").value;
      const qty = parseInt(document.getElementById("deduct-qty").value, 10);
      const msgEl = document.getElementById("deduct-modal-msg");

      try {
        const res = await fetch(`/api/v1/products/${prodId}/deduct-stock`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ quantity: qty })
        });
        const data = await res.json();

        if (res.ok) {
          closeModal();
          fetchProducts();
        } else {
          msgEl.textContent = `✗ ${data.detail || "Failed"}`;
          msgEl.className = "form-msg error";
        }
      } catch (err) {
        msgEl.textContent = `✗ Network Error: ${err.message}`;
        msgEl.className = "form-msg error";
      }
    });
  }
}

window.openDeductModal = function(id, name, stock) {
  const modal = document.getElementById("deduct-modal");
  if (!modal) return;
  document.getElementById("deduct-prod-id").value = id;
  document.getElementById("deduct-prod-name").textContent = name;
  document.getElementById("deduct-prod-current-stock").textContent = `${stock} units`;
  document.getElementById("deduct-qty").value = "1";
  document.getElementById("deduct-modal-msg").className = "form-msg";
  modal.classList.remove("hidden");
};

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
