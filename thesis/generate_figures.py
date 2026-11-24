from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json, math, os

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "thesis" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    os.environ.get("M09_CJK_FONT", ""),
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

def font(size=26, bold=False):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size, index=0)
            except Exception:
                pass
    raise RuntimeError("未找到中文字体，请将 M09_CJK_FONT 设为本机中文 .ttf/.ttc 字体文件路径")

REG = font(24)
SMALL = font(20)
TITLE = font(32)
BOLD = font(24)

def canvas(title, w=1500, h=850):
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.text((45, 25), title, fill="black", font=TITLE)
    d.line((45, 82, w-45, 82), fill="black", width=2)
    return im, d

def box(d, xy, text, fill="#f3f3f3", outline="black", f=REG, radius=10, width=2):
    x1,y1,x2,y2 = xy
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    lines = text.split("\n")
    heights = [d.textbbox((0,0), line, font=f)[3] for line in lines]
    total = sum(heights) + (len(lines)-1)*6
    y = (y1+y2-total)//2
    for line, hh in zip(lines, heights):
        bb = d.textbbox((0,0), line, font=f)
        x = (x1+x2-(bb[2]-bb[0]))//2
        d.text((x,y), line, fill="black", font=f)
        y += hh+6

def arrow(d, a, b, width=3):
    d.line((*a,*b), fill="black", width=width)
    ang = math.atan2(b[1]-a[1], b[0]-a[0])
    L = 14
    p1 = (b[0]-L*math.cos(ang-math.pi/6), b[1]-L*math.sin(ang-math.pi/6))
    p2 = (b[0]-L*math.cos(ang+math.pi/6), b[1]-L*math.sin(ang+math.pi/6))
    d.polygon([b,p1,p2], fill="black")

def save(im, name):
    im.save(OUT/name, "PNG")

def fig_arch():
    im,d=canvas("系统总体架构")
    xs=[70,370,670,970,1270]
    labels=["数据层\nDataset.csv\n清洗报告 / Schema", "离线处理层\nETL + HDFS\nSHA-256 校验", "算法层\n互信息特征工程\n加权 XGBoost", "服务层\nSpring Boot\nSQLite + REST", "展示层\nWeb 控制台\n记录 / 预测 / 预警"]
    for x,l in zip(xs,labels): box(d,(x,260,x+190,480),l)
    for x in xs[:-1]: arrow(d,(x+190,370),(x+300,370))
    d.text((610,650),"数据流：原始记录 → 清洗 → 特征与模型 → 持久化接口 → 风险提示",fill="black",font=REG)
    save(im,"fig2_1_architecture.png")

def fig_flow():
    im,d=canvas("业务流程与模块关系")
    steps=["管理人员打开控制台","读取记录与实验指标","提交水果及传感器值","模型返回标签和概率","写入预测记录","Bad 或概率≥0.5\n生成 HIGH 预警"]
    y=180
    for i,s in enumerate(steps):
        x=80+i*235
        box(d,(x,y,x+180,y+170),s,fill="#f8f8f8")
        if i<len(steps)-1: arrow(d,(x+180,y+85),(x+225,y+85))
    box(d,(430,500,1070,680),"异常分支：模型文件缺失、输入格式错误或接口不可用时\n返回明确错误，不生成假预测",fill="#eeeeee")
    save(im,"fig2_2_flow.png")

def fig_er():
    im,d=canvas("SQLite 核心实体关系")
    box(d,(70,200,390,570),"sensor_record\nPK id\nfruit\ntemp / humid\nlight / co2\nsource / created_at")
    box(d,(560,150,900,390),"prediction_record\nPK id\nFK sensor_record_id\nlabel / risk_probability\nmodel_version")
    box(d,(1060,150,1410,390),"alert_record\nPK id\nFK prediction_id\nalert_level\nalert_message")
    box(d,(560,500,900,730),"experiment_metric\nPK id\nmodel_name\naccuracy / recall / F1\nroc_auc / mse / mae / r2")
    arrow(d,(390,300),(560,270)); arrow(d,(900,270),(1060,270)); arrow(d,(730,390),(730,500))
    d.text((415,235),"1 : N",fill="black",font=SMALL); d.text((920,235),"1 : N",fill="black",font=SMALL)
    save(im,"fig2_3_er.png")

def fig_usecase():
    """Black-and-white use-case view for the real management role."""
    im,d=canvas("管理人员用例图")
    # System boundary.
    d.rounded_rectangle((380,130,1420,745),radius=18,outline="black",width=3,fill="white")
    d.text((760,150),"冷库传感器损耗预警系统",fill="black",font=BOLD)
    # Simple editable-style actor symbol.
    d.ellipse((100,300,155,355),outline="black",width=3)
    d.line((127,355,127,490),fill="black",width=3)
    d.line((127,385,70,435),fill="black",width=3); d.line((127,385,184,435),fill="black",width=3)
    d.line((127,490,78,565),fill="black",width=3); d.line((127,490,176,565),fill="black",width=3)
    d.text((76,590),"管理人员",fill="black",font=REG)
    cases=[("浏览传感器记录",470,240),("提交风险预测",850,240),("查看预警记录",470,430),("查看模型指标",850,430),("检查接口状态",660,610)]
    for text,x,y in cases:
        d.ellipse((x,y,x+270,y+82),outline="black",width=3,fill="white")
        bb=d.textbbox((0,0),text,font=SMALL); d.text((x+(270-(bb[2]-bb[0]))//2,y+26),text,fill="black",font=SMALL)
        arrow(d,(184,435 if y<500 else 490),(x,y+41),width=2)
    d.text((445,775),"角色与功能覆盖：记录浏览、预测提交、预警追踪、指标查看和健康检查",fill="black",font=SMALL)
    save(im,"fig2_4_usecase.png")

def fig_modules():
    im,d=canvas("系统功能模块图")
    box(d,(80,290,310,500),"数据记录模块\n新增 / 查询\n字段校验",fill="white")
    box(d,(430,180,660,390),"模型预测模块\nJSON 输入\n标签 / 概率",fill="white")
    box(d,(430,490,660,700),"预警模块\nHIGH 状态\n消息记录",fill="white")
    box(d,(810,290,1040,500),"实验指标模块\n基线 / 加权\n分类与辅助指标",fill="white")
    box(d,(1190,290,1420,500),"控制台模块\n总览 / 记录\n预测 / 预警 / 指标",fill="white")
    arrow(d,(310,395),(430,285)); arrow(d,(310,395),(430,595)); arrow(d,(660,285),(810,395)); arrow(d,(660,595),(810,395)); arrow(d,(1040,395),(1190,395))
    d.text((420,760),"模块边界与后端接口、SQLite 实体及实际 Web 标签保持一致",fill="black",font=SMALL)
    save(im,"fig2_5_modules.png")

def fig_etl():
    im,d=canvas("ETL 与 HDFS 实测链路")
    items=["Dataset.csv\n10,995 行", "字段校验\n数值范围 / 标签", "cleaned_dataset.csv\n10,995 行", "HDFS\nraw / processed", "下载回读\nSHA-256 一致"]
    for i,t in enumerate(items):
        x=70+i*285; box(d,(x,260,x+220,470),t,fill="#f6f6f6")
        if i<len(items)-1: arrow(d,(x+220,365),(x+275,365))
    d.text((405,610),"Hadoop 3.5.0 · Java 17 · 单节点伪分布式 · DataNode=1",fill="black",font=REG)
    save(im,"fig3_1_etl_hdfs.png")

def fig_distribution():
    im,d=canvas("标签分布与数据集范围")
    vals=[5667,5328]; labels=["Good", "Bad"]; colors=["#777777","#222222"]
    maxv=max(vals); base=650
    for i,(v,l,c) in enumerate(zip(vals,labels,colors)):
        x=300+i*450; height=int(v/maxv*390)
        d.rectangle((x,base-height,x+190,base),fill=c,outline="black")
        d.text((x+55,base-height-45),str(v),fill="black",font=BOLD)
        d.text((x+57,base+20),l,fill="black",font=REG)
    d.text((380,740),"总记录 10,995；数据为静态传感器记录，不含时间戳",fill="black",font=REG)
    save(im,"fig3_2_distribution.png")

def fig_mi():
    im,d=canvas("训练集互信息得分与加权系数")
    names=["light","humid","temp","co2","fruit=Tomato"]
    mi=[0.3359,0.2063,0.1815,0.1374,0.00225]
    wt=[1.945,1.195,1.051,0.796,0.013]
    maxv=max(mi); base=690
    for i,(n,v,w) in enumerate(zip(names,mi,wt)):
        y=150+i*100; d.text((70,y+12),n,fill="black",font=SMALL)
        d.rectangle((300,y,300+int(v/maxv*700),y+45),fill="#444444",outline="black")
        d.text((1030,y+8),f"MI={v:.4f}  权重={w:.3f}",fill="black",font=SMALL)
    d.text((70,705),"筛选阈值为训练集互信息中位数；测试集未参与权重计算",fill="black",font=REG)
    save(im,"fig3_3_mi_weights.png")

def fig_metrics():
    im,d=canvas("基线与加权模型测试集指标")
    names=["Accuracy","Precision","Recall","F1","ROC-AUC"]
    base=[.999090,.999062,.999062,.999062,.999997]
    weighted=[.998636,.997194,1,.998595,.999998]
    for i,n in enumerate(names):
        y=145+i*100; d.text((70,y+18),n,fill="black",font=SMALL)
        d.rectangle((250,y,250+int(base[i]*800),y+28),fill="#999999",outline="black")
        d.rectangle((250,y+35,250+int(weighted[i]*800),y+63),fill="#222222",outline="black")
        d.text((1080,y+5),f"基线 {base[i]:.6f}",fill="black",font=SMALL)
        d.text((1080,y+40),f"加权 {weighted[i]:.6f}",fill="black",font=SMALL)
    d.text((250,685),"灰色：原始 XGBoost　黑色：互信息加权 XGBoost",fill="black",font=REG)
    save(im,"fig3_4_metrics.png")

def fig_confusion():
    im,d=canvas("加权 XGBoost 测试集混淆矩阵")
    evidence = ROOT / "evidence" / "models" / "confusion_matrix.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    cells = payload["matrix"]
    x0,y0=430,200; cw,ch=280,180
    d.text((515,135),"预测 Good",fill="black",font=REG); d.text((800,135),"预测 Bad",fill="black",font=REG)
    d.text((150,270),"实际 Good",fill="black",font=REG); d.text((150,450),"实际 Bad",fill="black",font=REG)
    for r in range(2):
        for c in range(2):
            x=x0+c*cw; y=y0+r*ch
            d.rectangle((x,y,x+cw,y+ch),fill="#eeeeee" if r==c else "#fafafa",outline="black",width=2)
            bb=d.textbbox((0,0),str(cells[r][c]),font=TITLE); d.text((x+(cw-(bb[2]-bb[0]))//2,y+65),str(cells[r][c]),fill="black",font=TITLE)
    d.text((380,640),"来源：固定随机种子 20261122 的 2,199 条测试记录逐样本预测结果；Good=0，Bad=1。",fill="black",font=SMALL)
    save(im,"fig3_5_confusion.png")

def fig_api():
    im,d=canvas("本机 API 联调证据（后端功能）")
    rows=[("GET /api/health","200","status=ok"),("GET /","200","静态 Web 页面返回"),("POST /api/records","200","记录写入 SQLite"),("POST /api/predict","200","Bad / 0.60024434 / HIGH"),("GET /api/predictions","200","预测历史可读"),("GET /api/alerts","200","高风险预警可读")]
    y=135
    for path,status,result in rows:
        d.rectangle((80,y,1420,y+78),fill="#f7f7f7",outline="black")
        d.text((105,y+22),path,fill="black",font=SMALL); d.text((760,y+22),status,fill="black",font=SMALL); d.text((900,y+22),result,fill="black",font=SMALL)
        y+=95
    d.text((80,735),"环境：macOS · Java 17 · Spring Boot 3.3.5 · SQLite · model_runner.py",fill="black",font=SMALL)
    save(im,"fig4_1_api_evidence.png")

def fig_hdfs():
    im,d=canvas("HDFS 实机运行证据")
    rows=[("Hadoop","3.5.0"),("Java","17.0.21.1"),("模式","单节点伪分布式 HDFS"),("NameNode","hdfs://localhost:9000"),("DataNode","1 个在线"),("原始行数","10,995"),("清洗行数","10,995"),("回读 SHA-256","与原始文件一致")]
    y=125
    for k,v in rows:
        d.rectangle((180,y,1320,y+62),fill="#f7f7f7",outline="black")
        d.text((220,y+17),k,fill="black",font=SMALL); d.text((700,y+17),v,fill="black",font=SMALL)
        y+=73
    save(im,"fig5_1_hdfs_evidence.png")

def fig_exe():
    im,d=canvas("Windows x64 模型运行器 EXE 烟测")
    rows=[("平台","Windows x64"),("文件类型","PE32+ executable, x86-64"),("输入","Tomato / 30°C / 95% / 10 Lux / 900 ppm"),("输出标签","Bad"),("风险概率","0.67811358"),("模型版本","weighted-xgboost-mi-v1"),("发布资产","m09-model-runner-windows.zip")]
    y=145
    for k,v in rows:
        d.rectangle((100,y,1400,y+72),fill="#f7f7f7",outline="black")
        d.text((145,y+21),k,fill="black",font=SMALL); d.text((550,y+21),v,fill="black",font=SMALL)
        y+=88
    d.text((100,770),"范围说明：只验证模型运行器 EXE，未制作全应用 Windows x64 离线包。",fill="black",font=SMALL)
    save(im,"fig5_2_exe_evidence.png")

for fn in [fig_arch,fig_flow,fig_er,fig_usecase,fig_modules,fig_etl,fig_distribution,fig_mi,fig_metrics,fig_confusion,fig_api,fig_hdfs,fig_exe]:
    fn()
print(f"generated {len(list(OUT.glob('*.png')))} figures in {OUT}")
