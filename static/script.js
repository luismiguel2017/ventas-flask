let mesaActualId = null;
let todosLosProductos = [];
let pedidoAcumulado = [];

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
  pedidoAcumulado = [];

  // Mostrar vista detalle, ocultar vista mesas
  document.getElementById('vista-mesas').style.display = 'none';
  document.getElementById('vista-detalle').style.display = 'block';
  document.getElementById('vista-categorias').style.display = 'block';
  document.getElementById('vista-productos-cat').style.display = 'none';
  document.getElementById('detTitle').textContent = 'Mesa ' + numero;

  // Cargar pedido existente y categorías
  cargarPedidoMesa();
  renderCategorias();
}

function volverMesas() {
  mesaActualId = null;
  pedidoAcumulado = [];
  document.getElementById('vista-mesas').style.display = 'block';
  document.getElementById('vista-detalle').style.display = 'none';
  cargarMesas();
}

function volverCategorias() {
  document.getElementById('vista-categorias').style.display = 'block';
  document.getElementById('vista-productos-cat').style.display = 'none';
  document.getElementById('buscarProd').value = '';
}

// =====================
// CATEGORÍAS
// =====================
const categorias = [
  { nombre: 'Jugos',     icon: '🧃' },
  { nombre: 'Sandwiches', icon: '🥪' },
  { nombre: 'Calientes', icon: '☕' },
  { nombre: 'Dulces',    icon: '🍰' },
  { nombre: 'Salados',   icon: '🥟' },
  { nombre: 'Fríos',     icon: '🧊' },
  { nombre: 'Menú',      icon: '🍽️' },
  { nombre: 'Golosinas y piqueos', icon: '🍬' },
];

function renderCategorias() {
  const grid = document.getElementById('gridCategorias');
  grid.innerHTML = '';
  categorias.forEach(cat => {
    const card = document.createElement('div');
    card.className = 'mesa-card';
    card.innerHTML = `
      <div class="mesa-numero">${cat.icon}</div>
      <div class="mesa-estado">${cat.nombre}</div>
    `;
    card.onclick = () => abrirCategoria(cat.nombre, cat.icon);
    grid.appendChild(card);
  });
}

function abrirCategoria(nombre, icon) {
  document.getElementById('vista-categorias').style.display = 'none';
  document.getElementById('vista-productos-cat').style.display = 'block';
  document.getElementById('catTitle').textContent = icon + ' ' + nombre;
  document.getElementById('buscarProd').value = '';
  cargarProductosPorCategoria(nombre);
}

// =====================
// PRODUCTOS POR CATEGORÍA
// =====================
function cargarProductosPorCategoria(categoria) {
  fetch('/listar_productos_categoria/' + encodeURIComponent(categoria))
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
    // prod = [nombre, precio, id]
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
    `;
    fila.style.cursor = 'pointer';
    fila.onclick = function(e) {
      // No activar si hace clic en los botones +/-
      if (e.target.closest('.qty-btn') || e.target.closest('.qty-input')) return;
      fila.classList.toggle('fila-seleccionada');
    };
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
    const qty = fila.querySelector('.qty-input');
    if (fila.classList.contains('fila-seleccionada')) {
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
      Swal.fire({ icon: 'success', title: '¡Agregado!', text: 'Productos agregados a la mesa', confirmButtonColor: '#c8883a', timer: 1200, showConfirmButton: false });
    });
}

// =====================
// PEDIDO ACUMULADO
// =====================
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
  // Cargar mesas al abrir la página
  cargarMesas();
  
  // Actualizar cada 5 segundos (POLLING EN TIEMPO REAL)
  setInterval(cargarMesas, 5000);
});