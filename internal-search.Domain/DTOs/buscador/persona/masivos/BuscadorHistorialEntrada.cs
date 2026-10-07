using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Text;

namespace internal_search.Domain.DTOs.buscador.persona.masivos
{
    public class BuscadorHistorialEntrada : IValidatableObject
    {
        [Required(ErrorMessage = "El documento es obligatorio.")]
        public string Documento { get; set; }

        [Required(ErrorMessage = "El tipo de documento es obligatorio.")]
        public string TipoDocumento { get; set; }

        //[Required(ErrorMessage = "El período es obligatorio.")]
        //[RegularExpression(@"^\d{6}$", ErrorMessage = "El período debe tener formato YYYYMM (6 dígitos).")]
        //public string Periodo { get; set; }

        //[Required(ErrorMessage = "El teléfono es obligatorio.")]
        //[RegularExpression(@"^9[0-9]{8}$",
        //ErrorMessage = "El celular debe tener 9 dígitos y comenzar con 9.")]
        //public string Telefono { get; set; } = string.Empty;

        private static readonly Dictionary<string, int> LongitudesFijasPorTipo = new()
        {
            ["DNI"] = 8,
            ["RUC"] = 11,
        };

        public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
        {
            var tipo = TipoDocumento?.Trim().ToUpper();

            if (!LongitudesFijasPorTipo.TryGetValue(tipo ?? "", out var longitudEsperada))
            {
                yield return new ValidationResult(
                    $"Tipo de documento '{TipoDocumento}' no soportado.",
                    new[] { nameof(TipoDocumento) });
                yield break;
            }

            if (Documento?.Length != longitudEsperada)
            {
                yield return new ValidationResult(
                    $"El {tipo} debe contener exactamente {longitudEsperada} dígitos.",
                    new[] { nameof(Documento) });
            }

            if (!string.IsNullOrEmpty(Documento) && !Documento.All(char.IsDigit))
            {
                yield return new ValidationResult(
                    $"El {tipo} debe contener solo números.",
                    new[] { nameof(Documento) });
            }
        }
    }
}
