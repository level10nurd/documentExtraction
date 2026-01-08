"""Debug test to see what's being extracted from each column."""

markdown = """| Item                | Description                                                                              | Description                                                                              | Description                                                                              | Qty              | Qty              | Rate             | Rate             | Amount        |
| 21-054-07 21-055-07 | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 224 268          | 224 268          | 1.59 1.59        | 1.59 1.59        | 356.16 426.12 |"""

line = "| 21-054-07 21-055-07 | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 21-054-07 Stemless Base Assembly - Cyan Blue 21-055-07 Stemless Cup Assembly - Cyan Blue | 224 268          | 224 268          | 1.59 1.59        | 1.59 1.59        | 356.16 426.12 |"

parts = [p.strip() for p in line.split("|")]
parts = [p for p in parts if p]

print("Number of parts:", len(parts))
print()
for i, part in enumerate(parts):
    print(f"Part {i}: {part[:60]}{'...' if len(part) > 60 else ''}")
