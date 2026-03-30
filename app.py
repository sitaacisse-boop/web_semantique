"""
app.py — Interface Streamlit moderne
Résumé RDF orienté requêtes — Dataset SWDF
Lancer : streamlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import warnings; warnings.filterwarnings("ignore")
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import networkx as nx

from src.schema_graph import RDFSchemaGraph
from src.query_parser import SPARQLQueryParser, load_queries
from src.subgraph_builder import SubgraphBuilder
from src.importance import (compute_external_connectivity,
                             compute_diversity, compute_importance_scores)
from src.summarizer import select_top_k, connect_subgraphs
from src.evaluator import compute_coverage, compute_compactness

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG + CSS
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Résumé RDF — SWDF", page_icon="🔗", layout="wide")

st.markdown("""
<style>
/* Fond général */
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"]          { background: #1a1d27; border-right: 1px solid #2d3047; }

/* Titres */
h1 { background: linear-gradient(90deg,#4f8ef7,#a78bfa);
     -webkit-background-clip:text; -webkit-text-fill-color:transparent;
     font-size:2.2rem !important; font-weight:800 !important; }
h2 { color:#e2e8f0 !important; font-size:1.3rem !important; margin-top:1.2rem !important; }
h3 { color:#94a3b8 !important; font-size:1rem !important; }

/* Métriques */
[data-testid="metric-container"] {
    background: #1e2235; border:1px solid #2d3047;
    border-radius:12px; padding:16px; }
[data-testid="stMetricValue"]  { color:#4f8ef7 !important; font-size:1.8rem !important; }
[data-testid="stMetricDelta"]  { color:#94a3b8 !important; }
[data-testid="stMetricLabel"]  { color:#cbd5e1 !important; }

/* Cards */
.card {
    background:#1e2235; border:1px solid #2d3047; border-radius:14px;
    padding:20px; margin:8px 0; }

/* Bouton principal */
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg,#4f8ef7,#7c3aed) !important;
    border:none !important; border-radius:10px !important;
    font-weight:700 !important; font-size:1rem !important;
    padding:14px !important; box-shadow:0 4px 15px rgba(79,142,247,.4) !important; }

/* Tabs */
[data-baseweb="tab-list"]  { background:#1a1d27; border-radius:10px; gap:4px; }
[data-baseweb="tab"]       { border-radius:8px !important; color:#94a3b8 !important; }
[aria-selected="true"]     { background:#4f8ef7 !important; color:#fff !important; }

/* Sliders */
[data-testid="stSlider"] > div > div > div > div { background:#4f8ef7 !important; }

/* Dataframe */
[data-testid="stDataFrame"] { border-radius:10px; overflow:hidden; }

/* Divider */
hr { border-color:#2d3047 !important; margin:1rem 0 !important; }

/* Info/success/warning */
[data-testid="stAlert"] { border-radius:10px !important; }

.badge-selected { color:#4ade80; font-weight:700; }
.badge-skip     { color:#94a3b8; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_schema(path):
    return RDFSchemaGraph(path, fmt="turtle")

@st.cache_data
def load_query_list(path):
    return load_queries(path)

@st.cache_data
def run_pipeline(schema_path, queries_path, k, alpha, beta, gamma):
    schema    = load_schema(schema_path)
    queries   = load_query_list(queries_path)
    parser    = SPARQLQueryParser(schema)
    bgps      = [parser.extract_bgp(q) for q in queries]
    builder   = SubgraphBuilder(schema)
    subgraphs = builder.build_all(bgps)
    ranked    = compute_importance_scores(subgraphs, schema, len(queries), alpha, beta, gamma)
    selected  = select_top_k(ranked, k)
    summary   = connect_subgraphs(selected, schema)
    return subgraphs, ranked, selected, summary

# ─────────────────────────────────────────────────────────────
# GRAPHE PLOTLY INTERACTIF
# ─────────────────────────────────────────────────────────────
def plotly_graph(G, title, node_color="#4f8ef7", highlight=None):
    if G.number_of_nodes() == 0:
        return go.Figure().add_annotation(text="Graphe vide",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#94a3b8"))

    pos = nx.spring_layout(G, seed=42, k=2.5)
    highlight = highlight or set()

    # Arêtes
    edge_x, edge_y, edge_text_x, edge_text_y, edge_labels = [], [], [], [], []
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x += [x0, x1, None]; edge_y += [y0, y1, None]
        edge_text_x.append((x0+x1)/2); edge_text_y.append((y0+y1)/2)
        edge_labels.append(data.get("property","").split("#")[-1].split("/")[-1])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#4a5568", width=1.5), hoverinfo="none")

    edge_label_trace = go.Scatter(
        x=edge_text_x, y=edge_text_y, mode="text",
        text=edge_labels,
        textfont=dict(size=9, color="#94a3b8"),
        hoverinfo="none")

    # Nœuds
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_labels = [n.split("#")[-1].split("/")[-1] for n in G.nodes()]
    node_colors = [("#f59e0b" if n in highlight else node_color) for n in G.nodes()]
    node_sizes  = [22 if n in highlight else 18 for n in G.nodes()]

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=node_labels, textposition="top center",
        textfont=dict(size=10, color="#e2e8f0"),
        marker=dict(size=node_sizes, color=node_colors,
                    line=dict(color="#1e2235", width=2),
                    symbol="circle"),
        hovertemplate="<b>%{text}</b><extra></extra>")

    fig = go.Figure(data=[edge_trace, edge_label_trace, node_trace])
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#e2e8f0"), x=0.5),
        paper_bgcolor="#1e2235", plot_bgcolor="#1e2235",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=50, b=20),
        height=400,
    )
    return fig

# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.title("🔗 Résumé RDF orienté requêtes")
st.markdown(
    "<p style='color:#64748b;margin-top:-10px'>Dataset SWDF · Ontologie SWC 2009 · "
    "Logs LSQ — <i>Approche Section 7</i></p>",
    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='color:#e2e8f0;margin-bottom:4px'>⚙️ Paramètres</h2>",
                unsafe_allow_html=True)

    st.markdown("**Fichiers**")
    schema_path  = "data/swdf_schema.ttl"
    queries_path = "data/swdf_queries.txt"
    st.markdown(f"<small style='color:#64748b'>📄 {schema_path}</small>", unsafe_allow_html=True)
    st.markdown(f"<small style='color:#64748b'>📄 {queries_path}</small>", unsafe_allow_html=True)

    st.divider()
    st.markdown("**Sélection top-k**")
    k = st.slider("Nombre de sous-graphes k", 1, 14, 5,
                  help="Plus k est grand → plus de coverage, moins de compacité")

    st.divider()
    st.markdown("**Poids I(S)**")
    st.caption("α + β  ≤ 1  →  γ = 1 − α − β  (calculé automatiquement)")
    alpha = st.slider("α  fréquence d'usage",     0.0, 1.0, 0.5, 0.05)
    beta  = st.slider("β  connectivité externe",  0.0, 1.0-alpha, 0.3, 0.05)
    gamma = round(1.0 - alpha - beta, 2)

    st.markdown(
        f"<div style='background:#1e3a5f;border-radius:8px;padding:10px;text-align:center'>"
        f"α = <b>{alpha}</b> &nbsp;|&nbsp; β = <b>{beta}</b> &nbsp;|&nbsp; "
        f"γ = <b style='color:#4f8ef7'>{gamma}</b></div>",
        unsafe_allow_html=True)

    st.divider()
    run = st.button("▶️  Lancer le pipeline", use_container_width=True, type="primary")

# ─────────────────────────────────────────────────────────────
# CHARGEMENT SCHEMA (toujours visible)
# ─────────────────────────────────────────────────────────────
schema  = load_schema(schema_path)
queries = load_query_list(queries_path)

# ─────────────────────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "   📊  Schéma   ",
    "   ⚙️  Pipeline   ",
    "   📈  Évaluation   ",
    "   🔬  Analyse   ",
])

# ══════════════════════════════════════════════
# ONGLET 1 — SCHEMA
# ══════════════════════════════════════════════
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Classes",    len(schema.classes()))
    c2.metric("Propriétés", len(schema.properties()))
    c3.metric("Requêtes",   len(queries))

    # Graphe en pleine largeur
    fig_schema = plotly_graph(
        schema.schema,
        f"Schéma SWDF complet — {len(schema.classes())} classes · {len(schema.properties())} propriétés",
        node_color="#4f8ef7")
    fig_schema.update_layout(height=480)
    st.plotly_chart(fig_schema, use_container_width=True)

    # Classes et propriétés côte à côte en dessous
    col_cls, col_prop = st.columns(2)
    with col_cls:
        classes_list = sorted([c.split("#")[-1].split("/")[-1] for c in schema.classes()])
        badges = " &nbsp; ".join(
            f"<span style='background:#2d1f5e;color:#a78bfa;padding:3px 8px;"
            f"border-radius:6px;font-size:0.82rem'>{c}</span>"
            for c in classes_list)
        st.markdown(f"**Classes ({len(classes_list)})**", unsafe_allow_html=True)
        st.markdown(f"<div style='line-height:2.2'>{badges}</div>", unsafe_allow_html=True)
    with col_prop:
        props_list = sorted([p.split("#")[-1].split("/")[-1] for p in schema.properties()])
        badges_p = " &nbsp; ".join(
            f"<span style='background:#1a3a5c;color:#4f8ef7;padding:3px 8px;"
            f"border-radius:6px;font-size:0.82rem'>→ {p}</span>"
            for p in props_list)
        st.markdown(f"**Propriétés ({len(props_list)})**", unsafe_allow_html=True)
        st.markdown(f"<div style='line-height:2.2'>{badges_p}</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# ONGLET 2 — PIPELINE
# ══════════════════════════════════════════════
with tab2:
    if not run and not st.session_state.get("ran"):
        st.markdown("""
        <div class='card' style='text-align:center;padding:40px'>
            <div style='font-size:3rem'>▶️</div>
            <h2 style='color:#e2e8f0'>Prêt à lancer</h2>
            <p style='color:#64748b'>Configurez les paramètres dans la barre latérale
            puis cliquez sur <b>Lancer le pipeline</b></p>
        </div>""", unsafe_allow_html=True)
    else:
        if run:
            with st.spinner("⏳ Pipeline en cours..."):
                subgraphs, ranked, selected, summary = run_pipeline(
                    schema_path, queries_path, k, alpha, beta, gamma)
            st.session_state.update({"subgraphs": subgraphs, "ranked": ranked,
                                     "selected": selected, "summary": summary,
                                     "ran": True, "k": k, "alpha": alpha,
                                     "beta": beta, "gamma": gamma})
        else:
            subgraphs = st.session_state["subgraphs"]
            ranked    = st.session_state["ranked"]
            selected  = st.session_state["selected"]
            summary   = st.session_state["summary"]

        st.success(f"✅  Résumé produit — **{summary.number_of_nodes()} nœuds** · **{summary.number_of_edges()} arêtes**")

        # ── Tableau des scores ──
        st.markdown("#### Scores d'importance I(S)")
        rows = []
        selected_sigs = {sq.signature() for sq in selected}
        for rank, (sq, score) in enumerate(ranked, 1):
            cls  = ", ".join(c.split("#")[-1].split("/")[-1] for c in sorted(sq.classes))
            prop = ", ".join(p.split("#")[-1].split("/")[-1] for p in sorted(sq.properties))
            rows.append({
                "Rang": rank,
                "Sélectionné": "✅" if sq.signature() in selected_sigs else "·",
                "Score I(S)": round(score, 4),
                "freq_n": round(sq.freq / len(queries), 4),
                "EC_n": round(compute_external_connectivity(sq, schema) / max(schema.schema.number_of_edges(), 1), 4),
                "Div_n": round(compute_diversity(sq), 4),
                "Classes": cls,
                "Propriétés": prop,
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"Score I(S)": st.column_config.ProgressColumn(
                         "Score I(S)", min_value=0, max_value=1, format="%.4f")})

        # ── Graphe scores ──
        st.markdown("#### Distribution des scores")
        fig_bar = go.Figure()
        colors  = ["#4f8ef7" if sq.signature() in selected_sigs else "#334155"
                   for sq, _ in ranked]
        fig_bar.add_trace(go.Bar(
            x=[f"S{i+1}" for i in range(len(ranked))],
            y=[s for _, s in ranked],
            marker_color=colors,
            text=[f"{s:.3f}" for _, s in ranked],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Score : %{y:.4f}<extra></extra>"))
        fig_bar.add_hline(y=0, line_color="#334155")
        fig_bar.update_layout(
            paper_bgcolor="#1e2235", plot_bgcolor="#1e2235",
            font=dict(color="#e2e8f0"), height=300,
            xaxis=dict(gridcolor="#2d3047"),
            yaxis=dict(gridcolor="#2d3047", title="Score I(S)"),
            showlegend=False,
            title=dict(text=f"Bleu = sélectionnés (top-{k})", font=dict(size=12, color="#94a3b8")),
            margin=dict(l=40, r=20, t=40, b=40))
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Graphes côte à côte ──
        st.markdown("#### Schéma complet  vs  Résumé")
        g1, g2 = st.columns(2)
        with g1:
            fig1 = plotly_graph(schema.schema,
                f"Schéma ({schema.schema.number_of_nodes()} nœuds · {schema.schema.number_of_edges()} arêtes)",
                "#4f8ef7")
            st.plotly_chart(fig1, use_container_width=True)
        with g2:
            fig2 = plotly_graph(summary,
                f"Résumé top-{k} ({summary.number_of_nodes()} nœuds · {summary.number_of_edges()} arêtes)",
                "#4ade80")
            st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════
# ONGLET 3 — EVALUATION
# ══════════════════════════════════════════════
with tab3:
    if not st.session_state.get("ran"):
        st.info("Lancez d'abord le pipeline (onglet **Pipeline**).")
    else:
        subgraphs = st.session_state["subgraphs"]
        summary   = st.session_state["summary"]
        m    = compute_coverage(summary, subgraphs)
        comp = compute_compactness(summary, schema)

        # ── Métriques ──
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Coverage nœuds",  f"{m['coverage_nodes']*100:.1f}%",
                  f"{m['n_covered_nodes']} / {m['n_query_nodes']}")
        c2.metric("Coverage arêtes", f"{m['coverage_edges']*100:.1f}%",
                  f"{m['n_covered_edges']} / {m['n_query_edges']}")
        c3.metric("Coverage globale", f"{m['coverage_global']*100:.1f}%")
        c4.metric("Compacité",        f"{comp*100:.1f}%")

        # ── Jauges Plotly ──
        fig_gauge = go.Figure()
        gauges = [
            ("Coverage nœuds",  m['coverage_nodes']*100,  "#4f8ef7"),
            ("Coverage arêtes", m['coverage_edges']*100,  "#a78bfa"),
            ("Coverage globale",m['coverage_global']*100, "#f59e0b"),
            ("Compacité",       comp*100,                 "#4ade80"),
        ]
        for i, (label, val, color) in enumerate(gauges):
            fig_gauge.add_trace(go.Indicator(
                mode="gauge+number",
                value=val,
                title=dict(text=label, font=dict(color="#94a3b8", size=12)),
                number=dict(suffix="%", font=dict(color="#e2e8f0", size=22)),
                gauge=dict(
                    axis=dict(range=[0,100], tickcolor="#4a5568",
                              tickfont=dict(color="#64748b")),
                    bar=dict(color=color, thickness=0.6),
                    bgcolor="#1a1d27",
                    bordercolor="#2d3047",
                    steps=[dict(range=[0,100], color="#2d3047")],
                    threshold=dict(line=dict(color="red",width=2),
                                   thickness=0.8, value=80)),
                domain=dict(row=0, column=i)))
        fig_gauge.update_layout(
            grid=dict(rows=1, columns=4),
            paper_bgcolor="#0f1117",
            height=220,
            margin=dict(l=20, r=20, t=50, b=10))
        st.plotly_chart(fig_gauge, use_container_width=True)

        # ── Éléments manquants ──
        col_miss1, col_miss2 = st.columns(2)
        with col_miss1:
            st.markdown("#### 🔴 Classes manquantes")
            missing_n = sorted(m["missing_nodes"])
            if missing_n:
                for n in missing_n:
                    lbl = n.split("#")[-1].split("/")[-1]
                    st.markdown(f"<span style='color:#f87171'>✗</span> `{lbl}`",
                                unsafe_allow_html=True)
            else:
                st.success("Toutes les classes sont couvertes ✅")
        with col_miss2:
            st.markdown("#### 🔴 Relations manquantes")
            missing_e = sorted(m["missing_edges"])
            if missing_e:
                for u, v, p in missing_e:
                    ul = u.split("#")[-1].split("/")[-1]
                    vl = v.split("#")[-1].split("/")[-1]
                    pl = p.split("#")[-1].split("/")[-1]
                    st.markdown(
                        f"<span style='color:#f87171'>✗</span> `{ul}` → `{pl}` → `{vl}`",
                        unsafe_allow_html=True)
            else:
                st.success("Toutes les relations sont couvertes ✅")

# ══════════════════════════════════════════════
# ONGLET 4 — ANALYSE
# ══════════════════════════════════════════════
with tab4:
    if not st.session_state.get("ran"):
        st.info("Lancez d'abord le pipeline (onglet **Pipeline**).")
    else:
        subgraphs = st.session_state["subgraphs"]
        ranked    = st.session_state["ranked"]
        k_cur     = st.session_state.get("k", k)

        # ── Coverage vs k ──
        st.markdown("#### Impact de k sur la Coverage et la Compacité")
        k_vals, covs_g, comps_l = [], [], []
        for ki in range(1, len(subgraphs) + 1):
            sel  = select_top_k(ranked, ki)
            summ = connect_subgraphs(sel, schema)
            m_   = compute_coverage(summ, subgraphs)
            c_   = compute_compactness(summ, schema)
            k_vals.append(ki)
            covs_g.append(round(m_["coverage_global"]*100, 1))
            comps_l.append(round(c_*100, 1))

        fig_k = go.Figure()
        fig_k.add_trace(go.Scatter(x=k_vals, y=covs_g, mode="lines+markers",
            name="Coverage globale (%)", line=dict(color="#f59e0b", width=2.5),
            marker=dict(size=8), hovertemplate="k=%{x}<br>Coverage=%{y}%<extra></extra>"))
        fig_k.add_trace(go.Scatter(x=k_vals, y=comps_l, mode="lines+markers",
            name="Compacité (%)", line=dict(color="#a78bfa", width=2.5),
            marker=dict(size=8), hovertemplate="k=%{x}<br>Compacité=%{y}%<extra></extra>"))
        fig_k.add_vline(x=k_cur, line_color="#f87171", line_dash="dash",
                        annotation_text=f" k={k_cur} actuel",
                        annotation_font_color="#f87171")
        fig_k.update_layout(
            paper_bgcolor="#1e2235", plot_bgcolor="#1e2235",
            font=dict(color="#e2e8f0"), height=360,
            xaxis=dict(gridcolor="#2d3047", title="k", tickmode="linear"),
            yaxis=dict(gridcolor="#2d3047", title="%", range=[0,110]),
            legend=dict(bgcolor="#1a1d27", bordercolor="#2d3047"),
            margin=dict(l=40,r=20,t=20,b=40))
        st.plotly_chart(fig_k, use_container_width=True)

        # Tableau k
        df_k = pd.DataFrame({"k": k_vals, "Coverage (%)": covs_g, "Compacité (%)": comps_l})
        st.dataframe(df_k, use_container_width=True, hide_index=True)

        st.divider()

        # ── Impact des poids ──
        st.markdown("#### Impact des poids α, β, γ (k fixé)")
        configs = [
            ("Fréquence (α=0.8)",     0.8, 0.1, 0.1),
            ("Équilibré (proposé)",   0.5, 0.3, 0.2),
            ("Connectivité (β=0.7)",  0.2, 0.7, 0.1),
            ("Diversité (γ=0.7)",     0.2, 0.1, 0.7),
            ("Structurel (β+γ=0.9)", 0.1, 0.5, 0.4),
        ]
        rows_w = []
        n_q = len(load_query_list(queries_path))
        for label, a, b, g in configs:
            r_    = compute_importance_scores(subgraphs, schema, n_q, a, b, g)
            sel_  = select_top_k(r_, k_cur)
            summ_ = connect_subgraphs(sel_, schema)
            m_    = compute_coverage(summ_, subgraphs)
            c_    = compute_compactness(summ_, schema)
            rows_w.append({"Configuration": label, "α": a, "β": b, "γ": g,
                           "Coverage (%)": round(m_["coverage_global"]*100, 1),
                           "Compacité (%)": round(c_*100, 1)})
        df_w = pd.DataFrame(rows_w)

        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(name="Coverage (%)", x=df_w["Configuration"],
            y=df_w["Coverage (%)"], marker_color="#4f8ef7",
            text=df_w["Coverage (%)"].apply(lambda v: f"{v}%"),
            textposition="outside"))
        fig_w.add_trace(go.Bar(name="Compacité (%)", x=df_w["Configuration"],
            y=df_w["Compacité (%)"], marker_color="#a78bfa",
            text=df_w["Compacité (%)"].apply(lambda v: f"{v}%"),
            textposition="outside"))
        fig_w.update_layout(
            barmode="group",
            paper_bgcolor="#1e2235", plot_bgcolor="#1e2235",
            font=dict(color="#e2e8f0"), height=360,
            xaxis=dict(gridcolor="#2d3047"),
            yaxis=dict(gridcolor="#2d3047", title="%", range=[0,115]),
            legend=dict(bgcolor="#1a1d27", bordercolor="#2d3047"),
            margin=dict(l=40,r=20,t=20,b=80))
        st.plotly_chart(fig_w, use_container_width=True)
        st.dataframe(df_w, use_container_width=True, hide_index=True)
