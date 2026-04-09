#!/bin/bash
PROXY="socks5://127.0.0.1:1081"
URL="https://api.binance.com/api/v3/ping"
TOTAL=150

success=0
fail=0

for i in $(seq 1 $TOTAL); do
    code=$(curl -x "$PROXY" -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$URL" 2>/dev/null)
    if [ "$code" = "200" ]; then
        success=$((success + 1))
        printf "\r[%d/%d] success=%d fail=%d" "$i" "$TOTAL" "$success" "$fail"
    else
        fail=$((fail + 1))
        printf "\r[%d/%d] success=%d fail=%d (last_code=%s)" "$i" "$TOTAL" "$success" "$fail" "$code"
    fi
done

echo ""
echo "--- Results ---"
echo "Total:   $TOTAL"
echo "Success: $success"
echo "Failed:  $fail"
echo "Rate:    $(echo "scale=1; $success * 100 / $TOTAL" | bc)%"
