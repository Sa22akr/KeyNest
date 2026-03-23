const menuBtn = document.getElementById("menuBtn");
const navMenu = document.getElementById("navMenu");

if (menuBtn && navMenu) {
  menuBtn.addEventListener("click", () => {
    navMenu.classList.toggle("show");
  });
}

function getCart() {
  try {
    return JSON.parse(localStorage.getItem("cart")) || [];
  } catch (error) {
    console.error("Error reading cart from localStorage:", error);
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem("cart", JSON.stringify(cart));
  updateCartCount();
  updateAddToCartButtonState();
}

function updateCartCount() {
  const cart = getCart();
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);

  document.querySelectorAll("#cartCount").forEach((el) => {
    el.textContent = count;
  });
}

function updateAddToCartButtonState() {
  const addToCartBtn = document.getElementById("addToCartBtn");
  if (!addToCartBtn || typeof storeProduct === "undefined") return;

  const cart = getCart();
  const alreadyInCart = cart.some((item) => item.id === storeProduct.id);

  if (alreadyInCart) {
    addToCartBtn.disabled = true;
    addToCartBtn.textContent = "Already in Cart";
    addToCartBtn.classList.add("disabled");
  } else {
    addToCartBtn.disabled = false;
    addToCartBtn.textContent = "Add to Cart";
    addToCartBtn.classList.remove("disabled");
  }
}

function addSingleProductToCart() {
  if (typeof storeProduct === "undefined") {
    console.error("storeProduct is not defined.");
    alert("Product data is missing.");
    return;
  }

  const cart = getCart();
  const existing = cart.find((item) => item.id === storeProduct.id);

  if (existing || cart.length > 0) {
    alert("You already have this service in your cart.");
    updateAddToCartButtonState();
    return;
  }

  cart.push({
    ...storeProduct,
    quantity: 1
  });

  saveCart(cart);
  alert("Service added to cart.");
}

function removeFromCart(productId) {
  const cart = getCart().filter((item) => item.id !== productId);
  saveCart(cart);
  renderCartPage();
}

function renderCartPage() {
  const cartItems = document.getElementById("cartItems");
  const cartTotal = document.getElementById("cartTotal");

  if (!cartItems || !cartTotal) return;

  const cart = getCart();

  if (!cart.length) {
    cartItems.innerHTML = `
      <div class="blocked-box">
        <p>Your cart is empty.</p>
      </div>
    `;
    cartTotal.textContent = "0.00";
    return;
  }

  cartItems.innerHTML = cart.map((item) => `
    <div class="cart-item">
      <div>
        <h3>${item.name}</h3>
        <p>${item.platform} • Quantity: ${item.quantity}</p>
      </div>
      <div>
        <strong>£${(item.price * item.quantity).toFixed(2)}</strong>
        <button class="btn small secondary" onclick="removeFromCart(${item.id})" type="button">Remove</button>
      </div>
    </div>
  `).join("");

  const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  cartTotal.textContent = total.toFixed(2);
}

async function startStripeCheckout() {
  const cart = getCart();
  const stripeCheckoutBtn = document.getElementById("stripeCheckoutBtn");

  if (!cart.length) {
    alert("Your cart is empty.");
    return;
  }

  if (stripeCheckoutBtn) {
    stripeCheckoutBtn.disabled = true;
    stripeCheckoutBtn.textContent = "Redirecting...";
  }

  try {
    const response = await fetch("/create-checkout-session/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ cart })
    });

    const contentType = response.headers.get("content-type") || "";
    let data = {};

    if (contentType.includes("application/json")) {
      data = await response.json();
    } else {
      const text = await response.text();
      console.error("Non-JSON response:", text);
      throw new Error("Server returned a non-JSON response.");
    }

    console.log("Stripe checkout response:", data);

    if (response.ok && data.url) {
      window.location.href = data.url;
      return;
    }

    throw new Error(data.error || "Could not start checkout.");
  } catch (error) {
    console.error("Stripe checkout error:", error);
    alert(error.message || "Something went wrong.");
  } finally {
    if (stripeCheckoutBtn) {
      stripeCheckoutBtn.disabled = false;
      stripeCheckoutBtn.textContent = "Proceed to Checkout";
    }
  }
}

async function verifyStripeSessionAndUnlockForm() {
  const statusMessage = document.getElementById("paymentStatusMessage");
  const formWrapper = document.getElementById("orderFormWrapper");
  const blockedBox = document.getElementById("paymentBlocked");
  const sessionInput = document.getElementById("paymentRef");
  const amountPaidInput = document.getElementById("amountPaid");
  const productSummaryInput = document.getElementById("productSummary");

  if (!statusMessage || !formWrapper || !blockedBox) return;

  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session_id");

  if (!sessionId) {
    statusMessage.textContent = "No verified payment session found.";
    blockedBox.classList.remove("hidden");
    return;
  }

  try {
    const response = await fetch(`/verify-session/?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();

    if (data.paid) {
      statusMessage.textContent = "Payment confirmed. Please complete your order details.";
      formWrapper.classList.remove("hidden");
      blockedBox.classList.add("hidden");

      if (sessionInput) sessionInput.value = data.sessionId || "";
      if (amountPaidInput) amountPaidInput.value = data.amountTotal || "";
      if (productSummaryInput) productSummaryInput.value = data.itemsSummary || "";

      localStorage.removeItem("cart");
      updateCartCount();
      updateAddToCartButtonState();
    } else {
      statusMessage.textContent = "Your payment has not been confirmed.";
      blockedBox.classList.remove("hidden");
    }
  } catch (error) {
    console.error(error);
    statusMessage.textContent = "Could not verify payment status.";
    blockedBox.classList.remove("hidden");
  }
}

function handleOrderFormSubmission() {
  const orderForm = document.getElementById("orderForm");
  if (!orderForm) return;

  orderForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const payload = {
      fullName: document.getElementById("fullName")?.value || "",
      email: document.getElementById("email")?.value || "",
      productSummary: document.getElementById("productSummary")?.value || "",
      amountPaid: document.getElementById("amountPaid")?.value || "",
      paymentRef: document.getElementById("paymentRef")?.value || "",
      activationMethod: document.getElementById("activationMethod")?.value || "",
      accountEmail: document.getElementById("accountEmail")?.value || "",
      notes: document.getElementById("notes")?.value || ""
    };

    try {
      const response = await fetch("/submit-order-form/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (data.success) {
        window.location.href = "/thank-you/";
      } else {
        alert("Could not submit form.");
      }
    } catch (error) {
      console.error(error);
      alert("There was an error submitting the form.");
    }
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const addToCartBtn = document.getElementById("addToCartBtn");
  const stripeCheckoutBtn = document.getElementById("stripeCheckoutBtn");

  if (addToCartBtn) {
    addToCartBtn.addEventListener("click", addSingleProductToCart);
  }

  if (stripeCheckoutBtn) {
    stripeCheckoutBtn.addEventListener("click", startStripeCheckout);
  }

  renderCartPage();
  verifyStripeSessionAndUnlockForm();
  handleOrderFormSubmission();
  updateCartCount();
  updateAddToCartButtonState();
});