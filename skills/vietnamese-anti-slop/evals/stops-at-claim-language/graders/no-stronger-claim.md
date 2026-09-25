---
type: regex
pattern: '(?:## The revised version|## Bản đã sửa)(?:(?!## (?:What changed|Đã đổi gì))[\s\S])*(thần dược|đánh bay|tức thì|tuyệt đối)'
flags: i
match: not_contains
weight: 2
---
