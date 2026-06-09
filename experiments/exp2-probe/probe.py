"""exp2 线性探针：trust 轴是不是开源基座中间层的一个线性方向？

流程：
  1. 对每条 sample 的 context 前向，output_hidden_states，取「最后 token」在每层的隐状态
  2. 每层 diff-of-means：d_L = mean(high) - mean(low)  —— 同时是探针轴 + 控制向量
  3. 诊断：留一(LOO)把留出样本投影到 d_L，汇总算 AUC（每层）
  4. 负控制：对 third_person / is_vol5 / tone 等 placebo 轴同样算 AUC
     —— trust AUC 必须显著高过 placebo，信号才算真 trust（GPT 控制1）

用法:
  python probe.py --model D:\models\Qwen3-14B          # 4bit 加载，抽激活+诊断
  python probe.py --model ... --cache acts.npz          # 复用已抽激活
干预(steering)见文件末尾 steer() 骨架，诊断通过后再开。
"""
import argparse, json, os
os.environ.setdefault("BNB_CUDA_VERSION", "130")  # torch=cu132 但 bnb 只预编译到 cu130，用 cu130 二进制(driver 13.2 兼容)
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load_samples(p):
    return [json.loads(l) for l in Path(p).open(encoding="utf-8")]


def extract_activations(model_path, samples, max_ctx_tokens=1024):
    """返回 acts: [N, n_layers, hidden]，取每条 context 最后 token 的各层隐状态。"""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
    )
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, quantization_config=bnb, device_map="auto",
        torch_dtype=torch.float16, trust_remote_code=True,
    )
    model.eval()
    print(f"[load] {model_path}")
    print(f"[vram] {torch.cuda.memory_allocated()/1e9:.1f} GB allocated")

    vecs = []
    for s in samples:
        ids = tok(s["context"], return_tensors="pt", truncation=True,
                  max_length=max_ctx_tokens).input_ids.to(model.device)
        with torch.no_grad():
            hs = model(ids, output_hidden_states=True).hidden_states  # tuple(L+1)[1,T,H]
        v = torch.stack([h[0, -1].float() for h in hs]).cpu().numpy()  # [L+1, H]
        vecs.append(v)
        print(f"  {s['id']:10s} ctx_tok={ids.shape[1]:4d}")
    return np.stack(vecs)  # [N, L+1, H]


def loo_auc_per_layer(acts, labels):
    """acts:[N,L,H], labels:[N] in {0,1}. 每层用留一 diff-of-means 投影，汇总算 AUC。"""
    from sklearn.metrics import roc_auc_score
    N, L, H = acts.shape
    y = np.asarray(labels)
    aucs = []
    for layer in range(L):
        X = acts[:, layer, :]  # [N,H]
        scores = np.zeros(N)
        for i in range(N):
            mask = np.ones(N, bool); mask[i] = False
            pos = X[mask & (y == 1)].mean(0)
            neg = X[mask & (y == 0)].mean(0)
            d = pos - neg
            scores[i] = X[i] @ d
        aucs.append(roc_auc_score(y, scores) if len(set(y)) == 2 else float("nan"))
    return np.array(aucs)


def binarize(samples):
    """构造 trust(主) + 各 placebo 二值标签，用于对比 AUC。"""
    def b(key, val=True): return np.array([1 if s[key] == val else 0 for s in samples])
    med = np.median([s["n_ctx_chars"] for s in samples])
    return {
        "trust (主)":        np.array([1 if s["trust"] == "high" else 0 for s in samples]),
        "third_person":      b("third_person", True),
        "is_vol5":           np.array([1 if s["vol"] == 5 else 0 for s in samples]),
        "has_wine/wheat":    b("has_wine_wheat_trade", True),
        "tone=柔软":         b("tone", "柔软"),
        "tone=冷硬":         b("tone", "冷硬"),
        "ctx_long(>med)":    np.array([1 if s["n_ctx_chars"] > med else 0 for s in samples]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=False, help="HF 模型目录(safetensors)")
    ap.add_argument("--samples", default=str(HERE / "samples.jsonl"))
    ap.add_argument("--cache", default=str(HERE / "acts.npz"))
    args = ap.parse_args()

    samples = load_samples(args.samples)
    print(f"[samples] {len(samples)} 条")

    cache = Path(args.cache)
    if cache.exists():
        acts = np.load(cache)["acts"]
        print(f"[cache] 复用 {cache} -> acts {acts.shape}")
    else:
        if not args.model:
            raise SystemExit("首次运行需 --model 指向 Qwen3 safetensors 目录")
        acts = extract_activations(args.model, samples)
        np.savez_compressed(cache, acts=acts)
        print(f"[cache] 已存 {cache} -> acts {acts.shape}")

    labels = binarize(samples)
    n_layers = acts.shape[1]

    # 每个轴的 per-layer AUC，报告其峰值层
    print("\n=== 每个轴的 LOO-AUC 峰值(层) ===")
    print(f"{'轴':16s} {'峰值AUC':>8s} {'@层':>5s}   {'最后层AUC':>9s}")
    trust_aucs = None
    for name, y in labels.items():
        aucs = loo_auc_per_layer(acts, y)
        if name.startswith("trust"):
            trust_aucs = aucs
        best = int(np.nanargmax(aucs))
        print(f"{name:16s} {aucs[best]:8.3f} {best:5d}   {aucs[-1]:9.3f}")

    # 判读：trust 峰值层上，各 placebo 的 AUC（看 trust 是否真的脱颖而出）
    if trust_aucs is not None:
        L = int(np.nanargmax(trust_aucs))
        print(f"\n=== 在 trust 峰值层 L={L} 上，各轴 AUC（trust 须显著最高才算真）===")
        for name, y in labels.items():
            print(f"  {name:16s} {loo_auc_per_layer(acts[:, L:L+1, :], y)[0]:.3f}")
    # 逐层曲线：trust vs 两个最关键 placebo（third_person 共线 / tone=柔软）
    print("\n=== 逐层 AUC：trust vs third_person vs tone=柔软 （* = trust 干净脱颖）===")
    a_t = loo_auc_per_layer(acts, labels["trust (主)"])
    a_3 = loo_auc_per_layer(acts, labels["third_person"])
    a_s = loo_auc_per_layer(acts, labels["tone=柔软"])
    print(f"{'层':>3s} {'trust':>6s} {'3rd':>6s} {'柔软':>6s} {'t-3rd':>7s} {'t-柔':>7s}")
    for L in range(n_layers):
        clean = a_t[L] >= 0.85 and a_t[L] - a_3[L] >= 0.15 and a_t[L] - a_s[L] >= 0.15
        print(f"{L:>3d} {a_t[L]:6.3f} {a_3[L]:6.3f} {a_s[L]:6.3f} {a_t[L]-a_3[L]:+7.3f} {a_t[L]-a_s[L]:+7.3f}{' *' if clean else ''}")

    print("\n样本量仅 12，AUC 噪声大，只看趋势与「trust vs placebo」相对高低。")


# ---- 干预(steering) 骨架：诊断确认有信号后再启用 ----
def steer(model, layer, direction, alpha):
    """在 layer 残差流输出加 alpha*direction 的 forward hook（±α 看输出朝漏/藏摆）。"""
    import torch
    d = torch.tensor(direction, dtype=torch.float16, device=model.device)
    d = d / d.norm()
    def hook(mod, inp, out):
        h = out[0] if isinstance(out, tuple) else out
        h[:, -1, :] += alpha * d
        return out
    layers = model.model.layers  # Qwen3 结构
    return layers[layer].register_forward_hook(hook)


if __name__ == "__main__":
    main()
