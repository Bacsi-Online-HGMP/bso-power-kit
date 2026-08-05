#!/usr/bin/env bash
# Xuất trạng thái plugin Claude Code của MÁY NÀY ra plugins-claude-code.tsv.
# Chạy trên máy đang dùng tốt, commit file kết quả, rồi máy mới chạy bootstrap-plugins.sh.
#
# bash 3.2 (macOS mặc định) chạy được — không dùng mapfile, không dùng mảng kết hợp.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/plugins-claude-code.tsv"
DENY="$HERE/plugins-loai.tsv"
SRC="$HOME/.claude/plugins"

[ -d "$SRC" ] || { echo "Không thấy $SRC — máy này chưa cài Claude Code?" >&2; exit 1; }

python3 - "$SRC" "$OUT" "$DENY" <<'PY'
import json, sys, datetime, os
src, out, deny_path = sys.argv[1], sys.argv[2], sys.argv[3]
km = json.load(open(os.path.join(src, 'known_marketplaces.json')))
ip = json.load(open(os.path.join(src, 'installed_plugins.json')))['plugins']

# Cột `pack` do người gán, không suy ra được từ trạng thái máy.
# Đọc lại bản cũ để GIỮ NGUYÊN — nếu không, mỗi lần export là mất sạch phân loại.
old_pack = {}
if os.path.exists(out):
    for line in open(out):
        if line.startswith('#'):
            continue
        f = line.rstrip('\n').split('\t')
        if len(f) >= 4 and f[0] == 'plugin' and f[3]:
            old_pack[f[1]] = f[3]

# Plugin đã bị loại theo thước — đọc để KHÔNG kéo chúng trở lại danh sách cài.
# Không có file này thì mọi quyết định loại sẽ bị xoá sạch ở lần export sau.
deny = {}
if os.path.exists(deny_path):
    for line in open(deny_path):
        if line.startswith('#'):
            continue
        f = line.rstrip('\n').split('\t')
        if len(f) >= 3 and f[0]:
            deny[f[0]] = f[2]

lines = [
    '# Sinh tự động bởi export-plugins.sh — đừng sửa tay, TRỪ cột `pack`.',
    '# Sinh lúc: ' + datetime.datetime.now().isoformat(timespec='seconds'),
    '# Cột: loại<TAB>tên<TAB>nguồn<TAB>pack',
    '#',
    '# pack: core | code | web | vanphong | video | noidung | design | seo | ? (chưa phân loại)',
    '# Chỉ áp cho dòng `plugin`. Marketplace luôn thêm hết — kho rộng tay, bật chặt.',
    '# Cột này người gán tay và export giữ nguyên qua các lần sinh lại.',
    '#',
    '# Mục đã loại nằm ở plugins-loai.tsv, không xuất hiện ở đây. Chấm điểm: scoring-layer-2.md',
]

local = []
for name, info in sorted(km.items()):
    s = info.get('source', {})
    kind = s.get('source')
    if kind == 'github':
        ref = s['repo']
    elif kind == 'git':
        ref = s['url']
    elif kind == 'directory':
        ref = s['path']
        local.append(name)
    else:
        ref = json.dumps(s, ensure_ascii=False)
    lines.append(f'marketplace\t{name}\t{ref}\t')

rows = sorted((k.partition('@')[2], k.partition('@')[0]) for k in ip)
new = []
blocked = []
for mk, n in rows:
    if n in deny:
        blocked.append((n, deny[n]))
        continue
    pack = old_pack.get(n, '?')
    if n not in old_pack:
        new.append(n)
    lines.append(f'plugin\t{n}\t{mk}\t{pack}')

open(out, 'w').write('\n'.join(lines) + '\n')
written = len(rows) - len(blocked)
print(f'Đã ghi {out}')
print(f'  {len(km)} marketplace, {written} plugin (bỏ qua {len(blocked)} mục đã loại)')

kept = written - len(new)
print(f'  giữ pack cũ cho {kept} plugin')
if blocked:
    print(f'  ⓘ máy này đang cài {len(blocked)} plugin đã bị loại — không ghi vào TSV:')
    for n, rule in blocked:
        print(f'    - {n}  [{rule}]')
    print('    Gỡ bằng: claude plugin uninstall <tên>   · muốn phục hồi thì xoá dòng ở plugins-loai.tsv')
if new:
    print(f'  ⚠ {len(new)} plugin MỚI chưa có pack (đang để "?"), sẽ không cài trừ khi --all:')
    print('    ' + ', '.join(new))
    print('    Gán pack rồi commit, nếu không máy mới sẽ bỏ qua chúng.')
if local:
    print('  ⚠ marketplace đăng ký kiểu THƯ MỤC LOCAL, máy mới sẽ không có: ' + ', '.join(local))
    print('    Đăng ký lại bằng URL git trước khi commit file này.')
PY
