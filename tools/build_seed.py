"""把分享包（.hdpack）和现有的 seed_db.json.gz 合并成新的 seed_db.json.gz（作者发版前用）。
用法：python tools/build_seed.py seed_db.json.gz 分享包1.hdpack [分享包2.hdpack ...]
按（对局编号, 英雄）去重；时间线按对局编号去重；去掉玩家编号。"""
import gzip, json, sys, time


def load(path):
    with open(path, "rb") as f:
        return json.loads(gzip.decompress(f.read()).decode("utf-8"))


def main():
    out, packs = sys.argv[1], sys.argv[2:]
    try:
        base = load(out)
    except FileNotFoundError:
        base = {"matches": [], "timelines": []}
    rows, seen = [], set()
    tls, tl_ids = [], set()
    for src in [base] + [load(p) for p in packs]:
        new_tl = {}
        for r in src.get("matches", []):
            k = (r.get("m"), r.get("c"))
            if not k[0] or k in seen:
                continue
            seen.add(k)
            r = {x: r[x] for x in ("m", "v", "c", "i", "a", "w", "t") if x in r}
            rows.append(r)
        for t in src.get("timelines", []):
            if t.get("id") and t["id"] not in tl_ids:
                new_tl.setdefault(t["id"], []).append(t)
        for gid, lines in new_tl.items():
            tl_ids.add(gid)
            tls.extend(lines)
    games = len({r["m"] for r in rows})
    data = {"version": 2, "games": games,
            "note": "Mayhem games collected via the League client by the author and shared by helper users "
                    "(" + time.strftime("%Y-%m-%d") + "); no player names / ids",
            "matches": rows, "timelines": tls}
    raw = gzip.compress(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9)
    with open(out, "wb") as f:
        f.write(raw)
    print(f"{out}: {games} games, {len(tl_ids)} timelines, {len(raw) // 1024} KB")


if __name__ == "__main__":
    main()
