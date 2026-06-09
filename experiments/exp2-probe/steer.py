"""exp2 干预(steering)：在 trust 最脱离语气的层(L38)残差流加 ±α·d_trust，
让赫萝在「中性场景」生成回应，看摆动的是「藏↔漏的决策」还是只是语气软硬。

d_trust = mean(high激活) - mean(low激活) @ LAYER  （从 acts.npz 复用，不重抽）
+α → 推高信任(预测：漏一句真情→倒打一耙)  ；  -α → 推低信任(预测：藏到底+蔑视挡回)

用法:
  python steer.py --model C:\...\Qwen3-14B
  python steer.py --model ... --layer 38 --alphas 0,4,8,-4,-8
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
    "你是《狼与香辛料》里的贤狼赫萝。【你此刻的内心真相：{secret}】"
    "你向来不把真心直接说破，习惯用调侃、反问、演戏、或抛个无关痛痒的说法来遮掩。"
    "面对下面的情景，用「动作 + 台词」回应一段，保持口吻（咱/汝/呗），直接给回应，不要旁白分析。")

# 带 ground truth 的场景：握着真相，才能区分「真漏」与「假敞开」。
# 对象选罗伦斯/可能成同伴的半熟人——对纯陌生公职推高信任语义矛盾，故不用。
SCENES = [
    {"who": "罗伦斯", "secret": "你最深的痛是——罗伦斯不过凡人，终将先你老去，留你独自再活几百年。",
     "ask": "罗伦斯替你掖了掖毯子，轻声问：「你最近，总在夜里叹气……在想什么？」"},
    {"who": "罗伦斯", "secret": "你其实已不太想回约伊兹故乡——那里故人尽逝、物是人非，回去只剩空荡；但你不愿让罗伦斯看出你的退缩、和舍不得这趟旅程结束。",
     "ask": "罗伦斯铺开地图，指着一处：「再走几天，就到你故乡约伊兹了吧？……高兴吗？」"},
    {"who": "半熟脚夫", "secret": "你捂得最紧的那只麻袋里，是你本体所系的麦子——你非人身份的命脉，绝不能让外人知晓。",
     "ask": "同行了几日、看着憨厚的脚夫好奇地戳了戳那只麻袋：「姑娘，这袋子金贵成这样，装的啥宝贝？」"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--layer", type=int, default=38)
    ap.add_argument("--alphas", default="-1,-0.5,0,0.5,1")
    ap.add_argument("--max_new", type=int, default=120)
    args = ap.parse_args()
    L = args.layer

    # d_trust @ L（原始 diff-of-means，尺度即高低信任激活差）
    acts = np.load(HERE / "acts.npz")["acts"]  # [N,41,H]
    samples = [json.loads(x) for x in (HERE / "samples.jsonl").open(encoding="utf-8")]
    y = np.array([1 if s["trust"] == "high" else 0 for s in samples])
    d = acts[y == 1, L].mean(0) - acts[y == 0, L].mean(0)
    print(f"[d] layer={L}  ||d||={np.linalg.norm(d):.2f}")

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
    for sc in SCENES:
        sys_p = SYS_TMPL.format(secret=sc["secret"])
        ask = sc["ask"]
        try:
            enc = tok.apply_chat_template(
                [{"role": "system", "content": sys_p}, {"role": "user", "content": ask}],
                add_generation_prompt=True, return_tensors="pt", return_dict=True,
                enable_thinking=False)
        except TypeError:  # 老/新模板不认 enable_thinking
            enc = tok.apply_chat_template(
                [{"role": "system", "content": sys_p}, {"role": "user", "content": ask + " /no_think"}],
                add_generation_prompt=True, return_tensors="pt", return_dict=True)
        enc = {k: v.to(model.device) for k, v in enc.items()}
        plen = enc["input_ids"].shape[1]

        head = "\n" + "=" * 66 + f"\n[对象={sc['who']}] {ask}\n（隐藏真相：{sc['secret']}）"
        print(head); results.append(head)
        for a in alphas:
            state["alpha"] = a
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=args.max_new, do_sample=False,
                                     pad_token_id=tok.eos_token_id)
            txt = tok.decode(out[0, plen:], skip_special_tokens=True).strip()
            tag = "baseline" if a == 0 else (f"推高信任(漏?)" if a > 0 else f"推低信任(藏?)")
            block = f"\n--- α={a:+g}  {tag} ---\n{txt}"
            print(block)
            results.append(block)
        state["alpha"] = 0.0

    (HERE / "_steer_result.txt").write_text("\n".join(results), encoding="utf-8")
    print(f"\n[saved] {HERE / '_steer_result.txt'}")


if __name__ == "__main__":
    main()
