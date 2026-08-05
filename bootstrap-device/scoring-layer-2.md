# Scoring — Layer 2 (Claude Code plugins)

Chấm 81 plugin Lớp 2 theo thước 9 trục ở `bso-marketing/docs/rubric-danh-gia-cong-cu.md`.
Ngày 2026-08-06. Kết quả sinh ra `plugins-claude-code.tsv` (thứ được cài) và
`plugins-loai.tsv` (thứ bị loại, giữ lý do).

## Vì sao lượt này cần thiết

Cột `pack` gán ngày 2026-08-05 là **phân loại tay, không phải chấm điểm**. 62 mục bị gán `bo`
bằng cảm nhận, không mục nào qua luật cắt.

Nặng hơn: `SCORING.md` của repo này **cố ý loại official Anthropic** ("Harold's rule" — thứ
built-in thì không cần chấm). Nên 58 plugin từ `anthropics/claude-plugins-official` chưa từng
được thước nào chấm. Đây là **chấm lần đầu**, không phải chấm lại.

## Lỗ hổng thước phải vá trước khi chấm được

58 plugin chính chủ Anthropic ăn 5 điểm gần như tự động ở `AT FR ĐL VH PB`. `csharp-lsp` ra
**40 điểm = tier S** dù BSO không viết một dòng C# nào. Luật cắt cũ chỉ bắt từ tier B xuống nên
không chạm tới nó.

Đã vá bằng **sàn cứng `PH` = 1 → loại thẳng, độc lập tier** (và `PB` = 1 → loại thẳng). Lý do
đầy đủ ghi trong thước. Đổi lại, mọi điểm `PH` = 1 dưới đây **đều kèm lý do một dòng** — đó là
điều kiện thước đặt ra khi nhận sàn cứng.

## Hai luật loại khác nhau — đừng lẫn

| Luật | Ở đâu | Soi gì |
|---|---|---|
| **Luật cắt** | Thước, mục *Luật cắt* | Chất lượng của **một** mục: sàn `PH`/`PB`, tier, cờ điểm thấp |
| **Luật trùng** | `CLAUDE.root.md` — *trùng nhiều bật một* | Quan hệ giữa **hai** mục |

Trục `TR` **không được dùng trong luật cắt** — thước ghi rõ. Nên 5 mục bị loại vì trùng dưới đây
bị loại theo *luật trùng*, không phải luật cắt. Điểm của chúng vẫn cao.

## Giữ lại — 16 plugin, chấm đủ 9 trục

Cột điểm theo thứ tự `PH CP AT FR ĐL VH NG PB` rồi `TR`.

| Plugin | Nguồn | Pack | PH CP AT FR ĐL VH NG PB | TR | Tổng | Tier | Ghi chú |
|---|---|---|---|:--:|:--:|:--:|---|
| `claude-md-management` | official | core | 5 5 5 5 5 5 5 5 | 5 | **45** | S | CLAUDE.md bốn tầng (gốc · marketing · core · assets) — đúng việc |
| `plugin-dev` | official | core | 5 5 5 5 5 5 5 5 | 5 | **45** | S | BSO tự dựng hai marketplace. Không có gì thay |
| `skill-creator` | official | core | 5 5 5 5 5 5 5 5 | 4 | **44** | S | Trùng nhẹ bản trong bundle Cowork — khác lớp, bật cả |
| `commit-commands` | official | core | 4 5 5 5 5 5 5 5 | 4 | **43** | S | Commit hằng ngày ở hai repo |
| `pyright-lsp` | official | code | 4 5 5 5 5 5 4 5 | 5 | **43** | S | Pipeline video và `okf.py` đều là Python |
| `security-guidance` | official | core | 3 5 5 5 5 5 5 5 | 4 | **42** | S | "Không commit secret" là luật nhà — có lớp máy đỡ thì tốt |
| `hookify` | official | core | 3 5 4 5 5 5 5 5 | 5 | **42** | S | Hook cho `okf check` trước khi push |
| `desktop-commander` | official | core | 5 5 3 5 5 5 4 5 | 4 | **41** | S | **ĐANG DÙNG.** `AT`=3: chạy shell tuỳ ý trên máy thật, quyền rất rộng |
| `code-review` | official | code | 3 5 5 5 5 5 5 5 | 3 | **41** | S | `TR`=3 với brooks-lint và mattpocock — trùng ít, bật cả |
| `caveman` | caveman | van | 3 4 4 5 4 5 5 5 | 5 | **40** | S | 96k sao, push 04-08. Giảm token đầu ra; **không dùng cho chữ ra sản phẩm** |
| `ponytail` | ponytail | van | 3 5 5 5 4 5 5 5 | 3 | **40** | S | 96.5k sao, push 15-07. Văn phong gọn |
| `github` | official | code | 4 5 4 5 5 5 4 5 | 3 | **40** | S | `TR`=3: `gh` CLI đã làm phần lớn |
| `andrej-karpathy-skills` | karpathy-skills | code | 4 5 2 5 5 5 5 4 | 4 | **39** | S | 🟠 **`AT`=2** — xem cảnh báo bên dưới |
| `chrome-devtools-mcp` | official | web | 4 5 4 5 5 5 3 5 | 2 | **38** | S | Trùng ba đường — xem *luật trùng* |
| `superpowers` | official | code | 4 5 5 5 5 4 2 5 | 3 | **38** | S | `NG`=2: 14 skill tự bắn. Nặng nhất trong nhóm giữ |
| `ecc` | ecc | code | 2 4 3 5 4 4 1 5 | 3 | **31** | A | 238k sao. `NG`=1 — agent OS đầy đủ. Giữ trong kho, **cân nhắc không bật** |

### 🟠 `andrej-karpathy-skills` — repo đã đổi chủ

Nguồn trong TSV ghi `forrestchang/andrej-karpathy-skills`. GitHub API trả về
**`multica-ai/andrej-karpathy-skills`** — repo đã chuyển chủ, đường cũ còn chạy nhờ redirect.
Repo **không có license**, push cuối 2026-04-20.

Theo thước, "tác giả nghi fork" là dấu hiệu `AT` thấp; chuyển chủ + mất license đúng ô đó. Tổng
39 điểm nên luật cắt không bắt được — **đây là quyết định người, không phải quyết định của thước.**
Hai đường: sửa nguồn thành `multica-ai/...` và ghim commit, hoặc bỏ và giữ luật trong skill nhà làm.
Chưa quyết, chưa sửa nguồn.

### `ecc` — giữ trong kho, chưa nên bật

`NG`=1 là điểm nặng nhất trong nhóm giữ: ECC là một agent harness đầy đủ (agent + command + hook
+ skill + MCP). Đúng luật *kho rộng tay, bật chặt* thì nó vào TSV nhưng nằm ở pack `code`, chỉ cài
khi có việc thật cần.

## Loại theo luật trùng — 5 plugin, điểm vẫn cao

Không mục nào ở đây kém. Chúng bị loại vì **có mục khác cùng miền hợp BSO hơn**.

| Plugin | Điểm | Thua ai | Vì sao bên kia thắng |
|---|:--:|---|---|
| `frontend-design` | 39 (S) | `bso-design` | Mang nhận diện BSO; `bso-design` đã gộp bốn nguồn |
| `claude-code-setup` | 41 (S) | `bootstrap-device` | Bộ cài nhà có cột `pack` và biết ba lớp plugin |
| `playwright` | 38 (S) | `chrome-devtools-mcp` | Cùng điều khiển trình duyệt; DevTools đọc được console và network |
| `remember` | 37 (A) | memory Cowork | Trí nhớ đã có sẵn theo tài khoản, không cần lớp thứ hai |
| `huggingface-skills` *(bản official)* | 35 (A) | — | Kéo 19 skill ML; cả 19 đều bị sàn `PH` loại bên dưới |

`chrome-devtools-mcp` trùng **ba** đường: bản official (giữ), bản trong marketplace `claude-power-kit`,
và Claude-in-Chrome ở Cowork. Bật **một** — bản official, vì nó theo Claude Code và không cần
build-standalone.

## Loại theo sàn cứng `PH` = 1 — 44 plugin

Mỗi dòng kèm lý do, đúng điều kiện thước đặt ra khi nhận sàn cứng.

| Plugin | Lý do `PH` = 1 |
|---|---|
| `csharp-lsp` · `jdtls-lsp` · `php-lsp` · `clangd-lsp` · `typescript-lsp` | BSO không viết C#, Java, PHP, C/C++, TypeScript |
| `auth0` · `firebase` · `supabase` · `vercel` · `expo` | Hạ tầng ứng dụng web/mobile — BSO không có sản phẩm phần mềm |
| `coderabbit` · `greptile` | Review code dạng SaaS trả phí, trùng `code-review` miễn phí |
| `circleback` · `mintlify` · `datarobot-agent-skills` · `dataverse` · `fiftyone` | SaaS ngoài miền: họp, docs, AutoML, CRM Microsoft, dataset thị giác |
| `discord` · `telegram` · `imessage` · `fakechat` | Kênh chat không phải kênh của BSO (YouTube · Facebook · Zalo) |
| `data` · `data-engineering` | Kho dữ liệu, ETL — BSO không có |
| `agent-sdk-dev` · `atomic-agents` · `mcp-server-dev` · `mcp-tunnels` · `mcp-apps` | Dựng agent/MCP để bán hoặc phát hành; BSO chỉ tiêu thụ |
| `microsoft-docs` | Tra tài liệu Microsoft — không chạm việc nào |
| `math-olympiad` | Toán thi — lệch hẳn miền |
| `playground` · `ralph-loop` | Thử nghiệm vòng lặp agent, không gắn việc nào đang chạy |
| `firecrawl` | Scraping cần key trả phí; thước còn cảnh báo ToS ở mục 2 |
| 19 plugin `huggingface-skills` | Huấn luyện và triển khai mô hình ML: `hf-cli` · `hf-mem` · `huggingface-best` · `huggingface-community-evals` · `huggingface-datasets` · `huggingface-gradio` · `huggingface-llm-trainer` · `huggingface-local-models` · `huggingface-lora-space-builder` · `huggingface-paper-publisher` · `huggingface-papers` · `huggingface-spaces` · `huggingface-tool-builder` · `huggingface-trackio` · `huggingface-vision-trainer` · `huggingface-zerogpu` · `train-sentence-transformers` · `transformers-js` · `trl-training`. BSO dùng mô hình qua API, không huấn luyện |

## Loại theo luật cắt thường — 6 plugin

Không chạm sàn `PH` nhưng rơi tier B kèm cờ, hoặc `PH` = 2 mà không có việc thật.

| Plugin | PH | Vì sao |
|---|:--:|---|
| `pr-review-toolkit` | 2 | BSO push thẳng `main`, chưa có luồng PR — `CLAUDE.md` ghi rõ "chưa có lớp chặn nào trên `main`" |
| `code-modernization` | 2 | Không có codebase cũ cần hiện đại hoá; hai pipeline video đang chạy tốt |
| `feature-dev` | 2 | BSO không phát triển tính năng phần mềm |
| `code-simplifier` | 2 | Trùng `code-review`, và mã BSO là script ngắn |
| `session-report` | 2 | `HANDOFF-*.md` viết tay đang làm đúng việc này, hợp bối cảnh hơn |
| `explanatory-output-style` · `learning-output-style` · `ai-plugins` | 2 | Đổi giọng đầu ra của Claude, không chạm việc sản xuất |

## Ý cần hấp thụ — `harvest` từ thứ đã loại

Đúng ô thứ ba của bảng `harvest` trong thước: **không cài, đọc rút ý**.

| Nguồn | Ý cần rút |
|---|---|
| `session-report` | Cấu trúc mục nó sinh ra — đối chiếu với `HANDOFF-*.md` xem thiếu mục nào |
| `pr-review-toolkit` | Danh mục kiểm trước khi merge — dùng làm checklist tay cho `core/claims-matrix/`, nơi push thẳng `main` là rủi ro thật |
| `firecrawl` | Cách nó tách nội dung chính khỏi khung trang — hữu ích nếu tự viết bước đọc nghị định |
| `caveman` | Đã cài. Nguyên tắc "bỏ từ nối, giữ danh từ" đáng soi lại `vietnamese-anti-slop` |

## Còn treo

1. **Nguồn `andrej-karpathy-skills` chưa sửa** — vẫn trỏ `forrestchang/...`. Quyết rồi mới sửa.
2. **`ecc` vào kho nhưng chưa quyết bật** — `NG`=1.
3. **`assets/tools/index.md` bên `bso-marketing` ghi `bootstrap-device — empty`** — index sinh tự động
   đã sai từ trước, nay thư mục đã chuyển đi hẳn nên phải sinh lại.
