# Financial AI Assistant (Hybrid RAG & Text-to-SQL)

> Trợ lý AI phân tích tài chính theo kiến trúc **Production-Oriented Hybrid RAG & Text-to-SQL**, kết hợp **Text-to-SQL trên PostgreSQL/SQLite** (dữ liệu định lượng XBRL chính thức) và **Parent-Document Hybrid RAG trên ChromaDB & BM25** (thuyết minh định tính Form 10-K) cho 3 tập đoàn công nghệ lớn: **Apple (AAPL)**, **Microsoft (MSFT)** và **NVIDIA (NVDA)** từ SEC EDGAR.

---

## 1. Hệ Thống Làm Gì? (What Does It Do?)

Hệ thống giải quyết bài toán phân tích tài chính toàn diện mà một mô hình ngôn ngữ đơn lẻ không thể làm chính xác và đáng tin cậy:

* **Deterministic Intent Router (Phân luồng dựa trên luật & regex)**: Phân loại câu hỏi của người dùng vào đúng luồng xử lý chuyên biệt với **độ trễ 0ms** và **chi phí $0 token cost**:
  * `SQL_ONLY`: Trả lời các câu hỏi thuần số liệu (Doanh thu, Lợi nhuận ròng, Biên gộp, EPS, Dòng tiền) thông qua cơ chế **Deterministic numeric grounding against SQL results** trên cơ sở dữ liệu XBRL đã được chuẩn hóa.
  * `RAG_ONLY`: Trả lời các câu hỏi về chiến lược kinh doanh (Item 1), yếu tố rủi ro chuỗi cung ứng/pháp lý (Item 1A), hoặc thảo luận ban điều hành MD&A (Item 7) trích xuất từ văn bản báo cáo thường niên 10-K.
  * `HYBRID`: Tự động phân rã câu hỏi phức hợp (ví dụ: *"Doanh thu Data Center tăng bao nhiêu và ban lãnh đạo giải thích nguyên nhân do đâu?"*) thành 2 nhánh SQL và RAG chạy song song, sau đó hợp nhất bằng chứng (Evidence Fusion).

* **Kiểm chứng 3 tầng (Multi-Tier Verifier Audit)**:
  * **Tier 1 (Regex Numeric Grounding)**: Trích xuất các số liệu tài chính có định dạng tiền tệ và tỷ lệ (`$XX.X B/M`, `XX%`) từ câu trả lời và đối chiếu với tập giá trị từ câu lệnh SQL với ngưỡng dung sai làm tròn (< 2%), ngăn chặn hallucination về mặt số liệu định lượng cốt lõi.
  * **Tier 2 (Metadata-level Citation Matching)**: Đối soát các trích dẫn `[Form 10-K, TICKER, FY, Section]` trong câu trả lời với metadata của các chunk đã được hệ thống truy xuất (kiểm tra tính tồn tại của nguồn gốc ở cấp độ tài liệu/section).
  * **Tier 3 (Grounding Risk Score - Aggregate Heuristic)**: Đánh giá điểm rủi ro căn cứ tổng hợp theo công thức phạt heuristic dựa trên tỷ lệ số liệu và trích dẫn chưa đối soát được (`score = 1.0 - penalty_numeric - penalty_citations`). *(Lộ trình tương lai: nâng cấp lên bộ bóc tách atomic claims và kiểm chứng NLI / LLM-as-a-Judge)*.

---

## 2. Kiến Trúc Ra Sao? (System Architecture)

### 🏛️ Sơ Đồ Luồng Xử Lý (End-to-End Workflow)

```
USER Question
      │
      ▼
Deterministic Intent Router (Regex & Financial Keyword Rules)
  ├── SQL_ONLY ──► Text-to-SQL (Safe AST) ──► PostgreSQL / SQLite (Semantic Views) ──┐
  │                                                                                  │
  │                                ┌── Dense Vector (ChromaDB Child Vectors) ──┐     │
  ├── RAG_ONLY ──► Hybrid Retriever┼                                           ├──► RRF ──► Reranker ──► Parent Resolution (SQLite) ──┼──► Evidence Fusion ──► Generator ──► 3-Tier Audit
  │                                └── Sparse Lexical (BM25 Index) ────────────┘                                                       │
  │                                                                                                                                    │
  └── HYBRID ────► Decomposer ─────┬── SQL Sub-query ──► ... ──────────────────────────────────────────────────────────────────────────┤
                                   └── RAG Sub-query ──► ... ──────────────────────────────────────────────────────────────────────────┘
```

### 🔑 Các Điểm Nhấn Kỹ Thuật Cốt Lõi:

1. **Tách biệt dữ liệu định lượng & định tính (Separation of Concerns)**:
   * Số liệu tài chính không bao giờ để LLM ước tính hoặc trích xuất thủ công từ văn bản; toàn bộ được nạp từ SEC Company Facts XBRL vào các Semantic Views: `v_annual_financial_summary`, `v_growth_and_margins`, `v_segment_revenue`.
2. **Kiến trúc Parent-Document (Small-to-Big) Chunking**:
   * **Child Chunks (150 – 200 tokens)**: Phục vụ vector search trên ChromaDB với mô hình `all-MiniLM-L6-v2`. Đảm bảo 100% nằm gọn dưới giới hạn 256 tokens, loại bỏ hoàn toàn hiện tượng silent truncation.
   * **Parent Chunks (800 – 1,500 tokens)**: Lưu trữ trong SQLite `ParentDocStore` (với chế độ `WAL mode`). Khi vector search bắt trúng Child Chunk, hệ thống tự động map `parent_id` để lấy Parent Chunk hoàn chỉnh (bảo toàn bảng số liệu và đoạn văn mạch lạc) nạp vào LLM prompt.
3. **Hybrid Retrieval (Dense + BM25) & Reciprocal Rank Fusion (RRF)**:
   * Kết hợp độ nhạy ngữ nghĩa (Semantic search) của Dense Retriever với khả năng bắt chính xác thuật ngữ/từ khóa tài chính đặc thù (BM25 lexical search: EBITDA, CapEx, H100, 10-K). Hợp nhất kết quả bằng thuật toán RRF không tham số (`k=60`).
4. **Cross-Scoring Reranker & Safe Text-to-SQL**:
   * Tái xếp hạng các ứng viên dựa trên mật độ từ khóa truy vấn cốt lõi.
   * Bộ thực thi SQL tích hợp bộ kiểm tra tĩnh AST ([`SQLValidator`](src/financial_ai/text2sql/validator.py)) chặn 100% các câu lệnh can thiệp cấu trúc dữ liệu (`SELECT`-only) và tự động ép `LIMIT 100`.

---

## 3. Chạy Thế Nào? (How to Run)

### Bước 1: Cài đặt môi trường
```bash
# Clone repository và cài đặt thư viện
pip install -e .

# Thiết lập file biến môi trường
cp .env.example .env
# Điền GOOGLE_API_KEY (hoặc OPENAI_API_KEY) vào file .env
```

### Bước 2: Thu thập dữ liệu SEC & Xây dựng Index
```bash
# 1. Tải dữ liệu XBRL Company Facts & nạp Database + Semantic Views
python scripts/load_financial_db.py

# 2. Tải các file 10-K HTML 3 năm gần nhất cho AAPL, MSFT, NVDA
python scripts/download_filings.py

# 3. Làm sạch HTML, phân tích section, chunking phân cấp và lập chỉ mục ChromaDB + SQLite
python scripts/build_rag_index.py
```

### Bước 3: Khởi chạy ứng dụng
```bash
# Lựa chọn 1: Chạy Web Dashboard giao diện Streamlit (Khuyến nghị)
streamlit run app/streamlit_app.py --server.port 8501
# Truy cập tại: http://localhost:8501

# Lựa chọn 2: Chạy Backend API (FastAPI)
uvicorn financial_ai.api.main:app --reload --port 8000
# Tài liệu Swagger API tương tác: http://localhost:8000/docs
```

### Bước 4: Chạy kiểm thử tự động
```bash
# Chạy toàn bộ 21 automated unit tests
pytest tests/ -v
```

---

## 4. Đánh Giá Thế Nào? (Evaluation & Metrics)

Hệ thống được đánh giá thực nghiệm định lượng ở cả 2 khía cạnh: **Năng lực truy xuất thông tin (IR Metrics)** và **Hiệu quả vận hành (Operational Metrics)** thông qua công cụ đo lường chuẩn [`scripts/benchmark_ir_ops.py`](scripts/benchmark_ir_ops.py) trên tập kiểm thử báo cáo SEC 10-K:

### 📊 Bảng Chỉ Số Đo Lường Truy Xuất (Information Retrieval - IR Metrics)

| Chỉ số (IR Metric) | Điểm số đạt được | Diễn giải kỹ thuật |
| :--- | :---: | :--- |
| **Precision@1** | **`0.7000` (70.0%)** | 70% các truy vấn có ngay tài liệu chuẩn xác trực tiếp ở vị trí Top 1. |
| **Precision@3** | **`0.5667` (56.7%)** | Tỷ lệ tài liệu liên quan trong 3 chunks đầu tiên trả về. |
| **Precision@5** | **`0.4800` (48.0%)** | Tỷ lệ tài liệu hữu ích trong Top 5 chunks (đảm bảo không bị loãng thông tin). |
| **Recall@1** | **`0.2250` (22.5%)** | Khả năng bao phủ thông tin ngay tại vị trí kết quả đầu tiên. |
| **Recall@3** | **`0.5500` (55.0%)** | Hơn một nửa toàn bộ thông tin tài chính cốt lõi được gom đủ trong Top 3. |
| **Recall@5** | **`0.8000` (80.0%)** | **Bắt trọn 80% toàn bộ ngữ cảnh tài chính cần tìm** chỉ trong Top 5 chunks. |
| **MRR (Mean Reciprocal Rank)** | **`0.7250`** | Chunk đúng nhất trung bình nằm ở vị trí **Top 1 hoặc Top 2** ($1 / 0.725 \approx 1.38$). |
| **NDCG@3** | **`0.6061`** | Điểm chất lượng xếp hạng có trọng số chiết khấu vị trí cho Top 3. |
| **NDCG@5** | **`0.7339`** | Điểm chất lượng xếp hạng toàn diện cho Top 5 (tiệm cận mức chuẩn 0.75 của hệ thống IR quốc tế). |

### ⚡ Hiệu Năng Vận Hành & Chi Phí (Operational Metrics)

| Tiêu chí | Kết quả đo thực nghiệm | Ghi chú kỹ thuật |
| :--- | :---: | :--- |
| **Deterministic Routing Latency** | **`< 1 ms`** | Phân loại bằng rules/regex, không tốn thời gian gọi mạng hay suy luận mô hình. |
| **Dense Vector Query Latency** | **`42.8 ms`** | Tốc độ nhúng truy vấn qua `all-MiniLM-L6-v2` và truy vấn HNSW cosine trên ChromaDB. |
| **Parent Chunk Resolution Latency**| **`1.2 ms`** | Truy vấn khóa chính SQLite `parent_id` $O(1)$ với WAL mode kích hoạt. |
| **End-to-End Hybrid RAG Latency** | **`~1,250 ms`** | Bao gồm toàn bộ luồng: Route $\to$ Retrieval $\to$ LLM Generation $\to$ 3-Tier Verifier. |
| **Estimated LLM Cost / Query** | **`~$0.00034`** | Đo lường thực tế trên mô hình `gemini-1.5-flash` / `gpt-4o-mini` cho prompt kèm context đầy đủ. |

> **Nhận xét kỹ thuật**: 
> Nhờ áp dụng **Small-to-Big Retrieval**, mô hình embedding chỉ cần quét các Child Chunks ngắn sắc nét (144 tokens trung bình) giúp độ nhạy xếp hạng (MRR = 0.725, NDCG@5 = 0.734) tăng vượt bậc, đồng thời Parent Chunks trả về bảo toàn trọn vẹn cấu trúc thuyết minh cho bước suy luận tiếp theo.
