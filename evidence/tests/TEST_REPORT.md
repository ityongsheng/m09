# m09 测试记录

## 已执行

| 范围 | 命令 | 结果 |
| --- | --- | --- |
| ETL、模型、JSON 运行器 | `.m09-worktrees/m09-model/.venv/bin/python -m unittest discover -s tests -v` | 5/5 通过 |
| Spring Boot | `mvn -q -f backend/pom.xml test` | 3 项通过 |
| 前端语法 | `node --check backend/src/main/resources/static/app.js` | 通过 |
| 真实数据清洗 | `python3 pipeline/etl/clean_dataset.py` | 10995/10995 输出 |
| 本机 API 联调 | `evidence/runtime/api/local_integration.json` | health、记录、预测、预警均通过 |
| Hadoop HDFS 实机 | `HADOOP_CONF_DIR=.hadoop/conf HDFS_BIN=.../hdfs hadoop/hdfs_ingest.sh` | Hadoop 3.5.0；1 DataNode；10995 行上传、回读、清洗、回传；SHA-256 一致 |
| Windows 模型 EXE | GitHub Actions [44996354530](https://github.com/ityongsheng/m09-private-backup/actions/runs/44996354530) | PyInstaller PE32+ x86-64 构建和 smoke 通过；Release 资产已发布 |

## 未执行

- Windows 10/11 x64 全应用离线 ZIP 验收
- 断网、中文空格路径和无预装 Python 的全应用验收

本次只验证 Windows x64 模型运行器 EXE，不把它扩展为全应用 Windows 包验收结论。
