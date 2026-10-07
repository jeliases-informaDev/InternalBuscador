"""Genera un .sql con INSERTs del Excel hacia [Analitica].[Cusco].[ExtraJudicial_Asignacion] (Periodo 202609)."""
import pandas as pd, math
EXCEL = r'C:\Users\INFORMA PERU\Downloads\CuscoExtrajudicialSetiembre.xlsx'
OUT = r'C:\Inoc\reportes\cargar_asignacion_cusco_202609.sql'
COLS = ("REGION AGENCIA Producto Tipo Moneda Cuenta Titular Doc_Titular Telefono Departamento Provincia Distrito "
        "Domicilio Domicilio_Negocio Conyuge Doc_Conyuge Telefono_Conyuge Aval Doc_Aval Domicilio_Aval Telefono_Aval "
        "Saldo_Capital Interes Mora Gastos DEUDA_TOTAL RANG_K Anio_Transferencia Minimo_Cobrar_Sin_Campana "
        "Segmento_Campana DSC_CAPITAL Capital_DSC_Capital Monto_Cobrar_Campana Monto_Pago Fecha_Ultimo_Pago "
        "Fecha_Venta_Cartera Proceso_Venta Fecha_Transferencia Demanda Condicion Cuotas_Pagadas Negociado "
        "Monto_Negociado Cuotas_Negociadas Estudio_Juridico_Final Programas Tipo_Garantia Linea").split()
NUM = {'Saldo_Capital','Interes','Mora','Gastos','DEUDA_TOTAL','Anio_Transferencia','Minimo_Cobrar_Sin_Campana','DSC_CAPITAL',
       'Capital_DSC_Capital','Monto_Cobrar_Campana','Monto_Pago','Cuotas_Pagadas','Monto_Negociado','Cuotas_Negociadas'}
FEC = {'Fecha_Ultimo_Pago','Fecha_Venta_Cartera','Fecha_Transferencia'}

d = pd.read_excel(EXCEL)
assert len(d.columns) == 48
d.columns = COLS
assert d.Cuenta.is_unique

def lit(c, v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NaT or (isinstance(v, str) and v.strip() == ''):
        return 'NULL'
    if c in NUM:
        v = float(v)
        return str(int(v)) if v == int(v) and abs(v) < 1e15 else repr(v)
    if c in FEC:
        t = pd.to_datetime(v, dayfirst=True, errors='coerce')
        return 'NULL' if pd.isna(t) else f"'{t:%Y%m%d}'"
    s = str(v).strip().replace("'", "''")
    return f"N'{s}'"

lista = ','.join(COLS) + ',Periodo'
L = ["/* Carga CuscoExtrajudicialSetiembre -> [Analitica].[Cusco].[ExtraJudicial_Asignacion] | Periodo 202609",
     "   Solo INSERT (no borra ni actualiza). Omite cuentas ya existentes en el periodo.",
     "   PRUEBA por defecto (ROLLBACK). Para guardar: cambiar @Commit = 1 */",
     "USE Analitica; SET NOCOUNT ON; SET XACT_ABORT ON;",
     "DECLARE @Commit bit = 0;   -- 0 = prueba (revierte)  |  1 = guarda",
     f"DECLARE @Periodo varchar(6) = '202609';",
     "BEGIN TRAN;",
     f"SELECT TOP 0 {lista} INTO #stg FROM [Cusco].[ExtraJudicial_Asignacion];", ""]
rows = [f"({','.join(lit(c, v) for c, v in zip(COLS, r))},'202609')" for r in d.itertuples(index=False, name=None)]
for i in range(0, len(rows), 500):
    L.append(f"INSERT INTO #stg ({lista}) VALUES\n" + ",\n".join(rows[i:i+500]) + ";\n")
L += [f"""DECLARE @enExcel int = (SELECT COUNT(*) FROM #stg), @yaExisten int =
  (SELECT COUNT(*) FROM #stg s WHERE EXISTS (SELECT 1 FROM [Cusco].[ExtraJudicial_Asignacion] t WHERE t.Cuenta=s.Cuenta AND t.Periodo=@Periodo));
INSERT INTO [Cusco].[ExtraJudicial_Asignacion] ({lista})
SELECT {lista} FROM #stg s
WHERE NOT EXISTS (SELECT 1 FROM [Cusco].[ExtraJudicial_Asignacion] t WHERE t.Cuenta=s.Cuenta AND t.Periodo=@Periodo);
DECLARE @insertadas int = @@ROWCOUNT;
SELECT @enExcel AS filas_en_script, @yaExisten AS ya_existian_omitidas, @insertadas AS insertadas,
       (SELECT COUNT(*) FROM [Cusco].[ExtraJudicial_Asignacion] WHERE Periodo=@Periodo) AS total_periodo,
       (SELECT SUM(Saldo_Capital) FROM [Cusco].[ExtraJudicial_Asignacion] WHERE Periodo=@Periodo) AS saldo_capital_periodo;
-- Esperado: filas_en_script = {len(d)} | saldo capital del Excel = {d.Saldo_Capital.sum():,.2f}
IF @Commit = 1 BEGIN COMMIT; PRINT 'CONFIRMADO'; END ELSE BEGIN ROLLBACK; PRINT 'PRUEBA: se revirtio todo. Cambia @Commit = 1 para guardar.'; END
DROP TABLE IF EXISTS #stg;"""]
open(OUT, 'w', encoding='utf-8-sig').write('\n'.join(L))
print(len(d), 'filas |', round(__import__('os').path.getsize(OUT)/1e6, 1), 'MB | saldo', f'{d.Saldo_Capital.sum():,.2f}')
