"""Streamlit Web Dashboard for Financial AI Assistant with Chat, Trace Expander, and Analytics Visualizer."""
import os
import sys
import json
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure src/ is in sys.path
sys.path.insert(0, os.path.abspath("src"))

from financial_ai.router.router import QueryRouter
from financial_ai.router.schemas import RouteType, RouteDecision
from financial_ai.hybrid.executor import HybridExecutor
from financial_ai.generation.answer_generator import FinancialAnswerGenerator
from financial_ai.rag.indexer import ChromaIndexer
from financial_ai.db.repositories import execute_safe_select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AI Financial Analyst | SEC RAG & Text-to-SQL",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5 0%, #7B1FA2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #757575;
        margin-bottom: 1.5rem;
    }
    .badge-sql {
        background-color: #E3F2FD;
        color: #0D47A1;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-rag {
        background-color: #E8F5E9;
        color: #1B5E20;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-hybrid {
        background-color: #F3E5F5;
        color: #4A148C;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-verified {
        background-color: #E0F2F1;
        color: #004D40;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-left: 8px;
    }
    .card {
        padding: 1.2rem;
        border-radius: 8px;
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_assistant_components():
    """Cache pipeline components for low-latency queries."""
    router = QueryRouter()
    executor = HybridExecutor()
    generator = FinancialAnswerGenerator()
    indexer = ChromaIndexer()
    return router, executor, generator, indexer


router, executor, generator, indexer = load_assistant_components()

# --- Sidebar ---
st.sidebar.markdown("### 🏢 SEC 10-K Coverage")
st.sidebar.info("""
**3 Tập Đoàn Công Nghệ Mỹ:**
- **AAPL** (Apple Inc. - CIK `0000320193`)
- **MSFT** (Microsoft Corp. - CIK `0000789019`)
- **NVDA** (NVIDIA Corp. - CIK `0001045810`)
""")

st.sidebar.markdown("### ⚙️ Chế Độ Điều Phối (Routing)")
routing_option = st.sidebar.selectbox(
    "Chọn chế độ thực thi:",
    options=["Tự động (Auto Router)", "SQL_ONLY (Chỉ Text-to-SQL)", "RAG_ONLY (Chỉ RAG)", "HYBRID (Hợp nhất Đa luồng)"],
    index=0,
)

st.sidebar.markdown("### 📊 Trạng Thái Hệ Thống")
try:
    execute_safe_select("SELECT 1;")
    st.sidebar.success("✅ Database: Connected (Views Active)")
except Exception:
    st.sidebar.error("❌ Database: Disconnected")

st.sidebar.success(f"✅ ChromaDB: {indexer.count()} Chunks Indexed")

# LLM Status
llm_provider = os.getenv("LLM_PROVIDER", "gemini").upper()
llm_model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
if getattr(generator, "llm", None):
    st.sidebar.success(f"🤖 LLM: {llm_provider} ({llm_model}) - Active")
else:
    st.sidebar.error("❌ LLM: Chưa cấu hình (Bắt buộc)")

# --- Main App Tabs ---
tab_chat, tab_analytics, tab_architecture = st.tabs([
    "💬 Trợ Lý Phân Tích (Chat & Audit)",
    "📈 Bảng So Sánh Chỉ Số Tài Chính",
    "🏛️ Kiến Trúc Hệ Thống & Schema",
])

# ==========================================
# TAB 1: Chat Interface & Verification Audit
# ==========================================
with tab_chat:
    st.markdown('<div class="main-header">Trợ Lý Phân Tích Tài Chính AI End-to-End</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ứng dụng RAG và Text-to-SQL trên dữ liệu SEC EDGAR 3 năm gần nhất (AAPL, MSFT, NVDA)</div>', unsafe_allow_html=True)

    # Sample Quick Buttons
    st.markdown("**Gợi ý câu hỏi mẫu:**")
    col1, col2, col3 = st.columns(3)
    sample_q = None

    if col1.button("📊 Doanh thu & Biên gộp NVIDIA 3 năm qua"):
        sample_q = "Doanh thu và Biên lợi nhuận gộp Gross Margin của NVIDIA qua 3 năm gần nhất là bao nhiêu?"
    if col2.button("🔬 So sánh chi phí R&D Apple và Microsoft"):
        sample_q = "So sánh chi phí R&D của Apple và Microsoft qua 3 năm gần nhất"
    if col3.button("⚡ Tăng trưởng Data Center NVDA & Nguyên nhân MD&A"):
        sample_q = "Doanh thu mảng Data Center của NVIDIA tăng trưởng bao nhiêu trong năm tài chính gần nhất và ban lãnh đạo giải thích nguyên nhân do đâu trong MD&A?"

    user_query = st.chat_input("Nhập câu hỏi phân tích tài chính về AAPL, MSFT, NVDA...")
    active_query = sample_q or user_query

    if active_query:
        with st.spinner("Đang phân tích câu hỏi, điều phối và đối soát dữ liệu SEC..."):
            # Map routing override
            override_route = None
            if "SQL_ONLY" in routing_option:
                override_route = RouteType.SQL_ONLY
            elif "RAG_ONLY" in routing_option:
                override_route = RouteType.RAG_ONLY
            elif "HYBRID" in routing_option:
                override_route = RouteType.HYBRID

            if override_route:
                analysis = router.analyzer.analyze(active_query)
                decision = RouteDecision(
                    route=override_route,
                    analysis=analysis,
                    rationale=f"Chế độ được ép thủ công: {override_route.value}",
                )
            else:
                decision = router.route(active_query)

            try:
                evidence = executor.execute(decision)
                result = generator.generate(evidence)
            except Exception as exc:
                st.error(f"❌ **Lỗi thực thi LLM:** {exc}")
                st.info("Vui lòng kiểm tra lại API Key hoặc hạn mức quota của LLM trong file `.env`.")
                logger.error("Pipeline execution error: %s", exc, exc_info=True)
                st.stop()

            answer = result["answer"]
            verification = result["verification"]
            ver_badge = verification["verification_badge"]
            overall_status = verification["overall_status"]

            # Display Route Badges
            route_val = decision.route.value
            if route_val == "SQL_ONLY":
                badge_html = f'<span class="badge-sql">⚡ Route: {route_val}</span>'
            elif route_val == "RAG_ONLY":
                badge_html = f'<span class="badge-rag">📄 Route: {route_val}</span>'
            else:
                badge_html = f'<span class="badge-hybrid">🔀 Route: {route_val}</span>'

            badge_html += f'<span class="badge-verified">🛡️ {ver_badge}</span>'
            st.markdown(badge_html, unsafe_allow_html=True)

            # Display Main Financial Report
            st.markdown(answer)

            # Verification & Execution Trace Expander
            with st.expander("🔍 Chi Tiết Thực Thi & Đối Soát Verifier (Execution Trace)", expanded=False):
                trace_tab1, trace_tab2, trace_tab3 = st.tabs([
                    "💾 Text-to-SQL Execution",
                    "📚 SEC 10-K Chunks Retrieved",
                    "🛡️ Multi-tier Verifier Audit",
                ])

                with trace_tab1:
                    if evidence.sql_query:
                        st.markdown("**Câu lệnh SQL đã sinh & thực thi:**")
                        st.code(evidence.sql_query, language="sql")
                        if evidence.sql_rows:
                            st.markdown("**Bảng dữ liệu trả về từ PostgreSQL Semantic Views:**")
                            st.dataframe(pd.DataFrame(evidence.sql_rows), use_container_width=True)
                    else:
                        st.info("Nhánh này không cần gọi cơ sở dữ liệu SQL.")

                with trace_tab2:
                    if evidence.retrieved_chunks:
                        st.markdown(f"**Đã tìm thấy {len(evidence.retrieved_chunks)} chunks văn bản liên quan từ ChromaDB:**")
                        for i, ch in enumerate(evidence.retrieved_chunks, 1):
                            cit = ch.get("citation", "SEC 10-K")
                            sim = ch.get("similarity_score", "N/A")
                            st.markdown(f"**[{i}] {cit}** (Độ tương đồng: `{sim}`)")
                            st.text_area(f"Chunk text #{i}", ch.get("text", ""), height=120, key=f"chunk_{i}")
                    else:
                        st.info("Nhánh này không cần truy xuất văn bản 10-K qua RAG.")

                with trace_tab3:
                    st.markdown("### Kết Quả Kiểm Chứng 3 Tầng Chống Ảo Giác")
                    t1 = verification["tier1_numeric"]
                    t2 = verification["tier2_citation"]
                    t3 = verification["tier3_semantic"]

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Tầng 1: Số Liệu Khớp SQL", f"{len(t1['matched_numbers'])}/{t1['total_found']}", delta="Passed" if t1['passed'] else "Warning")
                    c2.metric("Tầng 2: Trích Dẫn Hợp Lệ", f"{len(t2['valid_citations'])}/{t2['total_citations']}", delta="Passed" if t2['passed'] else "Warning")
                    c3.metric("Tầng 3: Điểm Logic Ngữ Nghĩa", f"{int(t3['score'] * 100)}%", delta="Grounded" if t3['grounded'] else "Review")

                    if t1["unverified_numbers"]:
                        st.warning(f"Các con số chưa khớp ground-truth: {t1['unverified_numbers']}")
                    if t2["unmatched_citations"]:
                        st.warning(f"Các trích dẫn không khớp nguồn: {t2['unmatched_citations']}")


# ==========================================
# TAB 2: Financial Analytics Visualizer
# ==========================================
with tab_analytics:
    st.markdown("### 📊 So Sánh Hiệu Quả Tài Chính 3 Năm Gần Nhất (AAPL, MSFT, NVDA)")
    st.markdown("Dữ liệu được truy vấn trực tiếp từ các **Semantic Views** của PostgreSQL:")

    try:
        summary_data = execute_safe_select("SELECT ticker, fiscal_year, total_revenue, gross_profit, net_income, diluted_eps FROM v_annual_financial_summary ORDER BY fiscal_year, ticker;")
        margins_data = execute_safe_select("SELECT ticker, fiscal_year, revenue_growth_yoy_pct, gross_margin_pct, net_margin_pct FROM v_growth_and_margins ORDER BY fiscal_year, ticker;")

        df_summary = pd.DataFrame(summary_data)
        df_margins = pd.DataFrame(margins_data)

        if not df_summary.empty:
            df_summary["revenue_billions"] = df_summary["total_revenue"] / 1e9
            df_summary["net_income_billions"] = df_summary["net_income"] / 1e9
            df_summary["period"] = df_summary["ticker"] + " FY" + df_summary["fiscal_year"].astype(str)

            col_a, col_b = st.columns(2)

            with col_a:
                fig_rev = px.bar(
                    df_summary,
                    x="fiscal_year",
                    y="revenue_billions",
                    color="ticker",
                    barmode="group",
                    title="Tổng Doanh Thu Hàng Năm (Tỷ USD)",
                    labels={"revenue_billions": "Doanh thu (Tỷ USD)", "fiscal_year": "Năm tài chính"},
                    text_auto=".1f",
                )
                st.plotly_chart(fig_rev, use_container_width=True)

            with col_b:
                fig_net = px.bar(
                    df_summary,
                    x="fiscal_year",
                    y="net_income_billions",
                    color="ticker",
                    barmode="group",
                    title="Lợi Nhuận Ròng Net Income (Tỷ USD)",
                    labels={"net_income_billions": "Net Income (Tỷ USD)", "fiscal_year": "Năm tài chính"},
                    text_auto=".1f",
                )
                st.plotly_chart(fig_net, use_container_width=True)

            col_c, col_d = st.columns(2)
            with col_c:
                if not df_margins.empty and "gross_margin_pct" in df_margins.columns:
                    fig_margin = px.line(
                        df_margins,
                        x="fiscal_year",
                        y="gross_margin_pct",
                        color="ticker",
                        markers=True,
                        title="Biên Lợi Nhuận Gộp Gross Margin (%)",
                        labels={"gross_margin_pct": "Gross Margin (%)", "fiscal_year": "Năm tài chính"},
                    )
                    st.plotly_chart(fig_margin, use_container_width=True)

            with col_d:
                # Segment revenue for NVIDIA Data Center
                seg_data = execute_safe_select("SELECT fiscal_year, dimension_name, revenue FROM v_segment_revenue WHERE ticker='NVDA' ORDER BY fiscal_year;")
                if seg_data:
                    df_seg = pd.DataFrame(seg_data)
                    df_seg["revenue_billions"] = df_seg["revenue"] / 1e9
                    fig_seg = px.bar(
                        df_seg,
                        x="fiscal_year",
                        y="revenue_billions",
                        color="dimension_name",
                        title="NVIDIA Doanh Thu Phân Khúc (Data Center vs Gaming)",
                        labels={"revenue_billions": "Doanh thu (Tỷ USD)", "fiscal_year": "Năm tài chính"},
                        text_auto=".1f",
                    )
                    st.plotly_chart(fig_seg, use_container_width=True)

            st.markdown("#### Bảng Dữ Liệu Chi Tiết")
            st.dataframe(df_summary, use_container_width=True)
    except Exception as exc:
        st.error(f"Lỗi khi tải dữ liệu trực quan hóa: {exc}")


# ==========================================
# TAB 3: Architecture & Schema
# ==========================================
with tab_architecture:
    st.markdown("### 🏛️ Kiến Trúc Hệ Thống (Workflow Architecture)")
    st.code("""
    USER Question
          │
          ▼
    Query Analyzer
          │
          ▼
        Router
      ├── SQL_ONLY ──► Text-to-SQL ──► PostgreSQL (Semantic Views) ──┐
      │                                                               │
      ├── RAG_ONLY ──► Dense Retriever ──► ChromaDB (SEC Chunks) ─────┼──► Evidence Fusion ──► Answer Generator ──► 3-Tier Verifier ──► Answer + Citation
      │                                                               │
      └── HYBRID ────► Decomposer ──┬── SQL Sub-query ──► ... ────────┘
                                    └── RAG Sub-query ──► ...
    """, language="text")

    st.markdown("### 📋 Các Semantic Views Được Tối Ưu Sẵn Cho Text-to-SQL")
    st.markdown("""
    - `v_annual_financial_summary`: Bảng tổng hợp các chỉ số tài chính cốt lõi (Revenue, Gross Profit, Operating Income, Net Income, EPS, Cash Flow).
    - `v_growth_and_margins`: Tự động tính sẵn tăng trưởng doanh thu YoY (%), Biên lợi nhuận gộp, Biên hoạt động, Biên ròng.
    - `v_segment_revenue`: Báo cáo doanh thu theo mảng kinh doanh (Data Center, iPhone, Intelligent Cloud...).
    """)
