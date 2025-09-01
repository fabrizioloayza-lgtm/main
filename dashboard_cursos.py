# dashboard_cursos_tecsup.py
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import base64
from pathlib import Path
from datetime import date

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="Dashboard TECSUP - Capacitación", page_icon="📊", layout="wide")

# paletas según modo
PLOTLY_TEMPLATE = "simple_white"
COLOR_PRIMARIO = "#00A6E0"   # TECSUP celeste
COLOR_OK       = "#16A34A"
COLOR_BAD      = "#DC2626"
COLOR_ACCENT   = "#0EA5E9"

COLOR_PRIMARIO = "#00A6E0"   # se mantiene
COLOR_OK = "#22C55E"
COLOR_BAD = "#F87171"
COLOR_ACCENT = "#60A5FA"


# ===============================
# ESTILOS (sin logo fijo)
# ===============================
st.markdown("""
<style>
:root{
  --card:#FFFFFF; --muted:#64748B; --ink:#0F172A; --primary:#00A6E0;
}
html,body,[class*="css"]{font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;}
/* HERO con logo y título en el mismo contenedor */
.hero{
  border-radius: 18px;
  padding: 14px 18px;
  background: radial-gradient(1200px 260px at 8% 0%, #E0F4FF 0%, #FFFFFF 45%, #FFFFFF 100%);
  border: 1px solid #D9EEF9;
  box-shadow: 0 6px 22px rgba(15,23,42,.05);
  margin: 0 0 12px 0;
}
.hero-row{ display:flex; align-items:center; gap:14px; }
.hero-logo{
  display:flex; align-items:center; justify-content:center;
  width:56px; height:56px; border-radius:12px;
  background:#E6F6FD; border:1px solid #D9EEF9; overflow:hidden;
}
.hero-logo img{ width:48px; height:48px; object-fit:contain; }
.hero-title{ font-size:22px; font-weight:900; margin:0; color:var(--ink); }
.hero-sub{ margin:4px 0 0 0; color:var(--muted); }

/* KPI cards */
.kpi{
  border:1px solid #E6E9EF; border-radius:16px; background:#FFF; padding:18px;
  box-shadow:0 6px 18px rgba(15,23,42,.06);
}
.kpi .label{ color:#64748B; font-size:13px; }
.kpi .value{ font-size:28px; font-weight:900; color:#0F172A; }
.kpi .delta{ font-size:12px; color:#0EA5E9; margin-top:6px; }

/* Sidebar */
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, #F5F7FA 0%, #FFFFFF 100%);
  border-right:1px solid #E6E9EF;
}
</style>
""", unsafe_allow_html=True)


# ===============================
# UTIL: cargar logo (base64) desde varias rutas comunes
# ===============================
def load_logo_b64():
    candidates = [
        Path(__file__).parent / "tecsup.png",
        Path(__file__).parent / "assets" / "tecsup.png",
        Path(__file__).parent / ".streamlit" / "assets" / "tecsup.png",
    ]
    for p in candidates:
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode("utf-8")
    return None

logo_b64 = load_logo_b64()

# ===============================
# HERO (logo + título dentro del mismo contenedor)
# ===============================
st.markdown(
    f"""
    <div class="hero">
      <div class="hero-row">
        <div class="hero-logo">
          {"<img src='data:image/png;base64,"+logo_b64+"'/>" if logo_b64 else ""}
        </div>
        <div>
          <h3 class="hero-title">Dashboard de Capacitación — TECSUP</h3>
          <p class="hero-sub">Reporte ejecutivo con KPIs, calidad y desglose por empresa/curso. Fecha: {date.today().strftime('%d/%m/%Y')}</p>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ===============================
# DATOS (Google Sheets CSV público)
# ===============================
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1XobpyubcsSoBXPJyqMxdWXZLDTufKjl3b6XHPWtuzqY/export?format=csv&gid=0"  # <-- tu URL CSV

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(SHEET_CSV_URL)

    # Normaliza encabezados
    def norm(s):
        s = str(s).replace("\n"," ")
        s = " ".join(s.split())
        return (s.lower()
                .replace("á","a").replace("é","e").replace("í","i")
                .replace("ó","o").replace("ú","u"))
    df.columns = [norm(c) for c in df.columns]

    # Map a nombres canónicos
    aliases = {
        "empresa":"Empresa","curso":"Curso","nombre del curso":"Curso",
        "horas":"Horas","fecha":"Fecha","modalidad":"Modalidad","estado":"Estado",
        "docente":"Docente","cantidad de participantes":"Participantes","participantes":"Participantes",
        "aprobados":"Aprobados","desaprobados":"Desaprobados","encuestas":"Encuestas"
    }
    df = df.rename(columns={c:aliases.get(c,c.title()) for c in df.columns})

    # Numéricos
    for col in ["Horas","Participantes","Aprobados","Desaprobados"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Fecha_inicio para filtros
    def parse_first_date(s):
        s = str(s)
        if "-" in s or " y " in s:
            token = s.split("-")[0].split(" y ")[0].strip()
            return pd.to_datetime(token, dayfirst=True, errors="coerce")
        return pd.to_datetime(s, dayfirst=True, errors="coerce")
    if "Fecha" in df.columns:
        df["Fecha_inicio"] = df["Fecha"].apply(parse_first_date)

    # Limpieza básica
    for c in ["Empresa","Curso","Modalidad","Estado","Docente","Encuestas"]:
        if c in df.columns:
            df[c] = df[c].fillna("")
    return df

df = load_data()

# ===============================
# FILTROS
# ===============================
st.sidebar.header("Filtros")
empresas = st.sidebar.multiselect("Empresa", sorted(df["Empresa"].unique()), default=sorted(df["Empresa"].unique()))
modalidades = st.sidebar.multiselect("Modalidad", sorted(df["Modalidad"].unique()), default=sorted(df["Modalidad"].unique()))
estados = st.sidebar.multiselect("Estado", sorted(df["Estado"].unique()), default=sorted(df["Estado"].unique()))

min_f = pd.to_datetime(df["Fecha_inicio"].min())
max_f = pd.to_datetime(df["Fecha_inicio"].max())
rango = st.sidebar.date_input("Rango de fechas", (min_f, max_f))
if isinstance(rango, tuple) and len(rango)==2:
    f_ini, f_fin = pd.to_datetime(rango[0]), pd.to_datetime(rango[1])
else:
    f_ini, f_fin = min_f, max_f

df_f = df[
    df["Empresa"].isin(empresas) &
    df["Modalidad"].isin(modalidades) &
    df["Estado"].isin(estados) &
    (df["Fecha_inicio"].between(f_ini, f_fin))
].copy()

# ===============================
# KPIs
# ===============================
total_cursos = df_f["Curso"].nunique() if "Curso" in df_f.columns else 0
total_part = int(df_f["Participantes"].sum()) if "Participantes" in df_f.columns else 0
tasa_aprob = (df_f["Aprobados"].sum()/df_f["Participantes"].sum()*100) if total_part>0 else 0
horas_tot = int(df_f["Horas"].sum()) if "Horas" in df_f.columns else 0

k1,k2,k3,k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class="kpi"><div class="label">Total de cursos</div><div class="value">{total_cursos}</div><div class="delta">Periodo: {f_ini.date()} → {f_fin.date()}</div></div>""", unsafe_allow_html=True)
with k2:
    prom = (total_part/total_cursos if total_cursos else 0)
    st.markdown(f"""<div class="kpi"><div class="label">Total participantes</div><div class="value">{total_part}</div><div class="delta">Promedio/curso: {prom:.1f}</div></div>""", unsafe_allow_html=True)
with k3:
    color = COLOR_OK if tasa_aprob>=85 else COLOR_ACCENT if tasa_aprob>=75 else COLOR_BAD
    st.markdown(f"""<div class="kpi"><div class="label">Tasa de aprobación</div><div class="value">{tasa_aprob:.1f}%</div><div class="delta" style="color:{color}">Meta: 85%</div></div>""", unsafe_allow_html=True)
with k4:
    mods = ", ".join(sorted(df_f["Modalidad"].unique())) if "Modalidad" in df_f.columns else "-"
    st.markdown(f"""<div class="kpi"><div class="label">Horas dictadas</div><div class="value">{horas_tot}</div><div class="delta">Modalidades: {mods}</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# ===============================
# TABS
# ===============================
tab1, tab2, tab3, tab4 = st.tabs(["🔎 Resumen", "🏢 Por Empresa", "📚 Por Curso", "🧪 Calidad"])

# --- TAB 1: Resumen ---
with tab1:
    colL, colR = st.columns([1, 1], gap="large")

    # ---- FIGURA 1 (IZQUIERDA): Cursos por empresa (barras verticales) ----
    with colL:
        vc = (df_f["Empresa"].value_counts()
              .rename_axis("Empresa")
              .reset_index(name="Cursos")
              .sort_values("Cursos", ascending=False))

        fig1 = px.bar(
            vc, x="Empresa", y="Cursos",
            color="Cursos",
            color_continuous_scale=["#9BDCF2", COLOR_PRIMARIO],
            template=PLOTLY_TEMPLATE,
            title="Cantidad de cursos por empresa"
        )
        fig1.update_traces(
            text=vc["Cursos"],
            texttemplate="<b>%{text}</b>",
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=19, color="white"),
            cliponaxis=False
        )
        fig1.update_layout(
            xaxis_title="", yaxis_title="Cursos",
            coloraxis_showscale=False,
            uniformtext_minsize=12, uniformtext_mode="hide",
            bargap=0.25
        )
        st.plotly_chart(fig1, use_container_width=True)

    # ---- FIGURA 2 (DERECHA): Participantes por empresa (barras horizontales) ----
    with colR:
        part_emp = (df_f.groupby("Empresa")["Participantes"]
                    .sum().reset_index()
                    .sort_values("Participantes", ascending=True))

        fig2 = px.bar(
            part_emp, y="Empresa", x="Participantes",
            orientation="h",
            color="Participantes",
            color_continuous_scale=["#BAF2E1","#10B981"],
            template=PLOTLY_TEMPLATE,
            title="Participantes por empresa"
        )
        fig2.update_traces(
            text=part_emp["Participantes"],
            texttemplate="<b>%{text}</b>",
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=20, color="white")
        )
        fig2.update_layout(
            xaxis_title="Participantes", yaxis_title="",
            coloraxis_showscale=False,
            uniformtext_minsize=12, uniformtext_mode="hide"
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Rendimiento por empresa")
    apilado = (df_f.groupby("Empresa")[["Aprobados","Desaprobados"]]
               .sum().reset_index().sort_values("Aprobados", ascending=False))
    fig3 = go.Figure()
    fig3.add_bar(name="Aprobados", x=apilado["Empresa"], y=apilado["Aprobados"], marker_color=COLOR_OK)
    fig3.add_bar(name="Desaprobados", x=apilado["Empresa"], y=apilado["Desaprobados"], marker_color=COLOR_BAD)
    fig3.update_layout(barmode="stack", template=PLOTLY_TEMPLATE, xaxis_title="", yaxis_title="Personas", legend_title_text="")
    st.plotly_chart(fig3, use_container_width=True)

    tasas = (df_f.groupby("Empresa")[["Aprobados","Participantes"]]
         .sum().reset_index())
    tasas = tasas[tasas["Participantes"] > 0].copy()
    tasas["Tasa_%"] = (tasas["Aprobados"] / tasas["Participantes"] * 100).round(1)
    tasas = tasas.sort_values("Tasa_%", ascending=False)

    fig_tasa = px.bar(
        tasas, x="Empresa", y="Tasa_%",
        color="Tasa_%",
        color_continuous_scale=["#FCD34D", "#22C55E"],
        template=PLOTLY_TEMPLATE,
        title="Tasa de aprobación por empresa (%)"
    )
    fig_tasa.update_traces(
        text=tasas["Tasa_%"].astype(str) + "%",
        texttemplate="<b>%{text}</b>",
        textposition="inside",
        insidetextanchor="middle",
    )
    fig_tasa.update_layout(
        xaxis_title="", yaxis_title="%",
        coloraxis_showscale=False, yaxis_range=[0, 100]
    )
    st.plotly_chart(fig_tasa, use_container_width=True)

# --- TAB 2: Por Empresa ---
with tab2:
    emp_sel = st.selectbox("Empresa", ["(Todas)"] + list(sorted(df_f["Empresa"].unique())))
    df_emp = df_f if emp_sel=="(Todas)" else df_f[df_f["Empresa"]==emp_sel]

    c3, c4 = st.columns(2, gap="large")
    with c3:
        horas_emp = df_emp.groupby("Empresa")["Horas"].sum().reset_index()
        fig4 = px.bar(horas_emp, x="Empresa", y="Horas",
                      title="Horas totales por empresa", template=PLOTLY_TEMPLATE,
                      color="Horas", color_continuous_scale=["#B3E9F8", COLOR_PRIMARIO])
        fig4.update_layout(xaxis_title="", yaxis_title="Horas", coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)
    with c4:
        doc_rank = (df_emp.groupby("Docente")[["Participantes","Aprobados"]]
                    .sum().reset_index().sort_values("Participantes", ascending=False)[:10])
        fig5 = px.bar(doc_rank, x="Docente", y="Participantes",
                      color="Aprobados", title="Top docentes por participantes",
                      template=PLOTLY_TEMPLATE, color_continuous_scale=["#D1FAE5","#10B981"])
        fig5.update_layout(xaxis_title="", yaxis_title="Participantes", coloraxis_showscale=False)
        st.plotly_chart(fig5, use_container_width=True)

    st.subheader("Detalle")
    st.dataframe(df_emp.sort_values(["Empresa","Fecha_inicio","Curso"]), use_container_width=True)

# --- TAB 3: Por Curso ---
with tab3:
    st.subheader("Estado de ejecución de cursos")

    # Controles
    estados_disponibles = sorted(df_f["Estado"].dropna().unique())
    estados_sel = st.multiselect("Mostrar estados", estados_disponibles, default=estados_disponibles)
    q = st.text_input("Buscar (curso / empresa / docente)", "")

    # Datos base + tasa
    df_tab = df_f.copy()
    if "Participantes" in df_tab and "Aprobados" in df_tab:
        df_tab["Tasa_%"] = (df_tab["Aprobados"] / df_tab["Participantes"] * 100).round(1).fillna(0)

    # Filtros
    df_tab = df_tab[df_tab["Estado"].isin(estados_sel)]
    if q:
        qlow = q.lower()
        df_tab = df_tab[
            df_tab["Curso"].str.lower().str.contains(qlow, na=False) |
            df_tab["Empresa"].str.lower().str.contains(qlow, na=False) |
            df_tab["Docente"].str.lower().str.contains(qlow, na=False)
        ]

    # Orden y columnas visibles
    cols = ["Empresa","Curso","Docente","Modalidad","Horas","Fecha","Estado",
            "Participantes","Aprobados","Desaprobados","Tasa_%"]
    cols = [c for c in cols if c in df_tab.columns]
    df_show = df_tab[cols].sort_values(["Estado","Empresa","Curso"])

    # Resumen rápido
    cA, cB, cC = st.columns(3)
    with cA: st.metric("Cursos (total)", df_show.shape[0])
    with cB: st.metric("Ejecutados", int((df_show["Estado"]=="Ejecutado").sum()))
    with cC: st.metric("En Proceso", int((df_show["Estado"].str.contains("Proceso", case=False, na=False)).sum()))

    # Tabla interactiva (no editable) con formato
    st.data_editor(
        df_show,
        use_container_width=True,
        hide_index=True,
        disabled=True,
        column_config={
            "Horas": st.column_config.NumberColumn("Horas", format="%d"),
            "Participantes": st.column_config.NumberColumn("Participantes", format="%d"),
            "Aprobados": st.column_config.NumberColumn("Aprobados", format="%d"),
            "Desaprobados": st.column_config.NumberColumn("Desaprobados", format="%d"),
            "Tasa_%": st.column_config.ProgressColumn(
                "Tasa de aprobación",
                help="Aprobados / Participantes",
                format="%.1f%%",
                min_value=0, max_value=100
            ),
        }
    )

    # Descarga del resultado filtrado
    st.download_button(
        "⬇️ Descargar tabla (CSV)",
        df_show.to_csv(index=False).encode("utf-8-sig"),
        "cursos_estado_ejecucion.csv",
        "text/csv"
    )

# --- TAB 4: Calidad ---
with tab4:
    st.caption("Las encuestas con ‘-%’ no reportan dato; se excluyen del promedio.")
    def pct_to_num(x):
        try: return float(str(x).replace("%",""))
        except: return None
    df_q = df_f.copy()
    df_q["Encuestas_num"] = df_q["Encuestas"].apply(pct_to_num)

    prom_general = df_q["Encuestas_num"].dropna().mean()
    colQ1, colQ2 = st.columns(2, gap="large")

    with colQ1:
        val = prom_general if pd.notnull(prom_general) else 0
        fig_ind = go.Figure(go.Indicator(
            mode="gauge+number",
            value=val,
            number={'suffix': "%", 'valueformat': ".1f"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': COLOR_PRIMARIO},
                'steps': [
                    {'range': [0, 70], 'color': '#FEE2E2'},
                    {'range': [70, 85], 'color': '#FEF3C7'},
                    {'range': [85, 100], 'color': '#DCFCE7'}
                ],
                'threshold': {'line': {'color': COLOR_OK, 'width': 4}, 'thickness': .75, 'value': 85}
            }
        ))
        fig_ind.update_layout(title="Satisfacción promedio (encuestas)", template=PLOTLY_TEMPLATE, height=300)
        st.plotly_chart(fig_ind, use_container_width=True)

    with colQ2:
        q_emp = (df_q.dropna(subset=["Encuestas_num"])
                 .groupby("Empresa")["Encuestas_num"].mean().reset_index())
        if not q_emp.empty:
            fig_q = px.bar(q_emp.sort_values("Encuestas_num", ascending=False),
                           x="Empresa", y="Encuestas_num",
                           title="Encuesta promedio por empresa",
                           template=PLOTLY_TEMPLATE, color="Encuestas_num",
                           color_continuous_scale=["#D1FAE5","#10B981"])
            fig_q.update_layout(xaxis_title="", yaxis_title="%", coloraxis_showscale=False)
            st.plotly_chart(fig_q, use_container_width=True)
        else:
            st.info("No hay datos válidos de encuestas en el filtro actual.")

# ===============================
# DESCARGA
# ===============================
st.markdown("---")
csv = df_f.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Descargar datos filtrados (CSV)", csv, "cursos_filtrados.csv", "text/csv")
