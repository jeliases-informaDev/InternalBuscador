"""Reporte Cusco Extrajudicial - septiembre 2026. Solo SELECT (lectura).
Base: [Analitica].[Cusco].[ExtraJudicial_Asignacion] Periodo 202609; metricas: DBInforma.
Regla: ninguna cuenta de la base se descarta; sin dato => 0 o vacio."""
import os, re, pyodbc, pandas as pd
from openpyxl.styles import Font, PatternFill

BASE = r'C:\Users\INFORMA PERU\Downloads\CuscoExtrajudicialSetiembre.xlsx'
OUT = r'C:\Inoc\reportes\Reporte_Cusco_Extrajudicial_Setiembre_2026_v6.xlsx'
D1, D2 = pd.Timestamp('2026-09-01'), pd.Timestamp('2026-10-01')
S1, S2 = D1.strftime('%Y-%m-%d'), D2.strftime('%Y-%m-%d')
CONTACTO = ['CONTACTO DIRECTO', 'CONTACTO INDIRECTO', 'CONTACTADO']

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=192.168.1.18;DATABASE=DBInforma;"
    f"UID={os.environ['DB_USER']};PWD={os.environ['DB_PASS']};TrustServerCertificate=yes;Connection Timeout=15")


def q(sql, *p):
    return pd.read_sql(sql, conn, params=list(p) or None)


# ---- Base asignada (universo del reporte) ----
# Asignacion desde Analitica (login propio, solo SELECT)
conn_a = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=192.168.1.18;DATABASE=Analitica;"
    f"UID={os.environ['DBA_USER']};PWD={os.environ['DBA_PASS']};TrustServerCertificate=yes;Connection Timeout=15")
b = pd.read_sql("""SELECT Cuenta, Doc_Titular, Saldo_Capital, Telefono
FROM [Analitica].[Cusco].[ExtraJudicial_Asignacion] WHERE Periodo = '202609'""", conn_a)
conn_a.close()
base = pd.DataFrame({
    'pagare': b['Cuenta'].str.strip(),
    'dni': b['Doc_Titular'].str.strip().str.zfill(8),
    'saldo': pd.to_numeric(b['Saldo_Capital'], errors='coerce'),
    'tels': b['Telefono'].fillna('')})
assert base.pagare.is_unique, 'pagares duplicados en la base'

# ---- Gestiones Cusco Extrajudicial (todo el historial); septiembre se separa en pandas ----
hist = q("""SELECT LTRIM(RTRIM(NroCuenta)) pagare, FechaGestion, TipoContacto, telefono, Observacion
FROM Base.Gestiones WHERE NroCuenta IS NOT NULL AND Cartera LIKE '%CUSCO%EXTRA%'""")
hist = hist[hist.pagare.isin(base.pagare)].copy()
hist['contacto'] = hist.TipoContacto.isin(CONTACTO)
sep = hist[(hist.FechaGestion >= D1) & (hist.FechaGestion < D2)]


def fechas(df, suf):
    ug = df.groupby('pagare').FechaGestion.max().rename('UltGest' + suf)
    uc = df[df.contacto].groupby('pagare').FechaGestion.max().rename('UltCont' + suf)
    return pd.concat([ug, uc], axis=1)


r = base.set_index('pagare').join(fechas(sep, '_sep')).join(fechas(hist, '_hist'))
r['Llamadas'] = sep.groupby('pagare').size()
r['Llamadas'] = r.Llamadas.fillna(0).astype(int)
r = r.reset_index()

# ---- SMS (septiembre, campanas Cusco Extrajudicial) por telefono ----
cols = q("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='Base' AND TABLE_NAME='SMS'")['COLUMN_NAME'].tolist()
camp = [c for c in cols if c.upper().startswith('CAMPA')][0]
num = [c for c in cols if c.upper().startswith('N') and 'MERO' in c.upper()][0]
sms = q(f"""SELECT CAST(CAST([{num}] AS bigint) AS varchar(20)) tel, COUNT(*) n FROM Base.SMS
WHERE FECHA>=? AND FECHA<? AND [{camp}] LIKE '%CUSCO%EXTRA%' GROUP BY CAST(CAST([{num}] AS bigint) AS varchar(20))""", S1, S2)
last9 = lambda t: re.sub(r'\D', '', str(t))[-9:]
smsd = sms.assign(tel=sms.tel.map(last9)).groupby('tel').n.sum()
tb = base[['pagare', 'tels']].assign(tel=base.tels.str.split(r'[,;/ ]+')).explode('tel')
tg = sep[['pagare', 'telefono']].rename(columns={'telefono': 'tel'})
t = pd.concat([tb[['pagare', 'tel']], tg]).dropna()
t['tel'] = t.tel.map(last9)
t = t[t.tel.str.len() == 9].drop_duplicates()
t['sms'] = t.tel.map(smsd).fillna(0)
r = r.merge(t.groupby('pagare').sms.sum().rename('SMS').reset_index(), on='pagare', how='left')
r['SMS'] = r.SMS.fillna(0).astype(int)

# ---- IVR (septiembre, campanas CuscoExtrajudicial) por DNI ----
ivr = q("""SELECT LTRIM(RTRIM(Documento)) dni, COUNT(*) IVR FROM Ivr.Base
WHERE Fecha>=? AND Fecha<? AND NombredeCampania LIKE 'CuscoExtrajudicial%' GROUP BY LTRIM(RTRIM(Documento))""", S1, S2)
r['IVR'] = r.dni.map(ivr.assign(dni=ivr.dni.str.zfill(8)).set_index('dni').IVR).fillna(0).astype(int)
# WhatsApp: gestiones de septiembre cuya observacion indica envio por WhatsApp (WSP / WHATSAPP / WAPP)
wa = sep[sep.Observacion.fillna('').str.upper().str.contains(r'WSP|WHATS|WAPP|WS', regex=True)]
r['WhatsApp'] = r.pagare.map(wa.groupby('pagare').size()).fillna(0).astype(int)

# ---- Salida ----
out = r.rename(columns={
    'pagare': 'Pagaré', 'dni': 'DNI', 'saldo': 'Saldo Capital',
    'UltCont_sep': 'Fecha Último Contacto (Sep-2026)', 'UltGest_sep': 'Fecha Última Gestión (Sep-2026)',
    'SMS': 'Cant. SMS', 'IVR': 'Cant. IVR',
    'UltCont_hist': 'Último Contacto Histórico', 'UltGest_hist': 'Última Gestión Histórica'})[
    ['Pagaré', 'DNI', 'Saldo Capital', 'Fecha Último Contacto (Sep-2026)', 'Fecha Última Gestión (Sep-2026)',
     'Llamadas', 'Cant. SMS', 'WhatsApp', 'Cant. IVR', 'Último Contacto Histórico', 'Última Gestión Histórica']]
for c in ['Fecha Último Contacto (Sep-2026)', 'Fecha Última Gestión (Sep-2026)',
          'Último Contacto Histórico', 'Última Gestión Histórica']:
    out[c] = pd.to_datetime(out[c]).dt.strftime('%d/%m/%Y %H:%M')

# controles de integridad: no se pierde ni duplica ninguna cuenta
assert len(out) == len(base) and out['Pagaré'].is_unique
assert abs(out['Saldo Capital'].sum() - base.saldo.sum()) < 0.01

with pd.ExcelWriter(OUT, engine='openpyxl') as xw:
    out.to_excel(xw, index=False, sheet_name='Septiembre 2026')
    ws = xw.sheets['Septiembre 2026']
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='1F4E78')
    for col, w in zip('ABCDEFGHIJK', [22, 12, 14, 24, 24, 10, 10, 10, 10, 24, 24]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    for row in ws.iter_rows(min_row=2, min_col=3, max_col=3):
        row[0].number_format = '#,##0.00'

n = lambda c: out[c].notna().sum()
print(f"{len(out)} filas = base ({len(base)}) | saldo total {out['Saldo Capital'].sum():,.2f}")
print('Sep: con llamadas', (out.Llamadas > 0).sum(), '| ult.contacto', n('Fecha Último Contacto (Sep-2026)'),
      '| ult.gestion', n('Fecha Última Gestión (Sep-2026)'), '| SMS', (out['Cant. SMS'] > 0).sum(), '| IVR', (out['Cant. IVR'] > 0).sum(), '| WhatsApp', (out['WhatsApp'] > 0).sum())
print('Hist: ult.contacto', n('Último Contacto Histórico'), '| ult.gestion', n('Última Gestión Histórica'))
sin = out['Última Gestión Histórica'].isna() & (out['Cant. IVR'] == 0) & (out['Cant. SMS'] == 0)
print('Cuentas sin ninguna gestion/SMS/IVR (se mantienen):', sin.sum())
