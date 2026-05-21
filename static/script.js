// Cambiar entre pestañas
function mostrarSeccion(id) {
  document.querySelectorAll('.seccion').forEach(sec => sec.classList.remove('activa'));
  document.getElementById(id).classList.add('activa');

  // Marcar botón activo
  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.remove('btn-primary', 'activo');
    tab.classList.add('btn-outline-primary');
  });
  const tabActivo = document.querySelector(`.tab[onclick="mostrarSeccion('${id}')"]`);
  tabActivo.classList.remove('btn-outline-primary');
  tabActivo.classList.add('btn-primary', 'activo');

  if (id === 'venta') cargarProductos();
}

// Cargar productos desde Flask
function cargarProductos() {
  fetch('/listar_productos')
    .then(response => response.json())
    .then(data => {
      const tbody = document.querySelector('#tablaProductos tbody');
      tbody.innerHTML = '';

      if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No hay productos registrados</td></tr>';
        return;
      }

      data.forEach(prod => {
        const fila = document.createElement('tr');
        fila.dataset.productoId = prod[2];
        fila.dataset.precio = prod[1];
        fila.innerHTML = `
          <td>${prod[0]}</td>
          <td>S/ ${parseFloat(prod[1]).toFixed(2)}</td>
          <td><input type="number" min="1" value="1" class="form-control form-control-sm" style="width:70px"></td>
          <td class="text-center"><input type="checkbox" class="form-check-input"></td>
        `;
        tbody.appendChild(fila);
      });
    })
    .catch(() => {
      const tbody = document.querySelector('#tablaProductos tbody');
      tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-3">Error al cargar productos</td></tr>';
    });
}

// Filtro de búsqueda
document.addEventListener('DOMContentLoaded', () => {
  const buscar = document.getElementById('buscar');
  if (buscar) {
    buscar.addEventListener('keyup', function () {
      const texto = this.value.toLowerCase();
      const filas = document.querySelectorAll('#tablaProductos tbody tr');
      filas.forEach(fila => {
        const nombre = fila.querySelector('td')?.textContent.toLowerCase() || '';
        fila.style.display = nombre.includes(texto) ? '' : 'none';
      });
    });
  }

  // Confirmar venta
  const confirmarBtn = document.querySelector('.confirmar');
  if (confirmarBtn) {
    confirmarBtn.addEventListener('click', () => {
      const filas = document.querySelectorAll('#tablaProductos tbody tr');
      const productos = [];

      filas.forEach(fila => {
        const checkbox = fila.querySelector('input[type="checkbox"]');
        const cantidadInput = fila.querySelector('input[type="number"]');
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
          confirmButtonText: 'OK',
          confirmButtonColor: '#3085d6'
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
            confirmButtonText: 'OK',
            confirmButtonColor: '#3085d6'
          }).then(() => {
            // Limpiar selección y cantidades
            document.querySelectorAll('#tablaProductos input[type="checkbox"]').forEach(cb => cb.checked = false);
            document.querySelectorAll('#tablaProductos input[type="number"]').forEach(inp => inp.value = 1);
          });
        })
        .catch(() => {
          Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No se pudo registrar la venta. Intenta nuevamente.',
            confirmButtonText: 'OK',
            confirmButtonColor: '#d33'
          });
        });
    });
  }

  // Marcar pestaña Ingresar Producto como activa al cargar
  const tabInicio = document.querySelector(`.tab[onclick="mostrarSeccion('producto')"]`);
  if (tabInicio) {
    tabInicio.classList.remove('btn-outline-primary');
    tabInicio.classList.add('btn-primary', 'activo');
  }
});

// Alerta al registrar producto
function mostrarMensaje(event) {
  event.preventDefault();

  Swal.fire({
    icon: 'success',
    title: '¡Buen trabajo!',
    text: '✅ Nuevo producto ingresado',
    confirmButtonText: 'OK',
    confirmButtonColor: '#3085d6',
    allowOutsideClick: false,
    allowEscapeKey: false,
    customClass: {
      popup: 'popup-pequeno'
    }
  }).then((result) => {
    if (result.isConfirmed) {
      event.target.submit();
    }
  });

  return false;
}