#!/usr/bin/env bash
# Bundle wardex diagnostic captures into a single shareable file.
set -euo pipefail

OUT="$HOME/wardex-capture-$(date +%Y%m%d-%H%M%S).txt"

write_section() {
    local title="$1"
    local file="$2"
    echo "" >> "$OUT"
    echo "================================================================================" >> "$OUT"
    echo "=== $title" >> "$OUT"
    echo "=== Source: $file" >> "$OUT"
    if [[ -f "$file" ]]; then
        echo "=== Size: $(wc -l < "$file" | tr -d ' ') lines, $(wc -c < "$file" | tr -d ' ') bytes" >> "$OUT"
    else
        echo "=== Size: FILE MISSING" >> "$OUT"
    fi
    echo "================================================================================" >> "$OUT"
    echo "" >> "$OUT"
    if [[ -f "$file" ]]; then
        cat "$file" >> "$OUT"
    else
        echo "(file not found)" >> "$OUT"
    fi
}

echo "Bundling diagnostic captures into: $OUT"

# Header
{
    echo "Wardex diagnostic capture bundle"
    echo "Generated: $(date)"
    echo "Host: $(hostname)"
    echo ""
    echo "Files included:"
    echo "  - /tmp/system-info.txt"
    echo "  - /tmp/wardex-capture.log"
    echo "  - /tmp/dirwatch-capture.log"
    echo "  - /tmp/fsusage-capture.log (head + tail only if large)"
} > "$OUT"

write_section "SYSTEM INFO" "/tmp/system-info.txt"
write_section "WARDEX CAPTURE (full)" "/tmp/wardex-capture.log"
write_section "DIRWATCH CAPTURE (full)" "/tmp/dirwatch-capture.log"

# For fs_usage, include everything if under 5000 lines, else head+tail
FSUSAGE="/tmp/fsusage-capture.log"
if [[ -f "$FSUSAGE" ]]; then
    LINES=$(wc -l < "$FSUSAGE" | tr -d ' ')
    if [[ "$LINES" -lt 5000 ]]; then
        write_section "FSUSAGE CAPTURE (full, $LINES lines)" "$FSUSAGE"
    else
        # Head and tail separately
        echo "" >> "$OUT"
        echo "================================================================================" >> "$OUT"
        echo "=== FSUSAGE CAPTURE (truncated — full file is $LINES lines)" >> "$OUT"
        echo "=== Source: $FSUSAGE" >> "$OUT"
        echo "================================================================================" >> "$OUT"
        echo "" >> "$OUT"
        echo "--- FIRST 500 LINES ---" >> "$OUT"
        head -500 "$FSUSAGE" >> "$OUT"
        echo "" >> "$OUT"
        echo "--- LAST 500 LINES ---" >> "$OUT"
        tail -500 "$FSUSAGE" >> "$OUT"
    fi
else
    write_section "FSUSAGE CAPTURE" "$FSUSAGE"
fi

echo ""
echo "Done. Bundle written to:"
echo "  $OUT"
echo ""
echo "Size: $(wc -l < "$OUT" | tr -d ' ') lines, $(du -h "$OUT" | cut -f1)"
echo ""
echo "To share with Claude, drag this file into the chat or attach it:"
echo "  $OUT"
