# Financial AI Assistant (RAG & Text-to-SQL)

> Trợ lý AI phân tích tài chính chuyên sâu cấp doanh nghiệp, kết hợp **Text-to-SQL trên PostgreSQL/SQLite** (dữ liệu định lượng XBRL chính thức) và **Parent-Document RAG trên ChromaDB** (thuyết minh định tính Form 10-K) cho 3 tập đoàn công nghệ lớn: **Apple (AAPL)**, **Microsoft (MSFT)** và **NVIDIA (NVDA)** từ SEC EDGAR.

---

## 1. Hệ Thống Làm Gì? (What Does It Do?)

Hệ thống giải quyết bài toán phân tích tài chính toàn diện mà một mô hình ngôn ngữ đơn lẻ không thể làm chính xác:

* **Tự động điều phối truy vấn (Intelligent Routing)**: Phân loại câu hỏi của người dùng vào đúng luồng chuyên biệt:
  * `SQL_ONLY`: Trả lời các câu hỏi thuần số liệu (Doanh thu, Lợi nhuận ròng, Biên gộp, EPS, Dòng tiền) với độ chính xác số học 100% bằng cách truy vấn cơ sở dữ liệu XBRL.
  * `RAG_ONLY`: Trả lời các câu hỏi về chiến lược kinh doanh (Item 1), yếu tố rủi ro chuỗi cung ứng/pháp lý (Item 1A), hoặc đánh giá thị trường (Item 7A) trích xuất từ văn bản báo cáo thường niên 10-K.
  * `HYBRID`: Tự động phân rã câu hỏi phức tạp (ví dụ: *"Doanh thu Data Center tăng bao nhiêu và ban lãnh đạo giải thích nguyên nhân do đâu?"*) thành 2 nhánh SQL và RAG chạy song song, sau đó hợp nhất bằng chứng (Evidence Fusion).
* **Kiểm chứng 3 tầng chống ảo giác (Multi-Tier Verifier Audit)**:
  * *Tầng 1 (Số học)*: Đối soát regex 100% các con số trong câu trả lời với kết quả SQL thật (dung sai < 2%).
  * *Tầng 2 (Trích dẫn)*: Kiểm tra tính hợp lệ của nguồn trích dẫn `[Form 10-K, TICKER, FY, Section]`.
  * *Tầng 3 (Ngữ nghĩa)*: Kiểm tra tính logic và factual consistency của toàn bộ câu trả lời.

---

## 2. Kiến Trúc Ra Sao? (System Architecture)

### 🏛️ Sơ Đồ Luồng Xử Lý (End-to-End Workflow)

```
USER Question
      │
      ▼
Query Analyzer (Entity, Fiscal Year, Metrics, Intent)
      │
      ▼
    Router
  ├── SQL_ONLY ──► Text-to-SQL ──► PostgreSQL/SQLite (Semantic Views) ──┐
  │                                                                     │
  ├── RAG_ONLY ──► Dense Retriever ──► ChromaDB (Child Vector) ─────────┼──► Evidence Fusion ──► Answer Generator ──► 3-Tier Verifier ──► Answer + Citation
  │                                         │                           │
  │                                         ▼ (Resolve Parent)          │
  │                                    SQLite Parent DocStore           │
  │                                                                     │
  └── HYBRID ────► Decomposer ──┬── SQL Sub-query ──► ... ──────────────┘
                                └── RAG Sub-query ──► ...
```

### 🔑 Các Điểm Nhấn Kiến Trúc Cốt Lõi:
1. **Tách biệt dữ liệu định lượng & định tính (Separation of Concerns)**:
   * Số liệu tài chính không bao giờ để LLM "đoán" từ văn bản; toàn bộ được nạp từ SEC Company Facts XBRL vào các Semantic Views: `v_annual_financial_summary`, `v_growth_and_margins`, `v_segment_revenue`.
2. **Kiến trúc Parent-Document (Small-to-Big) Chunking**:
   * **Child Chunks (150 – 200 tokens)**: Phục vụ vector search trên ChromaDB với mô hình `all-MiniLM-L6-v2`. Đảm bảo 100% nằm gọn dưới giới hạn 256 tokens, loại bỏ hoàn toàn hiện tượng silent truncation.
   * **Parent Chunks (800 – 1,500 tokens)**: Lưu trữ trong SQLite `ParentDocStore`. Khi vector search bắt trúng Child Chunk, hệ thống tự động gắp Parent Chunk hoàn chỉnh (giữ nguyên bảng thuyết minh và ngữ cảnh đoạn văn) để nạp vào prompt cho LLM.

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
# 1. Tải dữ liệu XBRL Company Facts & nạp Database + Views
python scripts/load_financial_db.py

# 2. Tải các file 10-K HTML 3 năm gần nhất cho AAPL, MSFT, NVDA
python scripts/download_filings.py

# 3. Làm sạch HTML, phân tích section, chunking phân cấp và lập chỉ mục ChromaDB
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

## 4. Đánh Giá Thế Nào? (Evaluation: Năng Lực Truy Xuất Thông Tin)

Năng lực truy xuất thông tin của bộ tìm kiếm RAG (ChromaDB Vector Search kết hợp SQLite Parent Resolution) được đo lường thực nghiệm định lượng thông qua bộ công cụ chuẩn [`scripts/benchmark_ir_ops.py`](file:///d:/financial-rag-ai-assistant/scripts/benchmark_ir_ops.py) trên tập kiểm thử báo cáo SEC 10-K:

### Bảng Chỉ Số Đo Lường Truy Xuất (Information Retrieval - IR Metrics)

| Chỉ số (IR Metric) | Điểm số đạt được | Diễn giải kỹ thuật |
| :--- | :---: | :--- |
| **Precision@1** | **`0.7000` (70.0%)** | 70% các truy vấn có ngay tài liệu chuẩn xác tuyệt đối ở vị trí Top 1. |
| **Precision@3** | **`0.5667` (56.7%)** | Tỷ lệ tài liệu liên quan trực tiếp trong 3 chunks đầu tiên trả về. |
| **Precision@5** | **`0.4800` (48.0%)** | Tỷ lệ tài liệu hữu ích trong Top 5 chunks (đảm bảo không bị loãng thông tin). |
| **Recall@1** | **`0.2250` (22.5%)** | Khả năng bao phủ thông tin ngay tại vị trí kết quả đầu tiên. |
| **Recall@3** | **`0.5500` (55.0%)** | Hơn một nửa toàn bộ thông tin tài chính cốt lõi được gom đủ trong Top 3. |
| **Recall@5** | **`0.8000` (80.0%)** | **Bắt trọn 80% toàn bộ ngữ cảnh tài chính cần tìm** chỉ trong Top 5 chunks. |
| **MRR (Mean Reciprocal Rank)** | **`0.7250`** | Chunk đúng nhất trung bình luôn nằm ở vị trí **Top 1 hoặc Top 2** ($1 / 0.725 \approx 1.38$). |
| **NDCG@3** | **`0.6061`** | Đánh giá chất lượng xếp hạng có trọng số chiết khấu vị trí cho Top 3. |
| **NDCG@5** | **`0.7339`** | Đánh giá chất lượng xếp hạng toàn diện cho Top 5 (tiệm cận mức chuẩn 0.75 của hệ thống IR quốc tế). |

> **Nhận xét kết quả IR**: 
> Nhờ áp dụng cơ chế **Small-to-Big Retrieval**, mô hình embedding `all-MiniLM-L6-v2` chỉ cần quét các Child Chunks ngắn sắc nét (144 tokens trung bình) giúp điểm tương đồng và độ nhạy xếp hạng (MRR = 0.725, NDCG@5 = 0.734) tăng vượt bậc, đồng thời Parent Chunks trả về bảo toàn trọn vẹn ngữ cảnh lập luận cho LLM.
