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

## Lượt 2026-08-06, phiên hai — sửa bốn quyết định

### `chrome-devtools-mcp` giữ lại, chuyển pack `web` → `seo`

Suýt bị loại vì tưởng Claude in Chrome đã phủ. **Kiểm `~/.claude/plugins/installed_plugins.json`
cho thấy Claude Code không có Claude in Chrome** — Claude in Chrome là Lớp 3, theo tài khoản, chỉ
sống ở Cowork/Desktop. Bỏ nó là để Claude Code mù hẳn trình duyệt.

Và nó không trùng hoàn toàn kể cả ở Cowork. Claude in Chrome có `read_console_messages` và
`read_network_requests`, nhưng **không có** `lighthouse_audit`, `performance_start_trace`,
`take_heapsnapshot`, `emulate`. Đó là toàn bộ phần đo Core Web Vitals mà `searchfit-seo:technical-seo`
cần — nên pack đúng của nó là `seo`, không phải `web`.

*Bài học: trước khi loại một mục vì "đã có thứ khác phủ", phải kiểm thứ kia có ở đúng lớp đó không.*

### `playwright` giữ nguyên quyết định loại

Phần tương tác Claude in Chrome làm được hết. Cái Playwright còn hơn là chạy ngầm, kịch bản test,
đa trình duyệt, CI — BSO không viết test cho web app.

### Nguồn `andrej-karpathy-skills` đã sửa

`forrestchang/andrej-karpathy-skills` → **`multica-ai/andrej-karpathy-skills`**. Tra GitHub search
xác nhận đây là repo gốc đã đổi tên tổ chức (199.884 sao, 20.560 fork), không phải fork.
Vẫn **không có license** — sự thật đó không đổi, chỉ là nguồn nay trỏ đúng chỗ.

Bản `0xwilliamortiz/andrej-karpathy-skills` có MIT và đóng gói sẵn thành plugin Claude Code, nhưng
551 sao — là nhánh, không phải bản chuẩn.

### `frontend-design` đã nhặt xong, vẫn loại

Bốn ý đã vào `bso-marketing/assets/skills/bso-design/SKILL.md`, ghi rõ nguồn:

| Ý | Vì sao đáng nhặt |
|---|---|
| Ba cụm mặc định của ảnh AI, kèm mã màu `#F4F1EA` | Cụ thể hơn hẳn danh sách "dấu hiệu máy làm" cũ — gọi được tên mã màu |
| Mục 10 `Chữ ký` trong `DESIGN.md` | Chín mục cũ tả cái *đúng*; mục này tả cái *đáng nhớ* |
| Cấu trúc phải mã hoá sự thật (phép thử đánh số `01/02/03`) | Chặn đúng lỗi hay gặp ở thumbnail và lower third |
| Chữ trên giao diện: một hành động một tên, lỗi không xin lỗi | Khoảng trống thật — `bso-design` chưa có mục nào về chữ trên nút |

Đây đúng ô thứ ba của bảng `harvest`: **đọc, rút ý, bỏ repo.**

## `mattpocock/skills` — chấm bổ sung

97.679 sao · 8.638 fork · MIT · push 2026-05-20 · 36 skill. Đang bật ở **Lớp 1 (Cowork)**, chưa
từng có trong TSV Lớp 2.

| PH | CP | AT | FR | ĐL | VH | NG | PB | TR | Tổng | Tier |
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| 3 | 5 | 4 | 5 | 3 | 4 | 2 | 5 | 2 | **33** | A |

- **`PH`=3** — chia đôi rõ rệt. Trúng: `handoff` (BSO đã dùng đúng lối này), `writing-great-skills`,
  `grilling`, `diagnosing-bugs`, `code-review`, `teach`, `edit-article`. Trượt: `to-issues`,
  `to-prd`, `triage`, `implement`, `setup-matt-pocock-skills` đều giả định có issue tracker mà BSO
  không có; `migrate-to-shoehorn`, `setup-pre-commit`, `scaffold-exercises` là hệ sinh thái
  TypeScript; `obsidian-vault` không dùng vì kho tri thức BSO chạy OKF.
- **`AT`=4** — MIT, tác giả rõ danh tính. Trừ một điểm vì đường cài mặc định là
  `npx skills@latest add` (chạy mã mạng của bên thứ ba), và vài skill dựng hook Husky, sinh script bash.
- **`ĐL`=3** — README dẫn về newsletter `aihero.dev` và badge `skills.sh`. Không phải SaaS trả phí,
  nhưng có phễu và có phụ thuộc trình cài.
- **`NG`=2** — 36 skill, trong đó **4 `deprecated` + 6 `in-progress` vẫn được ship**, cộng `ask-matt`
  là router chạy trên toàn bộ. Nhiều bề mặt mô tả cho khoảng 8 skill thật sự dùng.
- **`TR`=2** — trùng ba đường: `diagnosing-bugs` ↔ `systematic-debugging`, `tdd` ↔
  `test-driven-development`, `writing-great-skills` ↔ `writing-skills`, `handoff` ↔ plugin `handoff`
  power-kit đang dùng, `code-review` ↔ `code-review` official + `brooks-lint`.

**Không bị luật cắt** (`PH`≠1, `PB`≠1, tier A). Nhưng hai điểm 2 — nếu rơi tier B thì đã bị cắt.
Đây là lỗ hổng cũ ở dạng nhẹ: sàn cứng `PH` không bắt được thứ *nửa hợp nhưng cồng kềnh*.

**Kết luận: đừng cài cả 36.** Đúng cách xử là thứ đã định cho `superpowers` và `ecc` — rút phần
dùng được thành một bộ gộp. `mattpocock` là nguồn thứ ba của bộ đó, không phải một plugin nữa
để bật.

## Lượt 2026-08-06, phiên ba — sửa một lỗi chấm, chốt bộ gộp

### ⚠ Sửa điểm `mattpocock/skills`: `NG` 2 → 3, tổng 33 → **34**

Lần chấm trước đếm **36 skill** bằng cách `find` file `SKILL.md` trên đĩa. Sai. Đọc
`.claude-plugin/plugin.json` cho thấy plugin chỉ ship **19 skill** — `deprecated/` (4),
`in-progress/` (6), `misc/` (4), `personal/` (2) **không có trong manifest**, chúng nằm trong
repo nhưng không được đóng gói.

Tỉ lệ dùng được là **11/19**, không phải 8/36. `NG` = 3.

*Bài học, ghi để không lặp: **đếm skill bằng manifest của plugin, không bằng `find` trên đĩa.**
Repo chứa nhiều hơn thứ nó phát hành.*

### Bộ gộp: bỏ ý tưởng gộp, cài thẳng `mattpocock-skills`

Ba trong bốn skill định lấy đều từ mattpocock. Với 11/19 dùng được, tách ra là **dựng một bản
fork phải tự bảo trì** để đổi lấy rất ít — trái thẳng luật *"mở rộng cái đang chạy, đừng dựng
cái thứ hai"*. Nên cài nguyên bộ, pack `code`.

Đối chiếu từng cặp trùng, và vì sao mattpocock thắng:

| Việc | Bản thắng | Bản thua | Lý do |
|---|---|---|---|
| Chốt kế hoạch | `grilling` (10 dòng) | `brainstorming` (159) | Hỏi từng câu · mỗi câu tự đề xuất đáp án · tra được trong code thì tra. Bản superpowers có `<HARD-GATE>` cấm viết code trước khi có design doc commit vào `docs/superpowers/specs/` — quá nặng, và ghi vào đường dẫn riêng của nó |
| Tìm lỗi | `diagnosing-bugs` (134) | `systematic-debugging` (296) | Dạy phần khó thật: dựng vòng lặp pass/fail trước, 10 cách cụ thể, cấm đoán khi chưa có loop |
| Viết skill | `writing-great-skills` (82) | `writing-skills` (689) | Cùng việc, 1/8 kích thước |
| Viết test | *(bỏ cả hai)* | `tdd` · `test-driven-development` | BSO không có test suite |

### `verification-before-completion` tách ra thành plugin lẻ

Mattpocock không có skill nào tương đương, và đây là thứ chặn đúng lỗi BSO **đã mắc thật** —
bản handoff cũ từng ghi sai danh sách "chưa commit", bài học trong file đó là *"đọc `git status`
trước khi tin"*.

Giữ cả `superpowers` chỉ vì một skill trong mười bốn thì không đáng, nên chép riêng nó ra
`plugins/verification-before-completion/`: **nguyên văn, chỉ thêm frontmatter ghi công**
(`license: MIT` · `source` · `author: Jesse Vincent`) và kèm `LICENSE`. Thân file có dòng cấm sửa —
cần cập nhật thì chép lại từ nguồn, đừng vá tay.

`superpowers` và `ecc` nay nằm ở `plugins-loai.tsv`.

### Va chạm hai skill `handoff` — xử bằng mô tả, không fork

Bản mattpocock ghi handoff vào **thư mục tạm của hệ điều hành**; bản power-kit ghi
`HANDOFF-<ngày>.md` vào thư mục làm việc. `CLAUDE.md` của BSO chốt file trạng thái phiên sống ở
gốc dự án, nên bản power-kit đúng.

Không fork mattpocock để gỡ skill kia. Thay vào đó **làm mô tả bản power-kit thắng rõ ràng**:
thêm câu *"THIS is the handoff to use when the handoff file must live in the working folder …
prefer it over any handoff skill that writes to a temporary directory."*

Nhân tiện nhặt ba ý của bản mattpocock vào bản power-kit: mục `## Suggested skills` cuối tài
liệu · không chép lại thứ đã nằm trong commit/ADR/plan mà trỏ đường dẫn · che thông tin nhạy cảm.

### Sửa kèm: marketplace power-kit đang hỏng

`claude plugin validate .` báo **2 lỗi có sẵn từ trước**, không do lượt này: `ai-research-skills`
khai `./02-tokenization/huggingface-tokenizers` và `./02-tokenization/sentencepiece`, nhưng thư
mục `02-tokenization/` **không tồn tại**. `build-standalone.sh` chỉ `cp -R` nguyên thư mục, không
loại trừ gì — nên đây là lỗi của bản upstream, không phải lỗi bước đóng gói.

Đã gỡ hai mục chết (98 → 96 skill). Validate nay **pass**. Đây là sửa vào file của bên thứ ba,
ghi lại ở đây để lần sau đối chiếu khi cập nhật bản upstream.

## Ba công cụ nén token — chấm 2026-08-06, loại cả ba

Ứng viên do người dùng đưa. **Không phải bản thay `caveman`** — `caveman` cắt chữ Claude *viết ra*,
ba cái này nén thứ *đi vào*. Khác khâu, nên `TR` chỉ ở mức 3, không phải cuộc đấu trùng lặp.

| Repo | Sao | License | PH CP AT FR ĐL VH NG PB | TR | Tổng | Tier | Bị loại vì |
|---|:--:|---|---|:--:|:--:|:--:|---|
| `alexgreensh/token-optimizer` | 1.811 | **PolyForm NC 1.0.0** | 3 5 2 **1** 3 4 4 4 | 3 | **29** | B | `FR`=1 |
| `headroomlabs-ai/headroom` | 65.018 | Apache-2.0 | **2** 4 **2** 5 3 4 **2** 5 | 3 | **30** | B | ba điểm 2 |
| `ooples/token-optimizer-mcp` | 466 | MIT | 2 **1** 2 5 4 4 2 3 | 3 | **26** | B | `CP`=1 |

### `alexgreensh/token-optimizer` — giấy phép cấm dùng thương mại

GitHub hiển thị `NOASSERTION`; đọc thẳng file `LICENSE` thì là **PolyForm Noncommercial License 1.0.0**.

BSO bán thực phẩm bảo vệ sức khoẻ. Dùng công cụ cấm thương mại vào dây chuyền sản xuất nội dung
bán hàng là **vi phạm giấy phép**, không phải chuyện khẩu vị. `FR`=1 vì miễn phí nhưng BSO không
dùng hợp pháp được nếu không mua giấy phép riêng.

*Đây là lần đầu luật cắt bắt một mục vì giấy phép. Ghi lại: `NOASSERTION` trên GitHub không có
nghĩa "không có license" — nó có nghĩa **GitHub không nhận dạng được**, và phải mở file ra đọc.*

### `headroomlabs-ai/headroom` — proxy chắn giữa mọi request

65k sao, Apache-2.0, push 2026-08-05, có `.claude-plugin/marketplace.json`. Repo mạnh. Vẫn loại.

- **`AT`=2** — `headroom wrap` dựng một **proxy cục bộ**, **tự cài Serena**, rồi chạy agent qua
  proxy đó. Mọi request đi qua một lớp trung gian, kể cả nội dung `core/claims-matrix/`. Repo có
  ghi *local-first* và *reversible*, nhưng vẫn là thêm một chỗ dữ liệu compliance chảy qua và tự
  cài thêm một công cụ thứ hai mà không hỏi.
- **`PH`=2** — con số quảng cáo là *60–95% cho JSON*, còn *15–20% cho coding agent*. Ngữ cảnh nặng
  của BSO là **markdown tiếng Việt** — luật, claim, handoff — không phải JSON. BSO rơi đúng vào
  vạch thấp.
- **`NG`=2** — thư viện + proxy + MCP, hàng loạt extras, một extras cần cả toolchain C++.

Bản `SCORING.md` cũ đã gặp `headroom` một lần và xếp *MESH → caveman* với 63 điểm. Thước mới cho 30
và loại hẳn. Hai lần đo độc lập ra cùng một kết luận.

### `ooples/token-optimizer-mcp` — `CP`=1, chặn cứng

Đây là mục duy nhất chạm trục compliance, và nó chạm rất mạnh. README nói thẳng cơ chế:

> *"It makes the expensive call impossible. Install the plugin and a built-in `Read` of a 200 KB
> file is **denied**, with the refusal naming the cached, [summarised] record."*

`CLAUDE.md` của BSO có một luật không được phép sai: **chỉ trích nguyên văn từ `core/claims-matrix/`;
diễn đạt lại claim đã duyệt cũng là tạo claim mới.** Một lớp cache **từ chối `Read` và trả về bản
tóm tắt** là nguyên tắc cốt lõi đẩy thẳng tới vi phạm — đúng định nghĩa `CP`=1 trong thước.

Thêm nữa: 466 sao là mức xác nhận quá mỏng cho một thứ chặn tool built-in của agent.

### Ý nhặt được — `harvest`

| Nguồn | Ý |
|---|---|
| `alexgreensh` | *"Find the ghost tokens"* — **đo cái gì đang ăn ngữ cảnh trước khi tối ưu.** Cowork đã có sẵn skill `explain-usage` làm đúng việc này, không cần cài gì |
| `headroom` | Nén phải **đảo ngược được**. Bất kỳ bước rút gọn nào trong dây chuyền BSO cũng phải giữ đường về bản gốc |
| `ooples` | Đọc thống kê cache từ **transcript của chính client**, không tự khai — nguyên tắc đo lường tốt |

**Kết luận: không cài gì. `caveman` giữ nguyên.** Ba cái này giải bài toán ngữ cảnh bằng cách xen
một lớp vào giữa Claude và dữ liệu. Với một repo mà sai một chữ trong claim là vi phạm nghị định,
lớp xen giữa ấy là rủi ro chứ không phải tiện ích.

## Còn treo

1. ~~**Bộ skill gộp chưa dựng.**~~ **ĐÓNG (2026-08-06)** — bỏ ý tưởng gộp, cài thẳng
   `mattpocock-skills`, tách riêng `verification-before-completion`. Xem phiên ba bên trên.
   *Ghi lại phần cũ để đối chiếu:* Ba nguồn `superpowers` (14 skill, MIT) · `ecc` (47 skill ở
   `.agents/skills/`, MIT) · `mattpocock` (36 skill, MIT) — cả ba MIT nên tách được, chỉ cần giữ
   dòng ghi công. Mỗi chức năng **phải chọn một bản**, nếu không bộ mới lại đẻ ra đúng cái mâu
   thuẫn mà `CLAUDE.root.md` cấm. Dựng xong thì gỡ được `superpowers` (`NG`=2) và `ecc` (`NG`=1)
   khỏi danh sách cài.
2. ~~**`ecc` vào kho nhưng chưa quyết bật**~~ **ĐÓNG** — loại hẳn, vào `plugins-loai.tsv`.
3. ~~**`mattpocock/skills` chưa vào TSV**~~ **ĐÓNG** — đã vào, pack `code`.
4. **`andrej-karpathy-skills` vẫn không có license.** Nguồn đã trỏ đúng, nhưng chưa ghim commit.
5. **`ai-research-skills` đã bị sửa tay** (gỡ 2 đường dẫn chết). Cập nhật bản upstream lần sau
   phải kiểm lại `02-tokenization/` đã có chưa, đừng để bản sửa bị đè mất.

## Danh sách cài cuối cùng — 16 plugin

| Pack | Số | Plugin |
|---|:--:|---|
| `core` | 8 | claude-md-management · plugin-dev · skill-creator · commit-commands · desktop-commander · hookify · security-guidance · **verification-before-completion** |
| `code` | 5 | pyright-lsp · code-review · github · andrej-karpathy-skills · **mattpocock-skills** |
| `seo` | 1 | chrome-devtools-mcp |
| `vanphong` | 2 | caveman · ponytail |

67 mục ở `plugins-loai.tsv`. Tổng 83 = 81 đã chấm + `mattpocock-skills` + `verification-before-completion`.
