async function createOrder() {
  const userId = document.getElementById("userId").value;
  const productId = document.getElementById("productId").value;

  const response = await fetch("/api/orders", {
    method: "POST",
    body: JSON.stringify({ userId, productId }),
  });

  document.getElementById("output").textContent =
    await response.text();
}

document.getElementById("createOrderButton")
  .addEventListener("click", createOrder);
