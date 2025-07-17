
function handleAdminButtonClick() {
  fetch('/check-auth')
    .then(response => response.json())
    .then(data => {
      if (data.authenticated) {
        window.location.href = '/admin';
      } else {
        window.location.href = '/login';
      }
    })
    .catch(() => {
      window.location.href = '/login';
    });
}
// Add this event listener to the admin button
document.addEventListener('DOMContentLoaded', function() {
  // ... existing code ...

    let currentTable = null;
  const menuContainer = document.getElementById("menuContainer");
  const cartItems = document.getElementById("cartItems");
  const totalPrice = document.getElementById("totalPrice");
  const confirmBtn = document.getElementById("confirmTable");
  const tableInput = document.getElementById("tableNumber");
  const searchBox = document.getElementById("searchBox");
  const checkoutBtn = document.getElementById("checkout");
  const categoryButtons = document.querySelectorAll(".category-btn");
  let currentCategory = "All";
  let debounceTimeout;

  function renderMenu(items) {
    menuContainer.innerHTML = "";
    const filtered = items.filter(item => {
      return (currentCategory === "All" || item.category === currentCategory) &&
        item.name.toLowerCase().includes(searchBox.value.toLowerCase());
    });
    
    if (filtered.length === 0) {
      menuContainer.innerHTML = `
        <div class="col-12 text-center py-5">
          <i class="bi bi-search" style="font-size: 3rem; color: #ccc;"></i>
          <h4 class="mt-3">No items found</h4>
          <p class="text-muted">Try a different search term or category</p>
        </div>
      `;
      return;
    }

    filtered.forEach(item => {
      const div = document.createElement("div");
      div.className = "col-md-4 col-sm-6 mb-4";
      div.innerHTML = `
        <div class="card menu-item-card h-100">
          <img src="${item.image}" class="card-img-top" alt="${item.name}">
          <div class="card-body">
            <h5 class="card-title">${item.name}</h5>
            <p class="card-text text-danger fw-bold">$${item.price.toFixed(2)}</p>
            <div class="input-group mb-3">
              <span class="input-group-text">Qty</span>
              <input type="number" class="form-control quantity" value="1" min="1">
            </div>
            <button class="btn btn-warning w-100 add-to-cart-btn" data-id="${item.id}">
              <i class="bi bi-cart-plus"></i> Add to Cart
            </button>
          </div>
        </div>
      `;
      menuContainer.appendChild(div);
    });

    document.querySelectorAll(".add-to-cart-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const qty = parseInt(btn.closest(".card-body").querySelector(".quantity").value);
        
        if (!currentTable) {
          showToast("Please confirm your table number first", "warning");
          return;
        }
        
        fetch("/add_to_cart", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ table_number: currentTable, item_id: id, quantity: qty })
        }).then(() => {
          showToast("Item added to cart", "success");
          loadCart();
        });
      });
    });
  }

  function loadCart() {
    if (!currentTable) return;
    
    fetch("/get_cart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ table_number: currentTable })
    })
      .then(res => res.json())
      .then(data => {
        cartItems.innerHTML = "";
        
        if (data.cart.length === 0) {
          cartItems.innerHTML = `
            <div class="text-center py-4">
              <i class="bi bi-cart" style="font-size: 2rem; color: #ccc;"></i>
              <p class="mt-2">Your cart is empty</p>
            </div>
          `;
        } else {
          data.cart.forEach(item => {
            const div = document.createElement("div");
            div.className = "cart-item";
            div.innerHTML = `
              <div>
                <span class="fw-bold">${item.name}</span>
                <span class="badge bg-secondary ms-2">${item.qty}x</span>
                <span class="text-muted">$${item.price.toFixed(2)}</span>
              </div>
              <div>
                <span class="fw-bold">$${(item.price * item.qty).toFixed(2)}</span>
                <i class="bi bi-trash ms-3 remove-item" data-id="${item.id}"></i>
              </div>
            `;
            cartItems.appendChild(div);
          });
        }
        
        totalPrice.textContent = data.total.toFixed(2);
        
        // Add event listeners to remove buttons
        document.querySelectorAll(".remove-item").forEach(btn => {
          btn.addEventListener("click", () => {
            const id = parseInt(btn.dataset.id);
            removeItemFromCart(id);
          });
        });
      });
  }

  function removeItemFromCart(itemId) {
    fetch("/remove_item", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ table_number: currentTable, item_id: itemId })
    }).then(() => {
      showToast("Item removed from cart", "info");
      loadCart();
    });
  }

  function showToast(message, type = "info") {
    const toastContainer = document.createElement("div");
    toastContainer.style.position = "fixed";
    toastContainer.style.top = "20px";
    toastContainer.style.right = "20px";
    toastContainer.style.zIndex = "1050";
    
    const toast = document.createElement("div");
    toast.className = `toast show bg-${type === "info" ? "info" : type === "success" ? "success" : "warning"} text-white`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
      <div class="toast-body">
        ${message}
      </div>
    `;
    
    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);
    
    setTimeout(() => {
      toastContainer.remove();
    }, 3000);
  }

  confirmBtn.addEventListener("click", () => {
    if (!tableInput.value) {
      showToast("Please enter a valid table number", "warning");
      return;
    }
    
    currentTable = tableInput.value;
    confirmBtn.innerHTML = `<i class="bi bi-check-circle"></i> Table ${currentTable} Confirmed`;
    confirmBtn.classList.remove("btn-danger");
    confirmBtn.classList.add("btn-success");
    confirmBtn.disabled = true;
    
    renderMenu(MENU_DATA);
    loadCart();
  });

  searchBox.addEventListener("input", () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      renderMenu(MENU_DATA);
    }, 300);
  });

  categoryButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      currentCategory = btn.dataset.category;
      categoryButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderMenu(MENU_DATA);
    });
  });

  // Update the checkout function in script.js
  checkoutBtn.addEventListener("click", () => {
    if (!currentTable) {
      showToast('Please confirm your table number first', 'warning');
      return;
    }
    
    if (confirm("Are you sure you want to checkout? This will complete your order.")) {
      fetch("/generate_bill", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ table_number: currentTable })
      })
      .then(res => res.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `receipt_table_${currentTable}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        
        // Mark all items as served instead of removing them
        fetch("/mark_all_served", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ table_number: currentTable })
        }).then(() => {
          showToast("Order completed successfully!", "success");
          cartItems.innerHTML = "";
          totalPrice.textContent = "0.00";
          confirmBtn.innerHTML = "Confirm Table";
          confirmBtn.classList.remove("btn-success");
          confirmBtn.classList.add("btn-danger");
          confirmBtn.disabled = false;
          currentTable = null;
        });
      });
    }
  });


 renderMenu(MENU_DATA);
  
  // Add this to handle admin button click
  const adminButton = document.querySelector('a[href="/admin"]');
  if (adminButton) {
    adminButton.addEventListener('click', function(e) {
      e.preventDefault();
      handleAdminButtonClick();
    });
  }
  
  // Add this to handle home button click
  const homeButton = document.querySelector('a[href="/"]');
  if (homeButton) {
    homeButton.addEventListener('click', function(e) {
      e.preventDefault();
      window.location.href = '/';
    });
  }
});



