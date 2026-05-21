// Cambiar entre pestañas
function mostrarSeccion(id) {
  document.querySelectorAll('.seccion').forEach(sec => sec.classList.remove('activa'));
  document.getElementById(id).classList.add('activa');

  document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
  document.querySelector(`.tab[onclick="mostrarSeccion('${id}')"]`).classList.add('active');

  if (id === 'venta') {
    cargarProductos();
  }
}

// Cargar productos desde Flask
function cargarProductos() {
  fetch('/listar_productos')
    .then(response => response.json())
    .then(data => {
      const tbody = document.querySelector('#tablaProductos tbody');
      tbody.innerHTML = '';
      data.forEach(prod => {
        // prod = [nombre, precio, id]
        const fila = document.createElement('tr');
        fila.dataset.productoId = prod[2]; // guardar id del producto
        fila.innerHTML = `
          <td>${prod[0]}</td>
          <td>${parseFloat(prod[1]).toFixed(2)}</td>
          <td><input type="number" min="1" value="1" style="width:60px"></td>
          <td><input type="checkbox"></td>
        `;
        tbody.appendChild(fila);
      });
    })
    .catch(error => console.error('Error al cargar productos:', error));
}

// Filtro de productos
document.addEventListener('DOMContentLoaded', () => {
  const buscar = document.getElementById('buscar');
  if (buscar) {
    buscar.addEventListener('keyup', function() {
      const texto = this.value.toLowerCase();
      const filas = document.querySelectorAll('#tablaProductos tbody tr');
      filas.forEach(fila => {
        const nombre = fila.querySelector('td').textContent.toLowerCase();
        fila.style.display = nombre.startsWith(texto) ? '' : 'none';
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
        if (checkbox.checked) {
          productos.push({
            id: fila.dataset.productoId,
            nombre: fila.querySelector('td').textContent,
            cantidad: parseInt(cantidadInput.value)
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
        Swal.fire({
          icon: 'success',
          title: 'Venta registrada',
          text: `ID de venta: ${data.venta_id}`,
          confirmButtonText: 'OK',
          confirmButtonColor: '#3085d6'
        });
      })
      .catch(err => console.error('Error al registrar venta:', err));
    });
  }
});

// Alerta moderna al registrar producto con botón OK
function mostrarMensaje(event) {
  // Evita envío inmediato
  event.preventDefault();

  Swal.fire({
    icon: 'success',
    title: '¡Buen trabajo!',
    text: '✅ Nuevo producto ingresado',
    confirmButtonText: 'OK',
    confirmButtonColor: '#3085d6',
    allowOutsideClick: false,
    allowEscapeKey: false,
    showConfirmButton: true,
    customClass: {
      popup: 'popup-pequeno'
    }
  }).then((result) => {
    if (result.isConfirmed) {
      event.target.submit(); // envía el formulario después de cerrar el popup
    }
  });

  return false;
}
