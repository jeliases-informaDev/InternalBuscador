using internal_search.Domain.DTOs.buscador.empresa.masivo; // Asegúrate de usar el namespace del masivo
using internal_search.Domain.Interfaces.Buscador.empresas.masivo;
using Microsoft.EntityFrameworkCore;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace internal_search_backend.Infraestructure.Repositories.Buscador.empresas.masiva
{
    public class BuscadorEmpresaMasivoRepository : IBuscadorEmpresaMasivoRepository
    {
        private readonly AppDbContext _db;

        public BuscadorEmpresaMasivoRepository(AppDbContext db)
        {
            _db = db;
        }

        // 1. Cambiado a BuscadorEmpresaMasivoResponseDto
        public async Task<BuscadorEmpresaMasivoResponseDto> BuscarMasivoPorRucAsync(
                    List<string> rucsValidos, HashSet<string> secciones, CancellationToken ct)
        {
            // 2. Instanciado el DTO masivo correcto
            var result = new BuscadorEmpresaMasivoResponseDto();

            var pideMoviles = secciones.Contains(BuscadorEmpresaMasivoEntradaDtocs.Moviles);
            var pideSueldos = secciones.Contains(BuscadorEmpresaMasivoEntradaDtocs.Sueldos);
            var pideCalificacion = secciones.Contains(BuscadorEmpresaMasivoEntradaDtocs.Calificacion);
            var pideDeuda = secciones.Contains(BuscadorEmpresaMasivoEntradaDtocs.Deuda);
            var pideLineasCredito = secciones.Contains(BuscadorEmpresaMasivoEntradaDtocs.LineasCredito);

            foreach (var lote in rucsValidos.Chunk(1000))
            {
                var batch = lote.ToList();

                if (pideMoviles)
                {
                    var moviles = await _db.Movil
                        .AsNoTracking()
                        .Where(x => x.Documento != null && batch.Contains(x.Documento))
                        .ToListAsync(ct);
                    result.Moviles.AddRange(moviles);
                }

                if (pideSueldos)
                {
                    var sueldos = await _db.Sueldos
                        .AsNoTracking()
                        .Where(x => x.Documento != null && batch.Contains(x.Documento))
                        .ToListAsync(ct);
                    result.Sueldos.AddRange(sueldos);
                }

                if (pideCalificacion)
                {
                    var calificaciones = await _db.Calificaciones
                        .AsNoTracking()
                        .Where(x => x.Documento != null && batch.Contains(x.Documento))
                        .ToListAsync(ct);
                    result.Calificaciones.AddRange(calificaciones);
                }

                if (pideDeuda)
                {
                    var deudas = await _db.Deudas
                        .AsNoTracking()
                        .Where(x => x.Documento != null && batch.Contains(x.Documento))
                        .ToListAsync(ct);
                    result.Deudas.AddRange(deudas);
                }

                if (pideLineasCredito)
                {
                    var lineas = await _db.LineaCreditos
                        .AsNoTracking()
                        .Where(x => x.Documento != null && batch.Contains(x.Documento))
                        .ToListAsync(ct);
                    result.LineasCredito.AddRange(lineas);
                }
            }

            return result;
        }
    }
}