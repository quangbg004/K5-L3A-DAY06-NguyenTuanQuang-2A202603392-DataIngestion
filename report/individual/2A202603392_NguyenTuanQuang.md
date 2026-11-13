# Báo cáo cá nhân Day 06 · AI Agent Protocols

Nguyễn Tuấn Quang · 2A202603392 · L3A

## Dữ liệu và pipeline

- Yang và cộng sự, *A Survey of AI Agent Protocols*, arXiv:2504.16736v3, CC BY 4.0. Corpus gồm 28 trang vật lý (3–30, cắt phần tài liệu tham khảo trên trang 30) và hai đơn vị MDX độc lập là MCP Architecture (4.074 ký tự) và MCP Lifecycle (5.952 ký tự) sau chuẩn hóa. Tổng cộng 30 đơn vị. `data/manifest.json` ghi URL tải đúng bản PDF và liên kết thông báo giấy phép MCP tại commit của hai tệp MDX.
- Dùng pypdf ở chế độ layout, chuẩn hóa Unicode và khoảng trắng. Cảnh báo chữ xoay chỉ xuất hiện ở trang vật lý 1 và 33, đều nằm ngoài corpus. Trong các trang đã dùng, trang 10 có chữ dính ở đoạn về phân mảnh MCP và trang 19 có văn bản bảng chen vào đoạn về hiệu suất. Benchmark đánh giá văn bản trích xuất. Xem `results/processing_notes.md`.
- Metadata truy vết gồm mã tài liệu, URL, trang vật lý hoặc ID đơn vị MDX và vị trí ký tự. `document_type` phân biệt bài khảo sát với đặc tả chính thức.
- Embedding BAAI/bge-small-en-v1.5 chạy CPU qua FastEmbed, 384 chiều, PostgreSQL 16.16 và pgvector 0.8.7 tìm kiếm cosine chính xác. Lệnh chạy nằm trong `starter/README.md`.

## Cấu hình và benchmark

- A chia 500 ký tự, overlap 50. B giới hạn 500 ký tự và ưu tiên ranh giới đoạn rồi câu. C dùng chỉ mục của B và thêm bộ lọc `document_type` khi câu hỏi yêu cầu nguồn là đặc tả.
- 20 câu với bằng chứng xác minh trên dữ liệu đã chuẩn hóa, gồm 15 dev, 5 test và 3 câu có filter. Q14–Q15 thuộc dev, Q20 thuộc test. Dev và test chia theo trang đối với bài khảo sát. Hai tập cùng dùng tài liệu Lifecycle, tạo nguy cơ trùng chủ đề.
- Chọn cấu hình theo Hit@3 dev, tiếp đến Hit@1 dev, rồi thứ tự A/B/C khi hòa. Bộ câu hỏi được chốt trước khi truy xuất.

## Kết quả đã đo

| Cấu hình | Số chunk | Tổng ký tự | Độ dài trung vị | Coherence /2 |
|---|---:|---:|---:|---:|
| A | 254 | 121314 | 500 | 1.0 |
| B | 297 | 109726 | 377 | 1.9 |
| C | 297, dùng chung với B | 109726 | 377 | 1.9, dùng nhãn B |

Coherence được chấm có AI hỗ trợ trên cùng 10 vị trí giữa trang 3–12. Mức 0 là đoạn khó hiểu, mức 1 là hiểu một phần, mức 2 là tự hiểu được và giữ trọn ý. C dùng lại nhãn B vì bộ lọc chỉ tác động lúc truy xuất và nội dung chunk giống hệt nhau. Mẫu và lý do nằm trong [coherence_samples.json](../../results/coherence_samples.json) và [coherence_audit.csv](../../results/coherence_audit.csv).

## Phân tích sơ bộ

A xử lý ít chunk hơn nhưng đưa nhiều ký tự hơn vào embedding do overlap. B giữ nhiều ý trọn vẹn hơn trong mẫu đã đọc, dù một số đoạn vẫn phụ thuộc đoạn trước, chẳng hạn trang 8 mở đầu bằng “this approach”. Mẫu 10 vị trí không đủ để suy rộng ra ngoài corpus.

## Benchmark truy xuất

| Cấu hình | Hit@1 dev | Evidence Hit@3 dev | Hit@1 test | Evidence Hit@3 test | Embedding và lưu |
|---|---:|---:|---:|---:|---:|
| A | 6/15 | 9/15 | 2/5 | 4/5 | 14.54 s |
| B | 11/15 | 11/15 | 2/5 | 3/5 | 16.09 s |
| C | 11/15 | 12/15 | 2/5 | 3/5 | Dùng lại B |

Chi phí API bằng 0. Chạy embedding cục bộ bằng FastEmbed 0.9.1, model ONNX tại commit aa8f8b060edb00e03bfdd08813a2949946c8ba55 của Qdrant/bge-small-en-v1.5-onnx-Q. Nạp lại A và B giữ nguyên lần lượt 254 và 297 bản ghi. Mỗi cấu hình có 20 trace, mỗi trace có 3 kết quả.

| Cấu hình | Metadata đủ và đúng | Top-3 tuân thủ filter trên test | Grounding 0/1/2 | Grounding TB /2 |
|---|---:|---:|---:|---:|
| A | 15/15 | 0/1 | 1 / 0 / 4 | 1.6 |
| B | 15/15 | 0/1 | 0 / 2 / 3 | 1.6 |
| C | 15/15 | 1/1 | 0 / 2 / 3 | 1.6 |

Metadata được đối chiếu bằng mã với tài liệu, URL, số trang hoặc ID đơn vị, loại tài liệu và vị trí trong văn bản chuẩn hóa. Grounding được chấm có AI hỗ trợ dựa trên top-3 của mỗi câu test. Mức 0 là thiếu bằng chứng, mức 1 là có bằng chứng một phần, mức 2 là đủ bằng chứng để trả lời và truy nguồn.

### Tuân thủ bộ lọc theo câu

Mỗi ô Q14, Q15 và Q20 ghi số chunk đúng `document_type=specification` trong top-3. Một câu đạt khi cả ba chunk đúng loại. A và B chạy không lọc. C dùng bộ lọc được cung cấp cùng câu hỏi.

| Cấu hình | Q14 dev | Q15 dev | Q20 test | Câu đạt dev | Câu đạt test | Tổng câu đạt |
|---|---:|---:|---:|---:|---:|---:|
| A | 2/3 | 1/3 | 2/3 | 0/2 | 0/1 | 0/3 |
| B | 2/3 | 2/3 | 1/3 | 0/2 | 0/1 | 0/3 |
| C | 3/3 | 3/3 | 3/3 | 2/2 | 1/1 | 3/3 |

C giữ đúng loại tài liệu ở cả ba câu. Q14 cho thấy các chunk đúng loại vẫn có thể thiếu bằng chứng cần thiết. Trên test, bộ lọc cải thiện tuân thủ ở Q20, còn số hit của B và C đều là 3/5.

### Xác nhận audit thủ công

Tôi đã rà thủ công cả ba bảng ngày 13/11/2026 và xác nhận các điểm, lý do chấm và thông tin nguồn đều phù hợp. Kết quả rà giữ nguyên toàn bộ nhãn và số liệu. Các bảng ban đầu được lập bằng đối chiếu tự động hoặc chấm có AI hỗ trợ.

| File | Phạm vi đã rà | Nội dung xác nhận |
|---|---|---|
| [coherence_audit.csv](../../results/coherence_audit.csv) | Dòng 2–21, A và B, trang 3–12 | Mức điểm và lý do của từng chunk mẫu. |
| [metadata_audit.csv](../../results/metadata_audit.csv) | Dòng 2–46, Q16–Q20, cả ba cấu hình, hạng 1–3 | Mã tài liệu, trang, URL và loại tài liệu so với manifest và nguồn, gồm việc tuân thủ bộ lọc của từng hạng ở Q20. |
| [grounding_audit.csv](../../results/grounding_audit.csv) | Dòng 2–16, Q16–Q20 ở A, B và C | Mức độ đủ bằng chứng trong top-3 và lý do chấm từng câu test. |

## Kết luận

- **A–B.** B cải thiện coherence và dev Hit@3. Trên test Q18, A đưa đoạn nêu đúng Flight Agent và Weather Agent ở trang 27 vào hạng 2. B và C truy xuất các đoạn cùng chủ đề, nhưng top-3 thiếu cặp agent.
- **Q05 và Q10 — ranh giới chunk.** Với A (500 ký tự, overlap 50), không chunk nào trên trang 10 chứa trọn đoạn gold về các loại tài nguyên MCP ở Q05. Tương tự, không chunk nào trên trang 15 chứa trọn đoạn gold nêu ba mục tiêu của Agent Communication Trilemma ở Q10. B có ít nhất một chunk chứa trọn bằng chứng ở mỗi trang. Điều này cho thấy overlap 50 vẫn có thể để đoạn trích chuẩn nằm qua hai chunk.
- **B–C, Q15 — yêu cầu bắt buộc trong MCP Lifecycle.** A tìm được câu nêu Initialization phải là tương tác đầu tiên ở hạng 1. Top-1 của B và C đều có danh sách đúng thứ tự. C tìm thêm câu có `MUST` ở hạng 3 nên được tính Evidence Hit@3 theo gold đã chốt cho câu hỏi về yêu cầu bắt buộc. Nếu tính danh sách có thứ tự là bằng chứng tương đương cho riêng Q15, B và C đều đạt Hit@1 và Evidence Hit@3 là 12/15 trên dev, và quy tắc hòa sẽ chọn B. Kết quả chính áp dụng gold gốc. Q14 vẫn trượt ở B và C dù C lọc đúng loại tài liệu.
- **Q16.** Cả ba cấu hình bỏ sót đoạn khuyến nghị ANP ở trang 25. B và C trả về ví dụ liên quan ở trang 27, chỉ đủ grounding mức 1.
- **Chọn C theo quy tắc dev đã chốt.** A đạt test Hit@3 cao hơn đúng một câu trên tập 5 câu. Chênh lệch nhỏ và bộ test chỉ có một câu dùng filter, nên cần thêm câu phân biệt phiên bản, loại tài liệu và ngoại lệ để đánh giá khả năng tổng quát hóa.

Xem results/traces.json, results/benchmark_metrics.json, results/grounding_audit.csv, results/metadata_audit.csv và artifacts/experiment_log.csv để tái kiểm tra.
