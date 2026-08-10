# Đánh giá & xếp hạng 55 repo (Scraping / Management / Claude Skills / khác)

*Ngày lập: 2026-08-05 · Số liệu GitHub lấy trực tiếp qua API cùng ngày · Phục vụ hệ sinh thái Bacsi Online / HGMP*

> **Cảnh báo dùng nội bộ.** Đây là đánh giá kỹ thuật để chọn công cụ, KHÔNG phải tư vấn pháp lý. Ba nhóm rủi ro xuyên suốt cần nhớ:
> 1. **Cài skill/plugin từ GitHub = chạy chỉ thị + script của người lạ trên máy bạn.** Luôn đọc `SKILL.md` và `install.sh`/`setup.sh` trước khi chạy, không `curl | bash` mù.
> 2. **Mọi công cụ scraping/auto-post đều có thể vi phạm ToS nền tảng** (khoá tài khoản) và một số vi phạm pháp luật (bypass SSL, bypass paywall).
> 3. **Không repo nào biết quy định TPBVSK Việt Nam.** Mọi title/script/caption chúng sinh ra phải qua skill `supplement-compliance` trước khi đăng.

---

## 1. Khung chấm điểm

Mỗi repo chấm 1–5 trên 6 trục (5 = tốt nhất cho bối cảnh Bacsi Online):

| Trục | Ý nghĩa | 5 điểm | 1 điểm |
|---|---|---|---|
| **PH** – Phù hợp/Ứng dụng | Giải đúng việc của kênh y tế + HGMP | Dùng ngay, đúng nhu cầu | Lệch hoặc trùng công cụ đã có |
| **AT** – An toàn/Bảo mật | ToS, xử lý credential, script cài, quyền ghi | Read-only, không key, không vi phạm | Bypass/scrape lậu, ghi tài khoản, xin cookie |
| **PB** – Phổ biến/Sức sống | Sao, fork, còn bảo trì | Nhiều sao + push gần đây | Ít sao hoặc chết/archived |
| **FR** – Free | Chi phí bản thân repo | Free hoàn toàn | Bắt buộc trả tiền |
| **ĐL** – Độc lập vs SaaS | Có phải phễu bán SaaS không | Độc lập, tự chủ | Vỏ mỏng dẫn về SaaS trả phí |
| **VH** – Chi phí vận hành | Tốn API/model/hạ tầng khi chạy | Chạy chay $0 | Cần nhiều API trả phí |

**Xếp hạng tổng (Tier):** S (nên dùng/nghiên cứu ngay) · A (tốt, có điều kiện) · B (dùng được cho việc hẹp) · C (thận trọng) · D (tránh / chỉ tham khảo).

Ký hiệu cảnh báo: 🔴 rủi ro pháp lý/ToS cao · 🟠 cần key/credential nhạy cảm · 🟣 phễu SaaS · ⚰️ chết/archived/lỗi thời · ⭐ điểm sáng triết lý.

---

## 2. Bảng tổng hợp số liệu thật (đối chiếu số sao bạn đưa)

Số sao bạn liệt kê phần lớn khớp. Vài chỗ lệch đáng chú ý:

| Repo | Sao bạn ghi | Sao thật | Ghi chú quan trọng |
|---|---|---|---|
| youtube/api-samples | 6.0k | 6 017 | ⚰️ **ARCHIVED**, official Google nhưng đóng băng (push cuối 2024-06) |
| Schmavery/facebook-chat-api | 1.9k | 1 947 | ⚰️ **ARCHIVED** 2021, unofficial, vi phạm ToS FB |
| drawrowfly/tiktok-scraper | 5.2k | 5 166 | ⚰️ push cuối **2023-05**, TikTok đã đổi API → nhiều khả năng hỏng |
| pytube/pytube | 13.2k | 13 160 | ⚰️ push cuối 2024-08, nổi tiếng hay hỏng theo thay đổi YouTube |
| ytdl-org/youtube-dl | 140.9k | 140 872 | Còn sống yếu; bản bảo trì thực tế là **yt-dlp** (repo khác) |
| Jamie-Landeg-Jones/youtube-dl | 37 | 38 | Chỉ là **fork** của youtube-dl, không có giá trị riêng |
| ZeroPointRepo/youtube-skills | 485 | 487 | 🟣 phễu về TranscriptAPI (trả phí credit) |
| AgriciDaniel/claude-ads | 7.8k | 7 828 | ⭐ kỷ luật kỹ thuật cao nhất nhóm |
| AgriciDaniel/claude-seo | 13.4k | 13 364 | ⭐ repo lớn nhất của tác giả này |
| mvanhorn/last30days-skill | 57.3k | 57 278 | **Bạn đã cài sẵn** (`/last30days` có trong máy) |

*Số sao rất cao ≠ hợp với bạn. youtube-dl 140k là công cụ tải video, không liên quan làm nội dung.*

---

## 3. NHÓM SCRAPING (13 repo)

| Repo | PH | AT | PB | FR | ĐL | VH | Tier | Cờ |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **mathiaschu/watch** | 5 | 5 | 3 | 5 | 5 | 4 | **S** | ⭐ no-key, on-device |
| **guimatheus92/mcp-video-analyzer** | 5 | 4 | 3 | 5 | 4 | 4 | **A** | MCP, npm, bảo trì tốt |
| davidteather/TikTok-Api | 3 | 3 | 5 | 5 | 4 | 3 | B | 🟠 dùng cookie/Webshare |
| supadata-ai/mcp | 4 | 3 | 3 | 3 | 2 | 3 | B | 🟣🟠 SaaS Supadata |
| ZeroPointRepo/youtube-skills | 4 | 3 | 4 | 2 | 2 | 3 | B | 🟣 phễu TranscriptAPI |
| rugvedp/Trends-MCP | 3 | 3 | 2 | 4 | 4 | 3 | B | 🟠 RapidAPI, scrape Later.com |
| apismith-labs/tiktok-transcript-api | 3 | 3 | 1 | 2 | 2 | 3 | C | 🟣 phễu Apify Actor |
| ytdl-org/youtube-dl | 2 | 4 | 5 | 5 | 5 | 5 | C | ⚰️ dùng yt-dlp thay thế |
| Tyrrrz/YoutubeDownloader | 2 | 4 | 4 | 5 | 5 | 5 | C | GUI tải video, ít liên quan |
| pytube/pytube | 2 | 3 | 4 | 5 | 5 | 5 | C | ⚰️ hay hỏng |
| drawrowfly/tiktok-scraper | 2 | 2 | 4 | 5 | 5 | 4 | D | ⚰️🔴 chết + scrape |
| **Zskkk/tiktok-ssl-bypass-skill** | 1 | 1 | 1 | 5 | 5 | 2 | **D** | 🔴 bypass SSL pinning, Frida |
| Jamie-Landeg-Jones/youtube-dl | 1 | 4 | 1 | 5 | 5 | 5 | D | fork trùng lặp |

**Kết luận nhóm:** thứ bạn thực sự cần là **"cho agent xem/nghe video"**, không phải tải hàng loạt.

- **mathiaschu/watch** là lựa chọn số 1: yt-dlp + ffmpeg + Whisper chạy **on-device, không API key, không telemetry, không lưu cookie**. Đúng tinh thần một kênh y tế cần kín đáo. Nó chính là phiên bản gọn của skill `youtube-video-perception` bạn vừa dùng.
- **mcp-video-analyzer** mạnh hơn (OCR khung hình, cache, nhiều nguồn) nếu cần xử lý bulk; đánh đổi là thêm phụ thuộc npm + tuỳ chọn TwelveLabs trả phí.
- 🔴 **tiktok-ssl-bypass-skill: tránh tuyệt đối.** Bypass chứng chỉ SSL của app là kỹ thuật tấn công, rủi ro pháp lý thật, không có chỗ trong quy trình marketing hợp chuẩn.
- Các repo tải video (youtube-dl/pytube/YoutubeDownloader) và scraper TikTok cũ: chỉ giữ **yt-dlp** làm hạ tầng nền, bỏ qua phần còn lại.

---

## 4. NHÓM MANAGEMENT / PUBLISHING (9 repo)

| Repo | PH | AT | PB | FR | ĐL | VH | Tier | Cờ |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **pipeboard-co/meta-ads-mcp** | 4 | 3 | 4 | 3 | 2 | 3 | **A** | 🟣 Pipeboard, Meta Business Partner |
| youtube/api-samples | 3 | 5 | 5 | 5 | 5 | 5 | B | ⚰️ archived nhưng là mẫu code chuẩn |
| iscale-llc/iscale-facebook-ad-builder | 3 | 3 | 2 | 4 | 4 | 2 | B | 🟠 full-stack, nhiều key |
| ndesv21/socialclaw | 3 | 3 | 2 | 3 | 2 | 3 | B | 🟣 dịch vụ getsocialclaw |
| makiisthenes/TiktokAutoUploader | 3 | 2 | 4 | 5 | 5 | 4 | C | 🔴 upload lậu bằng session |
| wanglinsaputra/OmniPost-AI | 2 | 2 | 1 | 4 | 4 | 3 | C | 🔴 auto-post qua DOM trình duyệt |
| brodyautomates/ig-setter | 2 | 2 | 1 | 4 | 4 | 3 | C | 🟠 tự trả lời DM IG |
| warifp/FacebookToolkit | 1 | 1 | 4 | 5 | 5 | 4 | D | 🔴⚰️ bot/scrape FB, PHP cũ |
| Schmavery/facebook-chat-api | 1 | 1 | 4 | 5 | 5 | 4 | D | 🔴⚰️ archived, unofficial |

**Kết luận nhóm:** đây là nhóm **rủi ro nhất** vì nó *ghi* ra tài khoản thật.

- Publishing tự động qua reverse-engineering session (TiktokAutoUploader) hoặc điều khiển DOM (OmniPost, ig-setter) đều **dễ khoá tài khoản** và không có kiểm soát an toàn. Với thương hiệu bác sĩ, một lần khoá kênh là mất trắng uy tín tích luỹ.
- Đường đúng nếu cần đăng tự động: dùng **API chính thức có OAuth** (mẫu ở `youtube/api-samples` dù đã archived vẫn là code tham chiếu tốt), hoặc MCP có kiểm soát ghi như hướng của `pipeboard-co/meta-ads-mcp` (là Meta Business Partner được duyệt — an toàn hơn hẳn scraper, đổi lại là phễu SaaS Pipeboard).
- Ghi chú license: `meta-ads-mcp` để **NOASSERTION** (không license rõ) → cân nhắc khi tái sử dụng mã.

---

## 5. NHÓM CLAUDE SKILLS (31 repo)

Chia theo tác giả/chất lượng để dễ đọc.

### 5A. Hệ AgriciDaniel — "kỷ luật bằng chứng" ⭐ (điểm sáng lớn nhất cả danh sách)

| Repo | PH | AT | PB | FR | ĐL | VH | Tier |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **AgriciDaniel/claude-blog** | 5 | 5 | 4 | 5 | 5 | 3 | **S** |
| **AgriciDaniel/anti-slop** | 5 | 5 | 2 | 5 | 5 | 5 | **S** |
| **AgriciDaniel/claude-ads** | 4 | 5 | 5 | 5 | 5 | 3 | **A** |
| **AgriciDaniel/claude-seo** | 4 | 4 | 5 | 5 | 5 | 3 | **A** |
| AgriciDaniel/youtuber (YouTube Brain) | 4 | 5 | 2 | 5 | 5 | 4 | A |
| AgriciDaniel/claude-shorts | 4 | 4 | 3 | 5 | 4 | 3 | A |
| AgriciDaniel/claude-repurpose | 4 | 4 | 3 | 5 | 4 | 3 | A |

Đây là bộ đáng **nghiên cứu để bắt chước cách làm**, dù không cài nguyên. Xem mục 7 (triết lý).

- **claude-blog**: kiến trúc 3 tầng (orchestrator → 31 sub-skill → agent + script), **5-Gate Delivery Contract** chặn giao hàng nếu chưa qua kiểm định, 5-category quality scoring, "brain" bằng chứng có nguồn. Rất hợp để dựng cỗ máy blog HGMP.
- **anti-slop**: bộ dò "văn AI" nhưng thiết kế để **không bao giờ tự kết luận tác giả**; mọi dấu hiệu phải route sang một thủ tục sinh ra *artifact người kiểm được*. Triết lý "evidence discipline" cực kỳ giá trị cho môi trường y tế cần trích dẫn.
- **claude-ads**: adapter **read-only mặc định**, muốn ghi phải qua 6 điều kiện (capability bật, ID rõ, diff before/after, phê duyệt, idempotency+rollback, verify precondition). Đây là **khuôn mẫu an toàn** nên áp cho mọi thứ đụng tài khoản thật.
- **youtuber (YouTube Brain)**: "maturity gates" 5 mức, điểm bị **trần hoá theo độ chín** — không thể sửa markdown để tự phong "market-ready". Chống thổi phồng nội bộ.

### 5B. Hệ sergebulaev — phễu Publora 🟣

| Repo | PH | AT | PB | FR | ĐL | VH | Tier |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| sergebulaev/linkedin-skills | 3 | 3 | 4 | 4 | 2 | 4 | B |
| sergebulaev/facebook-skills | 3 | 3 | 1 | 4 | 2 | 4 | B |
| sergebulaev/x-skills | 2 | 3 | 2 | 4 | 2 | 4 | B |
| sergebulaev/instagram-skills | 2 | 3 | 1 | 4 | 2 | 4 | C |
| sergebulaev/tiktok-skills | 2 | 3 | 1 | 4 | 2 | 4 | C |
| sergebulaev/threads-skills | 2 | 3 | 1 | 4 | 2 | 4 | C |

- Phần copywriting và **"voice rules"** (cấm em dash, cấm từ AI "leverage/delve/unlock", số cụ thể thay tính từ, title là lời hứa không phải tóm tắt) rất tốt — **nên trích riêng làm tài liệu tham khảo**.
- Điểm trừ: đường đăng đi qua **Publora** (SaaS bên thứ ba, video upload lên S3 của họ, cần API key, trần 512MB). Không nên bật cho nội dung y tế. Bản thân skill mỏng, giá trị nằm ở references.

### 5C. Skill lớn / độc lập đáng chú ý

| Repo | PH | AT | PB | FR | ĐL | VH | Tier | Ghi chú |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **mvanhorn/last30days-skill** | 5 | 4 | 5 | 4 | 4 | 3 | **S** | Bạn đã có sẵn. Research đa nguồn có chấm điểm cộng đồng |
| **rushindrasinha/youtube-shorts-pipeline** | 4 | 4 | 5 | 5 | 5 | 3 | **A** | ⭐ anti-hallucination gate, niche-profile |
| **hassancs91/claude-youtube-editor** | 4 | 4 | 3 | 5 | 4 | 2 | **A** | Pipeline dựng video "trung thực về chi phí" |
| **MaxKmet/idea-validation-agents** | 4 | 5 | 4 | 5 | 5 | 4 | **A** | Không key; hợp validate sản phẩm HGMP (xem thêm mục 6) |
| Affitor/affiliate-skills | 3 | 3 | 4 | 4 | 3 | 3 | B | ⭐ "flywheel" 8 giai đoạn, chain_metadata |
| nicojunk/claude-ig | 3 | 4 | 1 | 5 | 4 | 4 | B | ⭐ 7 quality gate có G3 "phải disclose affiliate" |
| bradautomates/content-ideas | 3 | 3 | 3 | 3 | 3 | 3 | B | 🟠 ScrapeCreators API; render HTML feed học ý |
| aaaronmiller/create-viral-content | 3 | 4 | 2 | 5 | 5 | 4 | B | ⭐ 6 lượt "adversarial refine" + khung đạo đức |
| Hao0321/claude-skill-social-post | 3 | 2 | 4 | 5 | 4 | 4 | B | 🔴 auto-post DOM FB; nhưng 7 công thức < 5K-fan hay |
| zubair-trabzada/ai-ads-claude | 3 | 3 | 3 | 5 | 4 | 3 | B | 15 skill quảng cáo, 5 agent song song |
| Hainrixz/claude-ads | 3 | 3 | 2 | 4 | 3 | 3 | B | ⭐ mô hình 3-tier chi phí minh bạch |
| itchernetski/threads-carousel-claude-skill | 3 | 4 | 2 | 5 | 4 | 4 | B | Text → carousel PNG/PDF, design-system 4 trục |
| iart-ai/tiktok-video-skills | 3 | 4 | 1 | 4 | 3 | 4 | B | 🟣 phễu iart.ai; grammar hook→retention→loop |
| Maartenlouis/remotion-ads | 3 | 4 | 2 | 5 | 4 | 2 | B | Remotion + ElevenLabs, caption theo từ |
| moboutrig/instagram-claude-skill | 2 | 4 | 1 | 5 | 4 | 4 | C | 🟠 IG Graph API chính thức (an toàn hơn scraper) |

### 5D. Skill nhỏ / một tác giả / phễu cá nhân (giá trị hẹp)

| Repo | Tier | Ghi chú |
|---|:--:|---|
| rediumvex/viral-hooks-skill | C | 100 công thức hook — dùng như thư viện tham khảo |
| rediumvex/ai-video-generator-claude | C | 🟠 phễu prompt cho Higgsfield/Seedance (trả phí) |
| rediumvex/social-media-caption-generator-claude | C | Caption 7 nền tảng, mỏng |
| dylanpakd-cyber/lazyreel | C | 🟣 MCP "doomscroll" 21B view, nguồn đóng |

---

## 6. CÁC REPO LẺ

| Repo | Nhóm | PH | AT | PB | FR | ĐL | VH | Tier | Ghi chú |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **DojoCodingLabs/remotion-superpowers** | Video edit | 4 | 4 | 2 | 5 | 5 | 3 | **A** | Plugin free biến Remotion thành studio; 5 MCP; cần vài key |
| **joeseesun/anything-to-notebooklm** | →NotebookLM | 4 | 2 | 5 | 5 | 4 | 3 | **B** | 🔴 có tính năng **bypass paywall** (rủi ro pháp lý); 15+ nguồn→podcast/PPT/mindmap |
| **akitaonrails/tiktok_analysis** | Privacy | 3 | 5 | 1 | 5 | 5 | 5 | **B** | ⭐ Không phải tool mà là **báo cáo dịch ngược** TikTok — đọc để hiểu rủi ro dữ liệu |
| **MaxKmet/idea-validation-agents** | Idea | 4 | 5 | 4 | 5 | 5 | 4 | **A** | Đã chấm ở mục 5C; validate ý tưởng, không cần key |

- **remotion-superpowers**: nếu Dr. Hiếu dựng video bằng code (Remotion), đây là bộ mạnh và free, có cả tầng "see/hear/analyze". Đáng thử trong nhánh sản xuất.
- **anything-to-notebooklm**: ý tưởng "bất kỳ nội dung → NotebookLM" rất hợp để biến tài liệu y khoa thành podcast/mindmap học tập. **Nhưng** module bypass paywall là lằn ranh pháp lý — nếu dùng, phải tắt phần đó và chỉ đưa nội dung bạn có quyền.
- **tiktok_analysis**: giữ làm tài liệu tham khảo an ninh dữ liệu, không phải công cụ.

---

## 7. TRIẾT LÝ / WORKFLOW / PIPELINE ĐÁNG GIỮ

Đây là phần giá trị nhất — chắt lọc để tái dùng cho hệ Bacsi Online/HGMP, kể cả khi không cài repo nào.

### 7.1. Kỷ luật bằng chứng (evidence discipline) — *AgriciDaniel/anti-slop, youtuber, claude-ads*
- **Mọi con số phải trỏ về một nguồn có ngày trong "source ledger"** (URL + ngày lấy + tier bằng chứng + giới hạn). Không nguồn = không được nêu claim. → Áp thẳng cho nội dung TPBVSK: mỗi công dụng phải neo về tài liệu được phép.
- **Không tự kết luận, chỉ đưa artifact người kiểm được.** anti-slop không bao giờ phán "cái này do AI viết"; nó chỉ ra khuyết điểm cụ thể kiểm chứng được.
- **Không cho model tự gác cửa sửa của chính nó** — scanner chạy lại sau khi sửa (chống "rubber-stamp" tự khen).

### 7.2. Delivery Contract có nhiều "gate" — *claude-blog (5 gate), nicojunk/claude-ig (7 gate)*
- Nội dung **không được giao nếu chưa qua các cổng**: đủ định dạng → kiểm thị giác (screenshot 3 khổ màn hình) → điểm review ≥ 90, 0 lỗi P0 → link/asset trả về 200.
- Orchestrator **tự lặp lại tối đa 3 lần** trước khi đẩy lên người. → Mô hình lý tưởng cho quy trình: *soạn → tự kiểm compliance → tự kiểm chất lượng → mới trình duyệt*.
- Quality gate kiểu "zero tolerance": ví dụ `/ig` có **G3 = không bao giờ tạo nội dung affiliate mà thiếu disclosure**. Đây chính là chỗ nhét guardrail TPBVSK vào.

### 7.3. Maturity gates — chống thổi phồng — *AgriciDaniel/youtuber*
- 5 mức chín: Scaffolded → Researched → Domain-adapted → Demo-verified → Market-ready. **Điểm bị trần theo mức chín; không thể sửa markdown để nhảy hạng.** Rất hợp để quản trị chất lượng khi có nhiều người cùng làm.

### 7.4. Orchestrator + agent chuyên biệt song song — *claude-ads, Hainrixz/claude-ads, ai-ads-claude, claude-blog*
- Một "nhạc trưởng" giữ phạm vi + tổng hợp; **nhiều agent chuyên sâu chạy song song**, mỗi agent có checklist riêng, nạp reference **on-demand (kiểu RAG)**, trả về **cả Markdown (người đọc) lẫn JSON (máy đọc, validate theo schema)**.
- **Một agent bắt buộc lỗi → cả run bị đánh dấu "partial", không bao giờ trình như bản đầy đủ.** Trung thực về độ phủ bằng chứng (graded ≥80% / provisional 60–79% / insufficient <60%).

### 7.5. Khuôn an toàn cho hành động ghi tài khoản — *AgriciDaniel/claude-ads*
Muốn cho AI *ghi* vào tài khoản thật, bắt buộc đủ 6 lớp: (1) capability đã test & bật, (2) ID tài khoản/đối tượng rõ, (3) diff before/after kèm "blast radius", (4) chủ phê duyệt trong trần định sẵn, (5) idempotency key + audit + rollback + cửa sổ verify, (6) verify state remote vẫn khớp precondition. **Xoá vĩnh viễn: không hỗ trợ.** → Nên là chính sách chung của bạn cho mọi automation đụng kênh thật.

### 7.6. Niche-profile điều phối cả pipeline — *rushindrasinha/youtube-shorts-pipeline*
- Một file YAML "niche profile" nạp một lần, **định hình mọi khâu**: giọng script, phong cách hình, nhạc, thumbnail. Đổi profile = đổi toàn bộ "chất" mà không phải sửa prompt từng chỗ.
- **Anti-hallucination gate**: khâu Research bơm sự thật (tên/số/claim) từ nguồn thật; LLM bị buộc *chỉ dùng dữ liệu research, không dùng kiến thức huấn luyện*. → Cực kỳ hợp nội dung y tế.
- Có **"$0.00 mode"** (Ollama local + Edge TTS) — làm chủ chi phí.

### 7.7. Flywheel khép kín, skill nối skill — *Affitor/affiliate-skills*
- 8 giai đoạn Research → Content → Blog/SEO → Offers → Distribution → Analytics → Automation → Meta, với **Analytics vòng lại Research**. Mỗi skill khai báo `chain_metadata.suggested_next` để **agent tự nối chuỗi**, truyền dữ liệu qua ngữ cảnh hội thoại chứ không copy-paste file.

### 7.8. Refine bằng nhiều "nhân vật phản biện" — *aaaronmiller/create-viral-content*
- 6 lượt tinh luyện đối kháng: The Skeptic → The Expert → The Scroller → The Competitor → The Editor → (thumbnail). Kèm **khung đạo đức tường minh** (được: đánh bóng ý mình, chuyển chuyên môn thành nội dung dễ hiểu; cấm: astroturf, tin sai, mạo danh). → Khung đạo đức này gần như bắt buộc cho bác sĩ.

### 7.9. Voice rules chống giọng AI — *sergebulaev family, anti-slop, viral-hooks*
- Cấm em dash; viết hoa tên riêng; cấm từ sáo AI; **số cụ thể thắng tính từ**; **title là lời hứa + payoff cụ thể, không tóm tắt**; **title và thumbnail là một cặp, không lặp chữ**; **30 giây đầu (3 giây với Short) mới là thuật toán thật — bỏ intro**.

### 7.10. Perception privacy-first — *mathiaschu/watch*
- Xem/nghe video mà **không key, không telemetry, transcribe on-device, cookie đọc live không lưu**. Chuẩn mực về quyền riêng tư cho một tổ chức y tế.

### 7.11. "Feedback loop tự học" bằng thao tác người dùng — *bradautomates/content-ideas*
- Render một trang HTML tự chứa, người dùng ▲/▼ từng ý; phản ứng được lưu làm **substrate cá nhân hoá** cho lần sau. Mô hình "widget + học dần" đáng bắt chước.

---

## 8. KHUYẾN NGHỊ HÀNH ĐỘNG CHO BACSI ONLINE

**Dùng/nghiên cứu ngay (Tier S–A, an toàn):**
- Perception video: **mathiaschu/watch** (hoặc giữ skill `youtube-video-perception` đang có).
- Research trước khi làm nội dung/họp: **last30days** (đã cài).
- Học kiến trúc để dựng cỗ máy nội dung riêng: **AgriciDaniel/claude-blog + anti-slop + claude-ads** (đọc, không cần cài nguyên).
- Validate ý tưởng sản phẩm/nội dung HGMP: **MaxKmet/idea-validation-agents** (không key).
- Nếu làm video pipeline: tham khảo **youtube-shorts-pipeline** (anti-hallucination + niche profile) và **remotion-superpowers / claude-youtube-editor** cho khâu dựng.

**Chỉ lấy tinh hoa, không cài:**
- Voice rules + hook formulas (sergebulaev, viral-hooks, create-viral-content) → gộp thành 1 tài liệu house-style.
- Các "gate / evidence ledger / maturity gate" → nhúng vào skill `supplement-compliance` hiện có.

**Tránh:**
- 🔴 tiktok-ssl-bypass, TiktokAutoUploader, OmniPost-AI, ig-setter, FacebookToolkit, facebook-chat-api — mọi thứ ghi tài khoản bằng reverse-engineering/DOM.
- 🟣 Không bật đường Publora / TranscriptAPI / Supadata / Apify cho nội dung y tế trừ khi có lý do rõ; ưu tiên API chính thức.
- ⚰️ Bỏ qua repo chết/archived trừ khi đọc code tham khảo (youtube/api-samples là ngoại lệ đáng đọc).
- Bypass paywall trong anything-to-notebooklm: tắt, chỉ đưa nội dung có quyền.

**Luật vàng bao trùm:** mọi title/script/caption do bất kỳ skill nào sinh ra → **chạy qua `supplement-compliance` trước khi đăng**. Các công thức hook "shock/curiosity-gap" là nơi dễ đẻ claim công dụng vi phạm nhất.

---

*Nguồn số liệu: GitHub REST API (`/repos/{owner}/{repo}` và README raw), truy vấn 2026-08-05. Điểm số là đánh giá định tính theo bối cảnh Bacsi Online, không phải chỉ số khách quan tuyệt đối.*
