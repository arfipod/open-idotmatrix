# Unknown bytes and hypotheses

Use this document to track protocol fields that are not fully understood.

| Area | Offset | Observed values | Hypothesis | Test needed | Status |
|---|---:|---|---|---|---|
| Time | byte 4 | `year & 0xff` or `year % 100` | firmware may ignore year or use app-specific encoding | compare clock/date after sync | open |
| Text header | byte 4 | `00`, possibly non-zero for long payloads | continuation marker | send text >4KB | open |
| GIF header | bytes 5..8 | raw payload or payload+headers | total upload size | compare both modes | open |
| GIF flow | notifications | `0500010001`, `0500010003` | chunk ok / done | log actual notifications | open |
| PNG/DIY | header fields | several | not confirmed | capture app image upload | open |
| Freeze | packet | `04 00 03 00` | freeze/unfreeze or internal mode | visual test | open |
| Reset second packet | `05 00 04 80 50` | same as brightness 80 | recover by brightness + mode reset | compare with brightness alone | open |
