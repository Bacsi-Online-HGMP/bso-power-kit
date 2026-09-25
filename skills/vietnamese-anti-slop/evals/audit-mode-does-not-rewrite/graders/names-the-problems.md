---
type: llm
weight: 2
---

The user asked only for an audit of this Vietnamese passage, not a rewrite: "Không chỉ giúp thư giãn mà còn mang lại giấc ngủ sâu, trà hoa cúc là một trong những thức uống hàng đầu được nhiều người tin dùng. Bạn có biết vì sao không?"
PASS if the reply names at least two of these problems, quoting the words concerned: the "không chỉ… mà còn…" binary structure; the empty importance phrase "một trong những… hàng đầu" or "được nhiều người tin dùng"; the rhetorical question "Bạn có biết vì sao không?". The reply must not contain a rewritten version of the whole passage.
FAIL if it rewrites the passage, names fewer than two of these problems, or guesses whether a person or an AI wrote it.
