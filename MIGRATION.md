# 换电脑恢复说明

备份日期：2026-11-23；公开版整理日期：2026-11-24。前后端、ETL、模型训练和推理、Hadoop 脚本、启动与打包脚本、测试、数据、已训练模型、论文代码、图和学校模板均已纳入项目。

公开仓库的论文身份字段已清空。原件、完整历史、8 个开发分支和运行状态在私有仓库 `ityongsheng/m09-private-backup`，登录所有者 GitHub 账号即可下载。

## 获取与核验

```bash
git clone https://github.com/ityongsheng/m09.git
cd m09
python3 scripts/verify_checkout.py
```

核验清单为 `evidence/delivery/migration-inventory.json`。清单对其中每个文件记录 SHA-256；新增或主动修改文件后，旧清单不再代表新版本。

## macOS / Linux 开发环境

准备 Git、Python 3.13、Java 17、Maven 3.9，以及联网安装 Python/Maven 依赖的条件。仓库保留的是项目文件，不包含旧电脑的虚拟环境和系统安装软件。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-model.txt -r requirements-thesis.txt
.venv/bin/python -m unittest discover -s tests -v
mvn -q -f backend/pom.xml test
./scripts/start-dev.sh
```

浏览器打开 `http://127.0.0.1:8080/`。程序首次启动会创建 `runtime/m09.sqlite`。模型文件 `artifacts/model/weighted_xgboost.joblib` 已包含在仓库内；无需为首次运行重新训练。

## 保留原运行记录

本次迁移另保存[完整运行状态备份](https://github.com/ityongsheng/m09-private-backup/releases/tag/migration-20261123)，包含通过 SQLite backup API 得到的一致数据库副本、本机模型可执行文件、Hadoop 本地状态、项目工作文件和 Git bundle。下载后先阅读包内清单；数据库恢复时先停止服务，再复制所需的 `runtime/*.sqlite` 到新项目同名位置。

如需继续编辑含身份字段的原始说明书，使用私有备份仓库：

```bash
gh auth login
gh repo clone ityongsheng/m09-private-backup
gh release download migration-20261123 --repo ityongsheng/m09-private-backup --dir m09-backup
```

Hadoop NameNode/DataNode 目录包含旧机器路径和状态，仅作档案保存。新机器按 `hadoop/README.md` 创建新 HDFS，并重新导入仓库数据；不要直接用旧 PID 或旧配置启动。

## 论文复现

学校模板已放在 `thesis/templates/`，不再依赖旧电脑 `/Users/...` 下的外部文件。正式文稿和图已包含在项目内；需要重新构建时执行：

```bash
.venv/bin/python thesis/build_thesis_v1.py
```

重新绘图还需本机中文字体。脚本会查找 macOS 宋体、Windows 宋体/微软雅黑或 Linux Noto CJK；也可设置 `M09_CJK_FONT` 为中文字体文件的完整路径。模板覆盖可使用 `M09_THESIS_TEMPLATE`。

## Windows 模型运行器

私有备份仓库的 GitHub Release `model-exe-6` 保存已经烟测的 Windows x64 模型 EXE。源码构建脚本为 `scripts/build_model_exe.ps1`，CI 为 `.github/workflows/build-model-exe.yml`。此为模型运行器；完整 Windows 应用离线包未制作，也未做新电脑验收。

## 迁移范围

- 当前整合版本保留全部源码；此前各 agent 分支也另行保存，不用旧分支覆盖现有实现。
- 私有备份的 `thesis/archive/m09-thesis-worktree/` 保留原工作树中未提交的早期文稿和模板指纹；公开版仅保留指纹，当前脱敏文稿位于 `thesis/`。
- `evidence/hadoop/run/` 保留原始运行证据。它描述 2026-11-22 的实际运行，不代表新电脑已运行 Hadoop。
- `.venv`、Python 字节码、操作系统缓存、第三方依赖缓存可在新电脑重建，不作为项目源码上传。未把系统级凭据或 Git 登录信息打包。
