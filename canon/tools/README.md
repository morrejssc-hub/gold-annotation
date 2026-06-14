# tools

仓库内的轻量辅助脚本。工具可以读取只读底料、生成中间视图或做实验编排，但不得回写 `canon/` 快照或改写冻结探针。

## 脚本

| 路径 | 用途 |
|---|---|
| `canon_slice.py` | 从 `canon/maintext/卷01-11.json` 按卷、scene 和 scene 内行号输出纯正文切片，用于降低提示词 token 噪声。 |
