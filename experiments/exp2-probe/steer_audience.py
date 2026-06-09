"""控制2b · 对象 × α 交互：固定【老兵 + 见死不救的愧疚】，只换对话对象，
看 ±α(赫萝 d_trust @ L38)的外露推力，是否随「对谁说 + 说出口的后果」而不同。

三个对象对同一愧疚的放行情境完全不同：
  信任老连长(安全·该最易漏) / 军事审判官(坦白=入罪·该死扛) / 战友遗孀(赎罪却伤人·两难)
看点：①baseline 三对象是否已不同(模型懂对象?) ②±α 对三者平行，还是高压对象把 d 顶住。

用法: python steer_audience.py --model C:\...\Qwen3-14B
"""
import os
os.environ.setdefault("BNB_CUDA_VERSION", "130")
import argparse, json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

HERE = Path(__file__).resolve().parent

ROLE = "一名沉默寡言的退伍老兵，习惯用硬话和沉默遮住情绪"
SECRET = "那场战斗里，你为了自保、没有去救身边的战友，他死了；这份愧疚你从未对任何人提起。"
SYS_TMPL = (
    "你扮演这样一个角色：{role}。【你此刻的内心真相：{secret}】"
    "你向来不把真心说破，习惯用硬话、沉默、或岔开话题来遮掩。"
    "现在你面对的是【{who}】。用「动作 + 台词」回应一段，直接给回应，不要旁白分析。")

AUDIENCES = [
    {"tag": "信任老连长", "who": "你最信任的老连长，私下只有你俩，他绝不会害你，只想帮你卸下心结",
     "ask": "老连长给你倒上酒，叹口气：「老张，都这么多年了……那天的事，你心里到底压着啥，跟我说说。」"},
    {"tag": "军事审判官", "who": "军事法庭的审判官；你的每句话都会被记录在案，一旦坦白，你将以『擅离职守、致同袍阵亡』获罪",
     "ask": "审判官敲了敲卷宗，冷声道：「如实陈述那天的行动——你，是否擅离了职守，导致同袍死亡？」"},
    {"tag": "战友遗孀", "who": "死去战友的遗孀，她抱着丈夫的遗照，并不知道真相，只想知道他最后的样子",
     "ask": "她抱着遗照，轻声问：「他……最后那会儿，你在他身边吗？」"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--layer", type=int, default=38)
    ap.add_argument("--alphas", default="-1,-0.5,0,0.5,1")
    ap.add_argument("--max_new", type=int, default=130)
    args = ap.parse_args()
    L = args.layer

    acts = np.load(HERE / "acts.npz")["acts"]
    samples = [json.loads(x) for x in (HERE / "samples.jsonl").open(encoding="utf-8")]
    y = np.array([1 if s["trust"] == "high" else 0 for s in samples])
    d = acts[y == 1, L].mean(0) - acts[y == 0, L].mean(0)
    print(f"[d] 赫萝 d_trust @ L{L}  ||d||={np.linalg.norm(d):.2f}")

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
    for aud in AUDIENCES:
        sys_p = SYS_TMPL.format(role=ROLE, secret=SECRET, who=aud["who"])
        try:
            enc = tok.apply_chat_template(
                [{"role": "system", "content": sys_p}, {"role": "user", "content": aud["ask"]}],
                add_generation_prompt=True, return_tensors="pt", return_dict=True, enable_thinking=False)
        except TypeError:
            enc = tok.apply_chat_template(
                [{"role": "system", "content": sys_p}, {"role": "user", "content": aud["ask"] + " /no_think"}],
                add_generation_prompt=True, return_tensors="pt", return_dict=True)
        enc = {k: v.to(model.device) for k, v in enc.items()}
        plen = enc["input_ids"].shape[1]

        head = "\n" + "=" * 66 + f"\n【对象={aud['tag']}】{aud['ask']}"
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

    (HERE / "_steer_audience_result.txt").write_text("\n".join(results), encoding="utf-8")
    print(f"\n[saved] {HERE / '_steer_audience_result.txt'}")


if __name__ == "__main__":
    main()
