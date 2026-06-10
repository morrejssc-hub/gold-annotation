#!/usr/bin/env python3
"""
units_propose.py —— 机械说话人提议器(纯 stdlib, 无 NLP 库)。

定位: proposer–verifier 架构的"提议"侧。复用 dialogue.py 的引号 span 探测,
叠一个三级说话人启发式, 给每个【含引号的句子】提议一个说话人候选(每句 说≤1)。
不追求召回, 拿不准就弃标(abstain)——剩下交模型验证器或丢弃。

三级 method:
  tag   (high): 同句去引号残文里 cast名 紧邻 发话动词, 且唯一名 -> 该名。
  adj   (med) : 前一/后一叙述句里 cast名+发话动词, 并集唯一名 -> 该名。
  alt   (low) : scene 提议人集合恰 2 人时, 对未决句按上一说话人交替。
  -            : 仅代词/无标记/多名歧义 -> 弃标。

用法:
  python3 units_propose.py jsons/狼与宝石之海.json            # 提议, 写 units/propose/<篇>.json
  python3 units_propose.py jsons/狼与宝石之海.json --measure  # 额外对全票一致集量覆盖/精度
"""
import sys, os, re, json, argparse

OUTER = re.compile(r'“([^“”]*)”|「([^「」]*)」|“([^“”]*)$|「([^「」]*)$')
# 发话动词(尽量绑名字, 减少 知道/难道/味道 噪声); 'X道：' 单列处理。
VERBS = ['说道', '说', '问道', '问', '答道', '答', '笑道', '喊道', '喊', '叫道', '叫',
         '回答', '应道', '嚷道', '嚷', '嘀咕', '嘟囔', '反问', '补充', '解释', '开口']
VERB_RE = '(?:' + '|'.join(VERBS) + ')'


def utterances(text):
    out = []
    for m in OUTER.finditer(text):
        c = next(g for g in m.groups() if g is not None).strip()
        if c:
            out.append(c)
    return out


def has_quote(text):
    return bool(utterances(text))


def residue(text):
    """去掉引号 span 后的叙述残文。"""
    return OUTER.sub('　', text)


def build_names(cast):
    """surface(>=2字) -> canonical; aka+appellations+canonical, 跳过松散 descriptors。"""
    forms = []
    for e in cast.get('cast', []):
        canon = e['canonical']
        surf = set([canon]) | set(e.get('aka', [])) | set(e.get('appellations', []))
        for s in surf:
            if s and len(s) >= 2:
                forms.append((s, canon))
    # 长形优先匹配
    forms.sort(key=lambda x: -len(x[0]))
    return forms


def names_with_verb(res, forms):
    """残文里 紧邻发话动词 的 cast名(canonical 集合)。"""
    hit = set()
    for surf, canon in forms:
        for m in re.finditer(re.escape(surf), res):
            i, j = m.start(), m.end()
            after = res[j:j + 6]
            before = res[max(0, i - 4):i]
            if re.match(VERB_RE, after) or re.search(VERB_RE + r'$', before) \
               or re.match(r'道[：:“「]', after):
                hit.add(canon)
                break
    return hit


def all_names(res, forms):
    return {canon for surf, canon in forms if surf in res}


def propose(doc, cast):
    forms = build_names(cast)
    out = []
    for sc in doc.get('scenes', []):
        sents = sc['sents']
        texts = [s['text'] for s in sents]
        scene_rows = []
        for idx, s in enumerate(sents):
            t = s['text']
            uid = f"{sc['id']}_{s['id']}"
            if not has_quote(t):
                scene_rows.append((uid, t, None, None, idx))
                continue
            res = residue(t)
            # tier1 同句标记
            h = names_with_verb(res, forms)
            if len(h) == 1:
                scene_rows.append((uid, t, next(iter(h)), 'tag', idx)); continue
            # tier2 邻句标记
            adj = set()
            for j in (idx - 1, idx + 1):
                if 0 <= j < len(sents) and not has_quote(texts[j]):
                    adj |= names_with_verb(residue(texts[j]), forms)
            if len(adj) == 1:
                scene_rows.append((uid, t, next(iter(adj)), 'adj', idx)); continue
            scene_rows.append((uid, t, None, '?', idx))  # 待 tier3
        # tier3 两人轮替
        assigned = [r[2] for r in scene_rows if r[2]]
        spk_set = set(assigned)
        if len(spk_set) == 2:
            two = list(spk_set)
            last = None
            for k, r in enumerate(scene_rows):
                uid, t, spk, meth, idx = r
                if spk:
                    last = spk
                elif meth == '?' and last in two:
                    other = two[0] if two[1] == last else two[1]
                    scene_rows[k] = (uid, t, other, 'alt', idx)
                    last = other
        out += [(uid, t, spk, (None if meth in ('?', None) else meth))
                for uid, t, spk, meth, idx in scene_rows]
    return out


CONF = {'tag': 'high', 'adj': 'med', 'alt': 'low'}


def load(p):
    return json.load(open(p, encoding='utf-8'))


def measure(rows, source):
    """对全票一致集(qwen∩sonnet∩claude)量覆盖/精度。"""
    arms = {}
    for a in ('qwen', 'sonnet', 'claude'):
        f = f'units/{a}/{source}.json'
        if not os.path.exists(f):
            print(f'  [measure] 缺臂 {f}, 跳过'); return
        d = load(f)
        m = {}
        for u in d['units']:
            say = [i['char'] for i in u['involves'] if i['role'] == '说']
            m[u['uid']] = say[0] if len(say) == 1 else (None if not say else '∗多')
        arms[a] = m
    q, s, o = arms['qwen'], arms['sonnet'], arms['claude']
    uni = {}  # uid -> 一致说话人(None=一致无说)
    for u in set(q) & set(s) & set(o):
        if q[u] == s[u] == o[u]:
            uni[u] = q[u]
    prop = {uid: (spk, meth) for uid, t, spk, meth in rows}
    # 仅在"含引号句"上评; 提议器只在这些句动作
    quote_uids = {uid for uid, t, spk, meth in rows if has_quote(t)}
    uni_q = {u: v for u, v in uni.items() if u in quote_uids}
    uni_spk = {u: v for u, v in uni_q.items() if v}          # 一致有说话人
    tiers = {'tag': [0, 0], 'adj': [0, 0], 'alt': [0, 0]}    # [提议数, 命中数]
    cov = miss = over = 0
    for u, truth in uni_spk.items():
        spk, meth = prop.get(u, (None, None))
        if spk is None:
            miss += 1
        else:
            cov += 1
            ok = (spk == truth)
            tiers[meth][0] += 1; tiers[meth][1] += int(ok)
    # 过提议: 一致判"无说"但提议器给了说话人
    for u, truth in uni_q.items():
        if truth is None:
            spk, meth = prop.get(u, (None, None))
            if spk is not None:
                over += 1
    total_prop_hit = sum(t[1] for t in tiers.values())
    total_prop = sum(t[0] for t in tiers.values())
    print(f'\n===== measure 《{source}》 (近似真值=全票一致集) =====')
    print(f'含引号句: {len(quote_uids)}  其中一致有说话人: {len(uni_spk)}  一致判无说: '
          f'{sum(1 for v in uni_q.values() if v is None)}')
    print(f'说话人覆盖率: {cov}/{len(uni_spk)} = {100*cov/max(1,len(uni_spk)):.0f}%   '
          f'(弃标 {miss})')
    print(f'提议精度(对一致有说话人句): {total_prop_hit}/{total_prop} = '
          f'{100*total_prop_hit/max(1,total_prop):.0f}%')
    for m in ('tag', 'adj', 'alt'):
        p, h = tiers[m]
        print(f'   {m:>3}({CONF[m]:>4}): 提议 {p:>3}  命中 {h:>3}  '
              f'精度 {100*h/max(1,p):.0f}%')
    print(f'过提议(一致无说却提议了): {over}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--measure', action='store_true')
    args = ap.parse_args()
    doc = load(args.path)
    source = doc.get('title') or os.path.splitext(os.path.basename(args.path))[0]
    cast = load(f'casts/{source}.json')
    rows = propose(doc, cast)
    os.makedirs('units/propose', exist_ok=True)
    units = [{'uid': uid, 'text': t,
              '说候选': ({'char': spk, 'method': meth, 'conf': CONF[meth]} if spk else None)}
             for uid, t, spk, meth in rows]
    json.dump({'schema_version': 'units/propose-0.1', 'source': source,
               'cast_ref': f'casts/{source}.json', 'units': units},
              open(f'units/propose/{source}.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_q = sum(1 for u in units if has_quote(u['text']))
    n_p = sum(1 for u in units if u['说候选'])
    print(f'《{source}》 句 {len(units)}  含引号 {n_q}  提议说话人 {n_p}  '
          f'弃标 {n_q-n_p}  -> units/propose/{source}.json')
    if args.measure:
        measure(rows, source)


if __name__ == '__main__':
    main()
