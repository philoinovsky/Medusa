#!/bin/bash
PROXY="socks5://127.0.0.1:1081"
URL="https://api.binance.com/api/v3/ping"
TOTAL=500
CONCURRENCY=20

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

worker() {
    local id=$1
    local code
    code=$(curl -x "$PROXY" -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$URL" 2>/dev/null)
    echo "$code" > "$TMPDIR/$id"
}

launched=0
for i in $(seq 1 $TOTAL); do
    worker "$i" &
    launched=$((launched + 1))

    # throttle: wait when hitting concurrency limit
    if [ $((launched % CONCURRENCY)) -eq 0 ]; then
        wait
        success=$(grep -rl '^200$' "$TMPDIR" 2>/dev/null | wc -l)
        done_count=$(ls "$TMPDIR" | wc -l)
        fail=$((done_count - success))
        printf "\r[%d/%d] success=%d fail=%d" "$done_count" "$TOTAL" "$success" "$fail"
    fi
done
wait

success=$(grep -rl '^200$' "$TMPDIR" | wc -l)
fail=$((TOTAL - success))

echo ""
echo "--- Results ---"
echo "Total:       $TOTAL"
echo "Concurrency: $CONCURRENCY"
echo "Success:     $success"
echo "Failed:      $fail"
echo "Rate:        $(echo "scale=1; $success * 100 / $TOTAL" | bc)%"

# breakdown of failure codes
if [ "$fail" -gt 0 ]; then
    echo "Failure breakdown:"
    for f in "$TMPDIR"/*; do
        cat "$f"
    done | grep -v '^200$' | sort | uniq -c | sort -rn | while read count code; do
        echo "  HTTP $code: $count"
    done
fi
