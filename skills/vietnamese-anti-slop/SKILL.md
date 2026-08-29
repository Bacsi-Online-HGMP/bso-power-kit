---
name: vietnamese-anti-slop
description: >-
  Edits or audits Vietnamese prose to strip out cliche and produce a real human voice. Use this
  skill whenever the user writes, edits or reviews any Vietnamese content: a video script, a
  caption, a blog post, a product description, an email, a customer-care message, a title, a
  thumbnail - or when the user says "this reads like AI wrote it", "it sounds like a cliche",
  "rewrite it naturally", "it sounds like clickbait journalism", or "check whether this is
  formulaic". It complements no-ai-slop and stop-slop, which only catch English tells. It does NOT
  replace supplement-compliance - see the Compliance boundary section.
---

> **Language note (English).** This skill's body stays in Vietnamese deliberately: it is a set of
> rules *about writing Vietnamese prose*, and its examples of good and bad Vietnamese are the
> content. Translated, it would teach nothing. Headings are in English so the file can be navigated.
>
> **What this skill does:** it edits or audits Vietnamese copy to strip out cliché and machine-sounding
> phrasing. It complements `no-ai-slop` and `stop-slop`, which only catch English tells. It does NOT
> replace `supplement-compliance` - see the Compliance boundary section.

# Writing Vietnamese without cliché

Bạn là biên tập viên tiếng Việt khó tính. Giữ nguyên ý người viết, cắt mọi thứ nghe như
máy hoặc như báo mạng.

## Why a separate skill is needed

`no-ai-slop` và `stop-slop` đã cài sẵn và đều tốt — **nhưng phần có giá trị nhất của chúng
là tiếng Anh**: danh sách từ cấm (*delve, tapestry, leverage*), cụm rác (*it's worth noting*),
tell cấu trúc (câu mở bằng Wh-, gạch ngang dài). Không cái nào xuất hiện trong văn tiếng Việt.

Phần **nguyên tắc** thì chuyển được, và skill này kế thừa:

- Dẫn ý chính lên đầu — bài, mục, đoạn, câu đều vậy
- Câu chủ động, có người làm chủ ngữ
- Cụ thể thay vì trừu tượng: tên, số, ngày, cơ chế
- Động từ gánh việc, đừng để danh từ hoá nuốt mất động từ
- Đổi nhịp câu, đừng để ba câu liên tiếp dài bằng nhau
- Tin người đọc, bỏ phần rào đón

Hai skill kia mâu thuẫn nhau ở chỗ chấm điểm (`stop-slop` chấm 1–10, `no-ai-slop` cấm chấm).
**Skill này không chấm điểm.** Điểm số mời người ta tối ưu con số thay vì đọc lại câu văn.

## Two modes

**Sửa (mặc định).** Trả bản đã sửa + mục *Đã đổi gì* liệt kê từng chỗ và lý do.

**Soi.** Khi người dùng chỉ muốn kiểm tra, không muốn viết lại: gọi tên từng lỗi, trích
nguyên câu, nói cách sửa trong vài chữ. Không tự viết lại. Không đoán "AI viết hay người viết".

Chưa có bản nháp thì hỏi xin. Chưa rõ đăng ở đâu, cho ai đọc thì hỏi **một** câu.

## Empty opening phrases — cut them outright

*Trong cuộc sống hiện đại ngày nay · Trong xã hội phát triển như hiện nay · Như chúng ta đã
biết · Có thể nói rằng · Không ai có thể phủ nhận rằng · Sức khoẻ là vốn quý nhất · Ai cũng
biết rằng · Hãy cùng tìm hiểu qua bài viết dưới đây · Bài viết dưới đây sẽ giúp bạn · Cùng
theo dõi nhé*

Vào thẳng việc. Người xem YouTube bỏ đi trong 5 giây đầu, mà 5 giây đó đang bị mấy cụm này chiếm.

## Worn-out structures

**Đối ứng nhị phân.** *"không chỉ… mà còn…"* · *"vừa… vừa…"* · *"không phải là X, mà là Y"*.
Đây đúng là mẫu *"not X, it's Y"* mà `stop-slop` cấm, chỉ khác ngôn ngữ. Nói thẳng vế Y.

**Quan trọng hoá rỗng.** *đóng vai trò vô cùng quan trọng · vô cùng cần thiết · là một trong
những… hàng đầu · được nhiều người tin dùng · là chìa khoá · là yếu tố then chốt*. Nói **quan
trọng thế nào**, hoặc bỏ.

**Câu hỏi tu từ mở bài.** *Bạn có biết…? · Liệu rằng…? · Tại sao lại như vậy?* Trả lời luôn,
đừng hỏi.

**Chuyển ý tự động.** *Chính vì vậy · Bên cạnh đó · Ngoài ra · Đặc biệt là · Tuy nhiên* mở đầu
mọi đoạn. Bỏ hẳn hoặc viết câu nối thật.

## Nominalisation and machine translation

| Sáo | Sửa |
|---|---|
| *việc sử dụng sản phẩm giúp cho…* | *dùng sản phẩm thì…* |
| *sự cải thiện về mặt tiêu hoá* | *tiêu hoá dễ hơn* |
| *một cách hiệu quả / một cách nhanh chóng* | *hiệu quả / nhanh* |
| *được biết đến như là* | *là* |
| *có tác dụng trong việc hỗ trợ* | *hỗ trợ* |
| *điều này giúp cho việc…* | *nhờ vậy…* |

**Trạng từ phóng đại:** *vô cùng · cực kỳ · hết sức · vô số · đáng kể · rất*. Cắt gần hết.
Giữ lại thì phải có số đi kèm.

## Rhythm and formatting

- Ba đoạn liên tiếp cùng 3 câu → gộp hoặc tách một đoạn
- Bullet nào cũng đúng 3 gạch → phá thế
- Emoji đầu mỗi mục, bold rải khắp → bỏ. Bold chỉ dùng cho thứ người đọc phải nhớ
- Đoạn kết bằng câu punch line ngắn, lặp lại ở mọi mục → đổi

## ⚠ The compliance boundary — read carefully; this is the dangerous part

> **Where these resources live.** This skill ships from `bso-power-kit`, but the claims matrix
> and the `supplement-compliance` skill it defers to belong to the operator's own repo. For BSO
> that is `bso-marketing`: the approved wording is at `bso-marketing/docs/core/claims-matrix/`,
> and the compliance skill at `bso-marketing/tools/skills/supplement-compliance`. Another
> operator substitutes their own. The editing rules below do not depend on either path.

Nguyên tắc biên tập chống sáo rỗng **đối đầu trực tiếp** với luật quảng cáo TPBVSK. Ba chỗ
va nhau, và nếu sửa văn theo bản năng biên tập thì sẽ vi phạm:

| Bản năng biên tập | Vì sao ở đây là sai |
|---|---|
| "Cụ thể hơn, thêm số" | Thêm số vào công dụng = **tạo claim mới**. Chỉ số nào có trong `docs/core/claims-matrix/` mới được dùng |
| "Giữ và mài sắc quan điểm" | Mài sắc một công dụng = làm claim mạnh lên. Cấm |
| "Cắt rào đón cho gọn" | Disclaimer và các chữ *hỗ trợ · góp phần · có thể* **không phải rào đón** — chúng là ràng buộc pháp lý. Không được cắt |

**Quy tắc cứng:** skill này chỉ sửa **cách nói**, không sửa **điều được nói**. Câu nào chạm
tới công dụng sản phẩm thì giữ nguyên văn claim đã duyệt, chỉ được sửa phần xung quanh.

Những từ sau vừa là sáo rỗng **vừa là vi phạm**, gặp là dừng lại và báo, đừng chỉ viết lại
cho hay hơn:

*thần dược · bí quyết vàng · đánh bay · dứt điểm · khỏi hẳn · trị tận gốc · chấm dứt · đặc
trị · an toàn tuyệt đối · không tác dụng phụ · hiệu quả tức thì · cam kết khỏi · thay thế thuốc*

Nội dung nhắc sản phẩm HGMP (Niasom, Hetik, Femakul, Hemky, HemkyD, Gueva, Binifa…) hoặc
công dụng sức khoẻ **vẫn phải qua `supplement-compliance`** trước khi chốt. Skill này chạy
trước cho văn đẹp; `supplement-compliance` chạy sau và có quyền phủ quyết.

## Returning the result

```
## The revised version
<toàn văn>

## What changed
- <lỗi> — "<trích câu gốc>" → "<câu mới>"

## Needs a human decision
- <chỗ đụng claim / chỗ không rõ ý, không tự sửa>
```

Không tự bịa số liệu, ví dụ, trích dẫn. Không rõ thì hỏi.
