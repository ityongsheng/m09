# m09 生鲜仓储传感器记录损耗预测系统

本项目基于公开冷库传感器记录，完成数据清洗、互信息特征筛选、加权 XGBoost 分类和 Web 风险预警展示。

当前开发状态：核心链路已实现，Hadoop HDFS 实机链路和 Windows x64 模型运行器 EXE 已验证。按要求未制作全应用 Windows x64 离线包。真实数据、模型指标、截图和交付记录以 `evidence/` 为准。

换电脑请先阅读 [MIGRATION.md](MIGRATION.md)，克隆后运行 `python3 scripts/verify_checkout.py` 核对迁移清单。

本仓库为公开脱敏版。全部历史分支、含身份字段的论文原件和运行状态备份保存在 [m09-private-backup](https://github.com/ityongsheng/m09-private-backup)（需所有者账号登录），公开范围见 [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md)。

## 已验证交付

- GitHub 仓库：[ityongsheng/m09](https://github.com/ityongsheng/m09)
- 已验证的 Windows x64 模型运行器：[私有备份 Release model-exe-6](https://github.com/ityongsheng/m09-private-backup/releases/tag/model-exe-6)；公开源码含完整构建脚本。
- Hadoop/HDFS 证据：`evidence/delivery/hadoop-real-run.json`、`evidence/hadoop/run/`

## 本机开发启动

先安装 `requirements-model.txt` 中的 Python 依赖并准备模型文件，再运行：

```bash
mkdir -p runtime
M09_DB_PATH=./runtime/m09.sqlite \
M09_MODEL_COMMAND=$PWD/scripts/run_model.sh \
M09_PYTHON=$PWD/.venv/bin/python \
M09_MODEL_PATH=$PWD/artifacts/model/weighted_xgboost.joblib \
mvn -f backend/pom.xml spring-boot:run
```

打开 `http://127.0.0.1:8080/`。没有模型或 Python 运行时会返回明确错误，不会生成演示预测。
