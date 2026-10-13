"""回测（2.15）：推荐到底有没有让人赢更多？
用法：python tools/backtest.py <matches.jsonl> [--test 0.4] [--max 4000]
  · 考题＝最新版本里最后 40% 的对局（按对局编号＝时间顺序）；其余的对局当自建数据库（训练），考题不会混进去。
  · 对考题里的每个玩家：
      装备 —— 拿掉其中一件、其它最终装备当作身上已有，看推荐清单里这件的分数（跟当时第一名差多少）、在不在前 5；
      增幅 —— 拿掉其中一张、其它当已选，算这张的分数（自建库部分 / 本局调整部分），跟所有增幅的平均比；
      路线 —— 最终出装的主路线是不是模型预估胜率最高的那条。
  · 再用逻辑回归看这些分数能不能预测输赢（控制英雄强度）。
网上数据（ARAMKit）需要连网，这里不含：回测只检查本局调整、自建库、路线这几部分。"""
import argparse, collections, copy, json, math, os, random, sys, tempfile, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("matches")
    ap.add_argument("--test", type=float, default=0.4)
    ap.add_argument("--max", type=int, default=4000)
    ap.add_argument("--live", default=None, help="任一份 last_live.json 当模板")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    import haidou_helper as h
    rows = collections.OrderedDict()
    for line in open(a.matches, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        g = rows.setdefault(r["m"], [])
        if len(g) < 10:
            g.append(r)
    games = {k: v for k, v in rows.items() if len(v) == 10}
    vers = sorted({g[0].get("v", "") for g in games.values()}, key=h.ver_tuple)
    newest = [k for k in sorted(games) if games[k][0].get("v") == vers[-1]]
    test_ids = set(newest[int(len(newest) * (1 - a.test)):])
    print("games", len(games), "newest patch", vers[-1], len(newest), "test games", len(test_ids))
    # 训练用的自建数据库
    db_dir = os.path.join(h.APP_DIR, "riotdb")
    os.makedirs(db_dir, exist_ok=True)
    with open(os.path.join(db_dir, "matches.jsonl"), "w", encoding="utf-8") as f:
        for k, g in games.items():
            if k not in test_ids:
                for r in g:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for fn in ("pathmodel.json", "state.json"):
        p = os.path.join(db_dir, fn)
        if os.path.exists(p):
            os.remove(p)
    gd, st = h.load_all("zh_TW", "all", True, log=lambda m: None)
    adv = h.Advisor(gd, st)
    db = h.RiotCollector(gd)
    db.advisor = adv
    adv.riotdb = db
    db.maybe_path(force=True)
    tpl = json.load(open(a.live or os.path.join(h.APP_DIR, "last_live.json"), encoding="utf-8"))
    p0 = tpl["allPlayers"][0]
    aug_name = {}
    for x in adv.all_index.values():
        if x.get("id") and x["id"] not in aug_name:
            aug_name[x["id"]] = x["name"]
    all_augs = [x for x in adv.aug_index.values()]

    def raw_for(g, me_i, items_override=None):
        raw = copy.deepcopy(tpl)
        raw["allPlayers"] = []
        raw["events"] = {"Events": []}
        raw["gameData"]["gameTime"] = 1200.0
        for i, r in enumerate(g):
            c = gd.champ(r["c"]) or {}
            p = copy.deepcopy(p0)
            p["championName"] = c.get("name", r["c"])
            p["rawChampionName"] = "game_character_displayname_" + c.get("id", r["c"])
            p["riotId"] = p["summonerName"] = "P{0}#X".format(i)
            p["riotIdGameName"] = "P{0}".format(i)
            p["team"] = "ORDER" if bool(r.get("w")) == bool(g[me_i].get("w")) else "CHAOS"
            its = items_override if (i == me_i and items_override is not None) else r.get("i") or []
            p["items"] = [{"itemID": iid, "slot": k, "count": 1, "price": gd.item_price(iid)} for k, iid in enumerate(its)]
            p["level"] = 16
            p["isDead"] = False
            p["scores"] = {"kills": 5, "deaths": 5, "assists": 10, "creepScore": 0, "wardScore": 0}
            raw["allPlayers"].append(p)
        raw["activePlayer"]["riotId"] = "P{0}#X".format(me_i)
        return raw

    out = []
    tids = sorted(test_ids)
    random.seed(1)
    t0 = time.time()
    for gi, gid in enumerate(tids):
        g = games[gid]
        for me_i, r in enumerate(g):
            if len(out) >= a.max:
                break
            big = [i for i in r.get("i") or [] if gd.is_completed(i) and not gd.is_boots(i)]
            augs = [aug_name.get(x) for x in r.get("a") or []]
            augs = [x for x in augs if x]
            rec = {"m": gid, "c": r["c"], "w": 1 if r.get("w") else 0, "items": [], "augs": []}
            # 装备
            for j, iid in enumerate(big):
                others = [x for x in (r.get("i") or []) if x != iid]
                state = h.parse_live(raw_for(g, me_i, others))
                mode, map_id, me, allies, enemies, _ = state
                my_augs = [adv.find_aug(n) for n in augs]
                my_augs = [x for x in my_augs if x]
                t = adv.team_threat(enemies, [], allies, [], me)
                adv._ema_cid = None                      # 不要把上一个状态的平滑带进来
                lst, _ = adv.recommend_items(me, allies, enemies, my_augs, t, map_id, 0, k=500, cs=None)
                lst = [x for x in lst if not x.get("boots")]
                if not lst:
                    continue
                top = max(x["total"] for x in lst)
                mean = sum(x["total"] for x in lst) / len(lst)
                hit = next((k for k, x in enumerate(lst) if x["id"] == iid), None)
                x = lst[hit] if hit is not None else None
                rec["items"].append({"rank": hit, "gap": (x["total"] - top) if x else None,
                                     "rel": (x["total"] - mean) if x else None, "n": len(lst)})
                if j == 0:
                    rt = adv._route
                    rec["route_by_wr"] = bool(rt.get("by_wr"))
            # 路线：最终出装主路线 vs 模型（没有装备时）的预定路线
            state = h.parse_live(raw_for(g, me_i, []))
            mode, map_id, me, allies, enemies, _ = state
            my_augs = [x for x in (adv.find_aug(n) for n in augs) if x]
            t = adv.team_threat(enemies, [], allies, [], me)
            route = adv.build_route(me, my_augs, None, allies, enemies, None)
            kinds = [adv.item_kind_id(i) for i in big]
            kinds = [k for k in kinds if k]
            rec["path"] = collections.Counter(kinds).most_common(1)[0][0] if kinds else None
            rec["route"] = route["kind"]
            rec["route_wr"] = {k: v[0] for k, v in (route.get("wr") or {}).items()}
            # 增幅
            state_full = h.parse_live(raw_for(g, me_i))
            _, _, me_f, allies_f, enemies_f, _ = state_full
            t_f = adv.team_threat(enemies_f, [], allies_f, [], me_f)
            adv._route = adv.build_route(me_f, my_augs, None, allies_f, enemies_f, None)
            prof = adv.my_profile(me_f, my_augs)
            for n in augs:
                mine = [x for x in my_augs if x["name"] != n]
                pool = [adv.score_aug(x, prof, t_f, mine, me_f, None, 2) for x in all_augs]
                m_tot = sum(x["total"] for x in pool) / len(pool)
                m_own = sum(x.get("own", 0) for x in pool) / len(pool)
                m_adj = sum(x["adj"] for x in pool) / len(pool)
                ax = adv.find_aug(n)
                if not ax:
                    continue
                s = adv.score_aug(ax, prof, t_f, mine, me_f, None, 2)
                rec["augs"].append({"rel": s["total"] - m_tot, "own": s.get("own", 0) - m_own, "adj": s["adj"] - m_adj})
            rec["strength"] = adv.champ_strength(r["c"])
            out.append(rec)
        if gi % 20 == 0:
            print("game", gi, "/", len(tids), "players", len(out), "%.0fs" % (time.time() - t0), flush=True)
        if len(out) >= a.max:
            break
    if a.out:
        json.dump(out, open(a.out, "w"))
    report(out)


def logit_fit(X, y, lam=1.0):
    import numpy as np
    X, y = np.asarray(X, float), np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(30):
        p = 1 / (1 + np.exp(-X @ b))
        H = X.T @ (X * (p * (1 - p))[:, None]) + lam * np.eye(X.shape[1])
        b += np.linalg.solve(H, X.T @ (y - p) - lam * b)
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return b, se


def report(out):
    import numpy as np
    def show(name, xs):
        xs = [(x, y, s) for x, y, s in xs if x is not None]
        if len(xs) < 50:
            print(name, "too few", len(xs))
            return
        x = np.array([v[0] for v in xs]); y = np.array([v[1] for v in xs]); s = np.array([v[2] for v in xs])
        sd = x.std() or 1
        b, se = logit_fit(np.c_[np.ones(len(x)), s, (x - x.mean()) / sd], y)
        hi = y[x >= np.median(x)].mean(); lo = y[x < np.median(x)].mean()
        print("{0:28s} n={1:5d}  每 1 个标准差：{2:+.1f}% 胜率（z={3:+.1f}）  分数高的一半 {4:.1%} vs 低的一半 {5:.1%}".format(
            name, len(x), b[2] * 25, b[2] / se[2], hi, lo))
    mean = lambda v: (sum(v) / len(v)) if v else None
    print("\n== 回测结果（考题玩家 {0} 人）==".format(len(out)))
    show("装备：跟第一名的差距", [(mean([i["gap"] for i in r["items"] if i["gap"] is not None]), r["w"], r["strength"]) for r in out])
    show("装备：在前 5 名的比例", [(mean([1.0 if (i["rank"] is not None and i["rank"] < 5) else 0.0 for i in r["items"]]), r["w"], r["strength"]) for r in out])
    show("增幅：总分（比平均）", [(mean([x["rel"] for x in r["augs"]]), r["w"], r["strength"]) for r in out])
    show("增幅：本局调整部分", [(mean([x["adj"] for x in r["augs"]]), r["w"], r["strength"]) for r in out])
    show("增幅：自建库部分", [(mean([x["own"] for x in r["augs"]]), r["w"], r["strength"]) for r in out])
    pr = [(1.0 if r["path"] == r["route"] else 0.0, r["w"], r["strength"]) for r in out if r.get("path") and len(r.get("route_wr") or {}) >= 2]
    show("路线：走了预估最高的那条", pr)


if __name__ == "__main__":
    main()
