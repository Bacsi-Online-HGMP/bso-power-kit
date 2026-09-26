---
type: regex
pattern: '(?:## The revised version|## Bản đã sửa)(?:(?!## (?:What changed|Đã đổi gì))[\s\S])*(Trong cuộc sống hiện đại|phủ nhận rằng|Hãy cùng tìm hiểu|một cách hiệu quả|vô cùng quan trọng)'
flags: i
match: not_contains
weight: 2
---
