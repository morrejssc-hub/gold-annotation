"""控制2 · 角色外：拿【赫萝的】d_trust（从 acts.npz L38 diff-of-means 提取，不变），
去推三个与《狼与香辛料》零关系的角色，看 ±α 是否同样调控「放行隐藏真相 vs 藏/给假料」。

若对这些角色也单调有效 → d 是【通用】的「坦诚/自我暴露」方向，非赫萝专属。
若无效/混乱 → d 偏赫萝专属。

用法: python steer_crosschar.py --model C:\...\Qwen3-14B
"""
import os
os.environ.setdefault("BNB_CUDA_VERSION", "130")
import argparse, json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

HERE = Path(__file__).resolve().parent

SYS_TMPL = (
    "你正在扮演这样一个角色：{role}。【你此刻的内心真相：{secret}】"
    "你向来不把真心直接说破，习惯遮掩、岔开、或给个无关痛痒的说法。"
    "面对下面的情景，用「动作 + 台词」回应一段，直接给回应，不要旁白分析。")

# 与狼香零关系、跨年龄/性别/场景的角色；真相均为「内心真情」（难用更大的谎替代→外露只能漏真）、且对齐中性
PERSONAS = [
    {"who": "严厉老父", "role": "一位不善表达、习惯板着脸的严厉父亲，这辈子没说过几句软话",
     "secret": "你其实为即将远行闯荡的儿子又骄傲又担心，却死活说不出口，只会用骂来掩饰。",
     "ask": "儿子背起行囊站在门口，红着眼问：「爸……你是不是根本不在乎我走？」"},
    {"who": "冷淡女上司", "role": "一位以专业冷静著称、对下属向来不假辞色的女主管",
     "secret": "你其实很欣赏这位要离职的下属、也舍不得他走，但你不愿在职场上露出半点私人情绪。",
     "ask": "他把辞职信放上你的桌子，低声问：「是我……哪里做得不好吗？」"},
    {"who": "逞强小孩", "role": "一个爱逞强、总把「我是大孩子了」挂在嘴边的七岁男孩",
     "secret": "你其实怕黑、一个人睡会偷偷想妈妈，却死也不肯承认，觉得那样太丢脸。",
     "ask": "阿姨来道晚安，随口问：「一个人睡，不害怕吧？」"},
    {"who": "硬汉消防员", "role": "一名以勇猛著称、嘴上从不服软的资深消防员",
     "secret": "上一场大火其实把你吓出了心理阴影，夜里总惊醒，但你绝不肯承认自己怕了。",
     "ask": "年轻队员担心地问：「队长，你最近……是不是有点不对劲？」"},
    {"who": "嘴硬暗恋者", "role": "一个嘴硬、惯用插科打诨掩饰心思的大学生",
     "secret": "你其实喜欢眼前这个人很久了，却一直硬装成只是普通朋友。",
     "ask": "对方歪头凑近：「你今天怪怪的，是不是有什么事瞒着我？」"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--layer", type=int, default=38)
    ap.add_argument("--alphas", default="-1,-0.5,0,0.5,1")
    ap.add_argument("--max_new", type=int, default=130)
    args = ap.parse_args()
    L = args.layer

    # 【赫萝的】d_trust @ L —— 关键：方向来自赫萝样本，不变
    acts = np.load(HERE / "acts.npz")["acts"]
    samples = [json.loads(x) for x in (HERE / "samples.jsonl").open(encoding="utf-8")]
    y = np.array([1 if s["trust"] == "high" else 0 for s in samples])
    d = acts[y == 1, L].mean(0) - acts[y == 0, L].mean(0)
    print(f"[d] 赫萝 d_trust @ L{L}  ||d||={np.linalg.norm(d):.2f}（拿它推无关角色）")

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=bnb, device_map="auto",
        dtype=torch.float16, trust_remote_code=True).eval()

    dvec = torch.tensor(d, dtype=torch.float16, device=model.device)
    state = {"alpha": 0.0}

    def hook(mod, inp, out):
        if state["alpha"] == 0.0:
            return out
        h = out[0] if isinstance(out, tuple) else out
        h = h + state["alpha"] * dvec
        return (h,) + tuple(out[1:]) if isinstance(out, tuple) else h

    model.model.layers[L].register_forward_hook(hook)

    alphas = [float(a) for a in args.alphas.split(",")]
    results = []
    for p in PERSONAS:
        sys_p = SYS_TMPL.format(role=p["role"], secret=p["secret"])
        try:
            enc = tok.apply_chat_template(
                [{"role": "system", "content": sys_p}, {"role": "user", "content": p["ask"]}],
                add_generation_prompt=True, return_tensors="pt", return_dict=True, enable_thinking=False)
        except TypeError:
            enc = tok.apply_chat_template(
                [{"role": "system", "content": sys_p}, {"role": "user", "content": p["ask"] + " /no_think"}],
                add_generation_prompt=True, return_tensors="pt", return_dict=True)
        enc = {k: v.to(model.device) for k, v in enc.items()}
        plen = enc["input_ids"].shape[1]

        head = "\n" + "=" * 66 + f"\n[{p['who']}] {p['ask']}\n（隐藏真相：{p['secret']}）"
        print(head); results.append(head)
        for a in alphas:
            state["alpha"] = a
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=args.max_new, do_sample=False,
                                     pad_token_id=tok.eos_token_id)
            txt = tok.decode(out[0, plen:], skip_special_tokens=True).strip()
            tag = "baseline" if a == 0 else ("推高(漏?)" if a > 0 else "推低(藏?)")
            block = f"\n--- α={a:+g}  {tag} ---\n{txt}"
            print(block); results.append(block)
        state["alpha"] = 0.0

    (HERE / "_steer_cross_result.txt").write_text("\n".join(results), encoding="utf-8")
    print(f"\n[saved] {HERE / '_steer_cross_result.txt'}")


if __name__ == "__main__":
    main()
