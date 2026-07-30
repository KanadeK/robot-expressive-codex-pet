# RobotExpressive Codex Pet

这是一个基于 three.js 官方仓库中真实存在、采用 CC0 1.0 授权的
[RobotExpressive][model-source] 角色制作的完整 Codex v2 桌面宠物。

它不是只有界面的空壳，也不是一张精灵图：仓库包含离线 3D 动画渲染器、
严格校验器、确定性打包器、动图预览、事务式安装与回滚、诊断 CLI、测试、
CI、GitHub Pages 和 Release 自动化。

[English](README.md) ·
[在线动画实验室](https://kanadek.github.io/robot-expressive-codex-pet/) ·
[下载最新 Release](https://github.com/KanadeK/robot-expressive-codex-pet/releases/latest)

![RobotExpressive 全部动作状态](media/contact-sheet.png)

## 真实功能

- `1536x2288` RGBA/WebP Codex v2 图集，含 9 行语义动作和 16 个顺时针观察方向；
- 73 个有效姿态来自模型原生骨骼动画，包括 `Idle`、`Running`、`Wave`、
  `Jump`、`Death`、`Sitting`、`Punch`、`ThumbsUp`；
- Three.js + Playwright 离线渲染，不需要 API Key，也不会把模型上传到云端；
- 检查尺寸、透明度、必需/空白格、边缘裁切、隐藏 RGB、清单路径和 SHA-256；
- 固定 ZIP 元数据，隔时重复打包仍可得到字节一致的 `.codex-pet.zip`；
- 安全解压、替换前备份、失败自动回滚、可恢复卸载和安装后 doctor；
- 真实图集驱动的 GIF、总览图和网页交互实验室；
- 单元测试、恶意 ZIP 测试、覆盖率门禁、CI、Pages、Release 和修复手册。

RobotExpressive 不是虚构的仿制角色。上游 README 署名模型作者 Tomás Laulhé
和修改者 Don McCurdy，并使用 CC0 1.0。本仓库固定了 three.js 的准确提交和
GLB 文件 SHA-256。

## 安装

使用已生成的宠物只需要 Python 3.11 以上：

```bash
python -m pip install .
robot-pet validate pet
robot-pet install pet
robot-pet doctor
```

默认安装到 `${CODEX_HOME:-$HOME/.codex}/pets/robot-expressive`。若已有同名
宠物，会先移动到 `~/.codex/pet-backups`；替换失败会自动回滚。重启 Codex
后选择 **RobotExpressive / 表情机器人**。

不安装 Python 包也可从仓库直接安装：

```bash
python scripts/install.py --source pet
```

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Python python
```

可恢复卸载：

```bash
robot-pet uninstall
```

卸载命令会输出备份位置，而不是直接永久删除宠物。

## 验收

```bash
python -m pip install -e ".[dev]"
robot-pet validate pet --json
coverage run -m unittest discover -s tests -v
coverage report
ruff check .
mypy src scripts
python scripts/build_release.py --json
python scripts/build_site.py --json
pnpm run test:site
```

预期：

- 校验结果为 `"ok": true`，格式为 `1536x2288`、RGBA、v2、零错误；
- 全部测试通过，分支覆盖率不少于 85%；
- `dist/` 生成宠物 ZIP、独立清单和图集、`SHA256SUMS`、
  `release-manifest.json`；
- `media/` 生成每个状态的 GIF 和总览图；
- `site/` 使用已校验的真实图集，而不是模拟资源。
- 浏览器 E2E 在桌面、移动端和减少动态效果模式全部通过。

提交后再从干净工作区执行：

```bash
python scripts/release_check.py --json --strict
```

完整验收命令、预期结果和逐类故障修复方法见
[docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)。

## 从原始 3D 角色重新渲染

需要 Node.js 22+、pnpm、Python 3.11+，以及 Chrome、Edge 或 Playwright
Chromium：

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm run render:check
pnpm run render
python scripts/finalize_atlas.py \
  --input tmp/robot-atlas.png \
  --render-report tmp/robot-render-report.json
robot-pet validate pet --json
```

渲染器只启动临时本机回环服务器，读取本地固定版本模块和 GLB，完成后自动
关闭浏览器。源模型 SHA-256：

```text
047f5e5fb3bb6d378bd1df16ca6137f2a596c99b3a1b5690b4020c05aaf6f319
```

动作映射、固定输入和跨显卡可复现边界见
[artwork/RENDERING.md](artwork/RENDERING.md)。

## 许可证与来源

- [调研与去重记录](docs/RESEARCH.md)
- [架构](docs/ARCHITECTURE.md)
- [资产来源机器可读记录](artwork/PROVENANCE.json)
- [资产许可证](ASSET_LICENSE.md)
- [第三方声明](NOTICE.md)

代码采用 MIT。上游模型及本项目渲染的视觉资产采用 CC0 1.0。three.js 保留
其 MIT 许可证。本项目是独立社区项目，不代表 three.js 作者或 OpenAI 官方。

[model-source]: https://github.com/mrdoob/three.js/tree/eba30de865cfbf31ac736f792defd9a60ff28d57/examples/models/gltf/RobotExpressive
