#!/usr/bin/env bash
# Cài lại toàn bộ plugin Claude Code trên MÁY MỚI, theo plugins-claude-code.tsv.
#
# Chỉ lo LỚP 2 (plugin Claude Code, cài theo máy).
# Lớp 1 (plugin Cowork) theo tài khoản Claude, tự có sau khi đăng nhập.
# Lớp 3 (MCP connector) phải cấp quyền tay. Xem bso-marketing/docs/thiet-bi-moi.md.
#
# Danh sách đã qua thước 9 trục ngày 2026-08-06: giữ 16, loại 65.
# Điểm từng mục: scoring-layer-2.md · Lý do loại: plugins-loai.tsv
#
# Chạy khô để xem sẽ làm gì:  ./bootstrap-plugins.sh --dry-run
# bash 3.2 (macOS mặc định) chạy được.
#
# GÓI (pack) — cột 4 của TSV. Marketplace luôn thêm HẾT; chỉ plugin mới lọc theo gói.
# Đúng luật nhà: kho cứ rộng tay, danh sách bật phải chặt.
#
#   ./bootstrap-plugins.sh                    # chỉ gói 'core'
#   ./bootstrap-plugins.sh --pack core,code   # nhiều gói, ngăn bằng dấu phẩy
#   ./bootstrap-plugins.sh --all              # tất, kể cả gói '?' chưa phân loại
#   ./bootstrap-plugins.sh --list-packs       # xem có gói nào, mỗi gói mấy plugin
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LIST="$HERE/plugins-claude-code.tsv"
DRY=0
ALL=0
LISTPACKS=0
PACKS="core"

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)    DRY=1 ;;
    --all)        ALL=1 ;;
    --list-packs) LISTPACKS=1 ;;
    --pack)       shift; PACKS="${1:-}"
                  [ -n "$PACKS" ] || { echo "--pack cần tên gói." >&2; exit 1; } ;;
    --pack=*)     PACKS="${1#--pack=}" ;;
    -h|--help)    sed -n '2,20p' "$0"; exit 0 ;;
    *)            echo "Không hiểu tham số: $1" >&2; exit 1 ;;
  esac
  shift
done

[ -f "$LIST" ] || { echo "Không thấy $LIST" >&2; exit 1; }

if [ "$LISTPACKS" = 1 ]; then
  echo "Gói có trong $(basename "$LIST"):"
  awk -F'\t' '$1=="plugin"{p=($4==""?"?":$4); c[p]++} END{for(k in c) printf "  %-10s %3d plugin\n", k, c[k]}' "$LIST" | sort
  echo
  echo "'?' = chưa phân loại. Chỉ cài khi dùng --all."
  exit 0
fi

command -v claude >/dev/null || { echo "Chưa có lệnh 'claude' trong PATH." >&2; exit 1; }

# bash 3.2: không có mảng kết hợp. Dùng chuỗi có ngăn cách để tra.
PACKSEL=",$(echo "$PACKS" | tr -d ' '),"
in_pack() {
  [ "$ALL" = 1 ] && return 0
  case "$PACKSEL" in *",$1,"*) return 0;; esac
  return 1
}

run() {
  if [ "$DRY" = 1 ]; then echo "  [khô] $*"; else "$@"; fi
}

if [ "$ALL" = 1 ]; then
  echo "Gói: TẤT CẢ (--all)"
else
  echo "Gói: $PACKS   — thêm gói khác bằng --pack a,b · xem danh sách bằng --list-packs"
fi
echo

# --- Bước 1: marketplace ---------------------------------------------------
# Phải xong trước, không thì lệnh install không biết lấy plugin ở đâu.
echo "== Marketplace (luôn thêm hết, không lọc theo gói) =="
while IFS="$(printf '\t')" read -r kind name ref pack; do
  case "$kind" in \#*|'') continue;; esac
  [ "$kind" = "marketplace" ] || continue

  case "$ref" in
    /*)
      echo "  ✗ $name — đăng ký kiểu thư mục local ($ref). Bỏ qua."
      echo "    Máy cũ phải đăng ký lại bằng URL git rồi chạy export-plugins.sh lần nữa."
      continue
      ;;
  esac

  echo "  + $name  <- $ref"
  run claude plugin marketplace add "$ref" || echo "    ⚠ thất bại: $name (repo private? chưa đăng nhập đúng tài khoản gh?)"
done < "$LIST"

# --- Bước 2: plugin --------------------------------------------------------
echo
echo "== Plugin =="
FAIL=""
SKIP=0
DONE=0
while IFS="$(printf '\t')" read -r kind name ref pack; do
  case "$kind" in \#*|'') continue;; esac
  [ "$kind" = "plugin" ] || continue

  [ -n "${pack:-}" ] || pack="?"
  if ! in_pack "$pack"; then
    SKIP=$((SKIP + 1))
    continue
  fi

  echo "  + $name@$ref  [$pack]"
  DONE=$((DONE + 1))
  if ! run claude plugin install "$name@$ref"; then
    FAIL="$FAIL $name@$ref"
  fi
done < "$LIST"

echo
echo "Cài $DONE plugin, bỏ qua $SKIP (ngoài gói đang chọn)."
if [ -n "$FAIL" ]; then
  echo "⚠ Cài hỏng:$FAIL"
  echo "  Thường do marketplace ở bước 1 không thêm được. Sửa nguồn rồi chạy lại."
  exit 1
fi
echo "✔ Xong. Mở lại Claude Code hoặc chạy /reload-plugins."
echo
echo "Nhắc: đây là LỚP 2 (plugin Claude Code). Plugin Cowork ở LỚP 1 theo tài khoản Claude,"
echo "không script được — phải bật tay trong UI. Danh sách ở docs/chon-cong-cu-2026-08-05.md."
