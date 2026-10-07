using internal_search.Domain.DTOs.buscador.empresa.individual;
using internal_search.Domain.Entities;
using internal_search.Domain.Interfaces.Buscador.empresas.individual;
using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace internal_search_backend.Infraestructure.Repositories.Buscador.empresas.individual
{
    public class BuscadorIndividualRepository : IEmpresaIndividualRepository
    {
        private readonly AppDbContext _context;

        public BuscadorIndividualRepository(AppDbContext context)
        {
            _context = context;
        }

        public async Task<BuscadorEmpresaResponseDto> ObtenerTodasLasTablasPorRucAsync(string numeroDocumento)
        {
            // 1. Validación de seguridad en la entrada
            if (string.IsNullOrWhiteSpace(numeroDocumento) ||
                numeroDocumento.Length != 11 ||
                !numeroDocumento.StartsWith("20"))
            {
                throw new ArgumentException("El documento debe ser un RUC válido de 11 dígitos que empiece con 20.");
            }

            // 2. Ejecutar las consultas secuencialmente con await para proteger el DbContext
            var moviles = await _context.Movil
                .Where(x => x.Documento == numeroDocumento && x.Documento.Length == 11 && x.Documento.StartsWith("20"))
                .Take(10)
                .ToListAsync();

            var sueldos = await _context.Sueldos
                .Where(x => x.Documento == numeroDocumento && x.Documento.Length == 11 && x.Documento.StartsWith("20"))
                .Take(10)
                .ToListAsync();

            var deudas = await _context.Deudas
                .Where(x => x.Documento == numeroDocumento && x.Documento.Length == 11 && x.Documento.StartsWith("20"))
                .Take(10)
                .ToListAsync();

            var lineas = await _context.LineaCreditos
                .Where(x => x.Documento == numeroDocumento && x.Documento.Length == 11 && x.Documento.StartsWith("20"))
                .Take(10)
                .ToListAsync();

            var calificaciones = await _context.Calificaciones
                .Where(x => x.Documento == numeroDocumento && x.Documento.Length == 11 && x.Documento.StartsWith("20"))
                .Take(10)
                .ToListAsync();

            // 3. Retornar el objeto consolidado con los resultados ya obtenidos
            return new BuscadorEmpresaResponseDto
            {
                Moviles = moviles,
                Sueldos = sueldos,
                Deudas = deudas,
                LineasCredito = lineas,
                Calificaciones = calificaciones
            };
        }

        // 2. BÚSQUEDA POR RAZÓN SOCIAL (Parcial / LIKE)
        // ==========================================
        // 2. BÚSQUEDA POR RAZÓN SOCIAL (Optimizada y controlada)
        // 2. BÚSQUEDA POR RAZÓN SOCIAL (Optimizada con StartsWith para evitar timeouts)
        public async Task<BuscadorEmpresaResponseDto> ObtenerTodasLasTablasPorRazonSocialAsync(string razonSocial)
        {
            // Validación de seguridad: Exigir al menos 4 caracteres para obligar a mayor precisión
            if (string.IsNullOrWhiteSpace(razonSocial) || razonSocial.Trim().Length < 4)
            {
                throw new ArgumentException("Debe ingresar al menos 4 caracteres para buscar por razón social.");
            }

            string filtro = razonSocial.Trim();

            // Usamos StartsWith en lugar de Contains para que SQL use índices y no dé Timeout
            var deudas = await _context.Deudas
                .AsNoTracking()
                .Where(x => x.RazonSocial != null && x.RazonSocial.StartsWith(filtro))
                .Take(50)
                .ToListAsync();

            var lineas = await _context.LineaCreditos
                .AsNoTracking()
                .Where(x => x.RazonSocial != null && x.RazonSocial.StartsWith(filtro))
                .Take(50)
                .ToListAsync();

            return new BuscadorEmpresaResponseDto
            {
                Moviles = new List<Movil>(),
                Sueldos = new List<Sueldo>(),
                Deudas = deudas,
                LineasCredito = lineas,
                Calificaciones = new List<Calificacion>()
            };
        }
    }
}