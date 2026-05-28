let mesaActualId = null;
let todosLosProductos = [];

// =====================
// MESAS
// =====================
function cargarMesas() {
  fetch('/listar_mesas')
    .then(r => r.json())
    .then(mesas => {
      const grid = document.getElementById('gridMesas');
      grid.innerHTML = '';
      mesas.forEach(m => {
        const card = document.createElement('div');
        card.className = 'mesa-card' + (m.estado === 'ocupada' ? ' ocupada' : '');
        card.innerHTML = `
          <div class="mesa-numero">Mesa ${m.numero}</div>
          <div class="mesa-estado">${m.estado === 'ocupada' ? '🔴 Ocupada' : '🟢 Libre'}</div>
          ${m.estado === 'ocupada' ? `<div class="mesa-total">S/ ${parseFloat(m.total).toFixed(2)}</div>` : ''}
        `;
        card.onclick = () => abrirMesa(m.id, m.numero);
        grid.appendChild(card);
      });
    });
}

function abrirMesa(id, numero) {
  mesaActualId = id;
  document.getElementById('vista-mesas').style.display = 'none';
  document.getElementById('vista-detalle').style.display = 'block';
  document.getElementById('detTitle').textContent = 'Mesa ' + numero;
  cargarProductosMesa();
  cargarPedidoMesa();
}

function volverMesas() {
  mesaActualId = null;
  document.getElementById('vista-mesas').style.display = 'block';
  document.getElementById('vista-detalle').style.display = 'none';
  cargarMesas();
}

function cargarProductosMesa() {
  fetch('/listar_productos')
    .then(r => r.json())
    .then(data => {
      todosLosProductos = data;
      renderTablaProductosMesa(data);
    });
}

function renderTablaProductosMesa(lista) {
  const tbody = document.querySelector('#tablaProductosMesa tbody');
  tbody.innerHTML = '';
  lista.forEach(prod => {
    const fila = document.createElement('tr');
    fila.dataset.productoId = prod[2];
    fila.dataset.precio = prod[1];
    fila.dataset.nombre = prod[0];
    fila.innerHTML = `
      <td>${prod[0]}</td>
      <td>S/ ${parseFloat(prod[1]).toFixed(2)}</td>
      <td>
        <div class="qty-wrap">
          <button class="qty-btn" onclick="cambiarCantidad(this, -1)">−</button>
          <input type="number" min="1" value="1" class="qty-input">
          <button class="qty-btn" onclick="cambiarCantidad(this, 1)">+</button>
        </div>
      </td>
      <td><input type="checkbox" style="width:18px;height:18px;accent-color:var(--accent);cursor:pointer;"></td>
    `;
    tbody.appendChild(fila);
  });
}

function filtrarProdsMesa(txt) {
  const f = txt.toLowerCase();
  const filtrados = todosLosProductos.filter(p => p[0].toLowerCase().includes(f));
  renderTablaProductosMesa(filtrados);
}

function agregarAMesa() {
  const filas = document.querySelectorAll('#tablaProductosMesa tbody tr');
  const productos = [];
  filas.forEach(fila => {
    const cb = fila.querySelector('input[type="checkbox"]');
    const qty = fila.querySelector('.qty-input');
    if (cb && cb.checked) {
      productos.push({
        id: fila.dataset.productoId,
        nombre: fila.dataset.nombre,
        cantidad: parseInt(qty.value),
        precio: parseFloat(fila.dataset.precio)
      });
    }
  });

  if (productos.length === 0) {
    Swal.fire({ icon: 'warning', title: 'Sin productos', text: 'Selecciona al menos un producto', confirmButtonColor: '#c8883a' });
    return;
  }

  fetch('/agregar_mesa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mesa_id: mesaActualId, productos })
  })
    .then(r => r.json())
    .then(() => {
      document.querySelectorAll('#tablaProductosMesa input[type="checkbox"]').forEach(cb => cb.checked = false);
      document.querySelectorAll('#tablaProductosMesa .qty-input').forEach(inp => inp.value = 1);
      cargarPedidoMesa();
    });
}

function cargarPedidoMesa() {
  fetch('/pedido_mesa/' + mesaActualId)
    .then(r => r.json())
    .then(pedido => {
      const wrap = document.getElementById('pedidoWrap');
      if (pedido.length === 0) { wrap.style.display = 'none'; return; }
      wrap.style.display = 'block';
      const items = document.getElementById('pedidoItems');
      items.innerHTML = '';
      let total = 0;
      pedido.forEach(p => {
        total += p.precio * p.cantidad;
        const d = document.createElement('div');
        d.className = 'pedido-item';
        d.innerHTML = `<span>${p.nombre} x${p.cantidad}</span><span>S/ ${(p.precio * p.cantidad).toFixed(2)}</span>`;
        items.appendChild(d);
      });
      document.getElementById('pedidoTotal').textContent = 'S/ ' + total.toFixed(2);
    });
}

function confirmarVentaMesa() {
  const total = document.getElementById('pedidoTotal').textContent;
  fetch('/confirmar_mesa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mesa_id: mesaActualId })
  })
    .then(r => r.json())
    .then(() => {
      Swal.fire({
        icon: 'success',
        title: '¡Venta registrada!',
        text: 'Total: ' + total,
        confirmButtonColor: '#c8883a'
      }).then(() => {
        volverMesas();
      });
    });
}

// =====================
// CANTIDAD +/-
// =====================
function cambiarCantidad(btn, delta) {
  const input = btn.parentElement.querySelector('.qty-input');
  input.value = Math.max(1, parseInt(input.value) + delta);
}

// =====================
// REGISTRAR PRODUCTO
// =====================
function mostrarMensaje(event) {
  event.preventDefault();
  Swal.fire({
    icon: 'success',
    title: '¡Buen trabajo!',
    text: '✅ Nuevo producto ingresado',
    confirmButtonText: 'OK',
    confirmButtonColor: '#c8883a',
    allowOutsideClick: false,
    allowEscapeKey: false
  }).then((result) => {
    if (result.isConfirmed) event.target.submit();
  });
  return false;
}

// =====================
// INIT
// =====================
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('menuToggle') && null;
});