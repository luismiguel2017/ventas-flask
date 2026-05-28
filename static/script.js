// Cambiar cantidad
function cambiarCantidad(btn, delta) {
  const input = btn.parentElement.querySelector('.qty-input');
  const nuevo = Math.max(1, parseInt(input.value) + delta);
  input.value = nuevo;
}

// Cargar productos desde Flask
function cargarProductos() {
  fetch('/listar_productos')
    .then(response => response.json())
    .then(data => {
      const tbody = document.querySelector('#tablaProductos tbody');
      tbody.innerHTML = '';

      if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:1rem">No hay productos registrados</td></tr>';
        return;
      }

      data.forEach(prod => {
        const fila = document.createElement('tr');
        fila.dataset.productoId = prod[2];
        fila.dataset.precio = prod[1];
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
    })
    .catch(() => {
      const tbody = document.querySelector('#tablaProductos tbody');
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#f4a0a0;padding:1rem">Error al cargar productos</td></tr>';
    });
}

// Filtro de búsqueda
document.addEventListener('DOMContentLoaded', () => {

  cargarProductos();

  const buscar = document.getElementById('buscar');
  if (buscar) {
    buscar.addEventListener('keyup', function () {
      const texto = this.value.toLowerCase();
      document.querySelectorAll('#tablaProductos tbody tr').forEach(fila => {
        const nombre = fila.querySelector('td')?.textContent.toLowerCase() || '';
        fila.style.display = nombre.includes(texto) ? '' : 'none';
      });
    });
  }

  const confirmarBtn = document.querySelector('.btn-confirm');
  if (confirmarBtn && document.getElementById('venta')) {
    confirmarBtn.addEventListener('click', confirmarVenta);
  }
});

// Confirmar venta
function confirmarVenta() {
  const filas = document.querySelectorAll('#tablaProductos tbody tr');
  const productos = [];

  filas.forEach(fila => {
    const checkbox = fila.querySelector('input[type="checkbox"]');
    const cantidadInput = fila.querySelector('.qty-input');
    if (checkbox && checkbox.checked) {
      productos.push({
        id: fila.dataset.productoId,
        nombre: fila.querySelector('td').textContent,
        cantidad: parseInt(cantidadInput.value),
        precio: parseFloat(fila.dataset.precio)
      });
    }
  });

  if (productos.length === 0) {
    Swal.fire({
      icon: 'warning',
      title: 'Sin productos',
      text: 'Selecciona al menos un producto para registrar la venta',
      confirmButtonColor: '#c8883a'
    });
    return;
  }

  fetch('/registrar_venta', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ productos })
  })
    .then(res => res.json())
    .then(data => {
      const total = productos.reduce((acc, p) => acc + p.cantidad * p.precio, 0);
      Swal.fire({
        icon: 'success',
        title: '¡Venta registrada!',
        text: `Total: S/ ${total.toFixed(2)}`,
        confirmButtonColor: '#c8883a'
      }).then(() => {
        document.querySelectorAll('#tablaProductos input[type="checkbox"]').forEach(cb => cb.checked = false);
        document.querySelectorAll('#tablaProductos .qty-input').forEach(inp => inp.value = 1);
        const buscar = document.getElementById('buscar');
        if (buscar) {
          buscar.value = '';
          document.querySelectorAll('#tablaProductos tbody tr').forEach(f => f.style.display = '');
        }
      });
    })
    .catch(() => {
      Swal.fire({
        icon: 'error',
        title: 'Error',
        text: 'No se pudo registrar la venta. Intenta nuevamente.',
        confirmButtonColor: '#d33'
      });
    });
}

// Alerta al registrar producto
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
    if (result.isConfirmed) {
      event.target.submit();
    }
  });
  return false;
}