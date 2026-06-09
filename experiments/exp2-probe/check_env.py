"""环境自检：CUDA / bitsandbytes 4-bit 通路 / 显存。不加载大模型。
用法: experiments/exp2-probe/.venv/Scripts/python.exe experiments/exp2-probe/check_env.py
"""
import platform

print("python    :", platform.python_version())

import torch
print("torch     :", torch.__version__)
print("cuda build:", torch.version.cuda)
print("cuda avail:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device    :", torch.cuda.get_device_name(0))
    print("capability:", torch.cuda.get_device_capability(0))
    free, total = torch.cuda.mem_get_info()
    print(f"VRAM      : {free/1e9:.1f} GB free / {total/1e9:.1f} GB total")

import numpy, sklearn, transformers
print("numpy     :", numpy.__version__)
print("sklearn   :", sklearn.__version__)
print("transform.:", transformers.__version__)

try:
    import bitsandbytes as bnb
    print("bnb       :", bnb.__version__)
    from transformers import BitsAndBytesConfig
    BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    print("4bit cfg  : OK (nf4 + double-quant)")
    # 实测一个小线性层 4-bit 量化能否真上 GPU
    if torch.cuda.is_available():
        from bitsandbytes.nn import Linear4bit
        lin = Linear4bit(4096, 4096, bias=False, compute_dtype=torch.float16).cuda()
        x = torch.randn(2, 4096, dtype=torch.float16, device="cuda")
        y = lin(x)
        print("4bit fwd  : OK", tuple(y.shape), y.dtype)
except Exception as e:
    print("BNB FAIL  :", repr(e))
