"""Carga CuscoExtrajudicialSetiembre.xlsx en [Analitica].[Cusco].[ExtraJudicial_Asignacion] (Periodo 202609).
Solo INSERT: no hace DELETE/TRUNCATE/UPDATE. Omite cuentas que ya existan en ese periodo.
Por defecto es PRUEBA (rollback). Para confirmar: python cargar_asignacion_cusco.py --commit"""
import os, sys, pyodbc, pandas as pd

EXCEL = r'C:\Users\INFORMA PERU\Downloads\CuscoExtrajudicialSetiembre.xlsx'
TABLA = '[Analitica].[Cusco].[ExtraJudicial_Asignacion]'
PERIODO = '202609'
COMMIT = '--commit' in sys.argv
COLS = ("REGION AGENCIA Producto Tipo Moneda Cuenta Titular Doc_Titular Telefono Departamento Provincia Distrito "
        "Domicilio Domicilio_Negocio Conyuge Doc_Conyuge Telefono_Conyuge Aval Doc_Aval Domicilio_Aval Telefono_Aval "
        "Saldo_Capital Interes Mora Gastos DEUDA_TOTAL RANG_K Anio_Transferencia Minimo_Cobrar_Sin_Campana "
        "Segmento_Campana DSC_CAPITAL Capital_DSC_Capital Monto_Cobrar_Campana Monto_Pago Fecha_Ultimo_Pago "
        "Fecha_Venta_Cartera Proceso_Venta Fecha_Transferencia Demanda Condicion Cuotas_Pagadas Negociado "
        "Monto_Negociado Cuotas_Negociadas Estudio_Juridico_Final Programas Tipo_Garantia Linea").split()

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=192.168.1.18;DATABASE=Analitica;"
    f"UID={os.environ['DB_USER']};PWD={os.environ['DB_PASS']};TrustServerCertificate=yes;Connection Timeout=15",
    autocommit=False)
cur = conn.cursor()

# tipos reales de la tabla, para convertir cada columna
tipos = {r[0]: r[1] for r in cur.execute(
    "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='Cusco' AND TABLE_NAME='ExtraJudicial_Asignacion'")}
faltan = [c for c in COLS + ['Periodo'] if c not in tipos]
assert not faltan, f'columnas que no existen en la tabla: {faltan}'

df = pd.read_excel(EXCEL, dtype=str)
assert len(df.columns) == len(COLS), 'el Excel no tiene 48 columnas'
df.columns = COLS
df = df.apply(lambda s: s.str.strip())

NUM = {'decimal', 'numeric', 'float', 'real', 'money', 'smallmoney', 'int', 'bigint', 'smallint', 'tinyint'}
FEC = {'date', 'datetime', 'datetime2', 'smalldatetime'}
for c in COLS:
    t = tipos[c]
    if t in NUM:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    elif t in FEC:
        df[c] = pd.to_datetime(df[c], errors='coerce', dayfirst=True)
df['Periodo'] = PERIODO

existentes = {r[0] for r in cur.execute(f"SELECT LTRIM(RTRIM(Cuenta)) FROM {TABLA} WHERE Periodo=?", PERIODO)}
nuevos = df[~df.Cuenta.isin(existentes)]
print(f'Excel: {len(df)} | ya existen en {PERIODO}: {len(df) - len(nuevos)} | a insertar: {len(nuevos)}')

todas = COLS + ['Periodo']
sql = f"INSERT INTO {TABLA} ({','.join(todas)}) VALUES ({','.join('?' * len(todas))})"
filas = [[None if pd.isna(v) else (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for v in row]
         for row in nuevos[todas].itertuples(index=False, name=None)]
cur.fast_executemany = True
cur.executemany(sql, filas)

total = cur.execute(f"SELECT COUNT(*), SUM(Saldo_Capital) FROM {TABLA} WHERE Periodo=?", PERIODO).fetchone()
print(f'En tabla para {PERIODO}: {total[0]} filas | saldo capital {total[1]}')
if COMMIT:
    conn.commit(); print('CONFIRMADO (commit).')
else:
    conn.rollback(); print('PRUEBA: se revirtió todo (no se guardó nada). Usa --commit para guardar.')
