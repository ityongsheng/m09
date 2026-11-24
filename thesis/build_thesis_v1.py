from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from copy import deepcopy

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Cm, Pt, Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(os.environ.get("M09_THESIS_TEMPLATE", str(ROOT / "thesis" / "templates" / "河北工业职业技术大学_模板原件.docx")))
OUT = ROOT / "thesis" / "毕业设计说明书_m09_v1.0.docx"
FIG = ROOT / "thesis" / "figures"

TITLE = "基于 Hadoop 与 XGBoost 的生鲜仓储损耗预测系统的设计与实现"

def set_run_font(run, name="Songti SC", size=11, bold=None, italic=None):
    # Keep macOS's installed Songti/Heiti face for Chinese rendering while
    # declaring the Latin face explicitly as Times New Roman, which is the
    # handbook's Word-side requirement for mixed Chinese/Latin text.
    latin = "Times New Roman" if name in {"Songti SC", "Heiti SC"} else name
    east_asia = {"Songti SC": "宋体", "Heiti SC": "黑体"}.get(name, name)
    run.font.name = latin
    run._element.rPr.rFonts.set(qn("w:ascii"), latin)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), latin)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic

def set_paragraph_text(p, text, keep_first_format=True):
    # Template TOC paragraphs contain field codes and hyperlinks. Remove all
    # run-level children before writing static text so cached field results do
    # not remain beside the new heading.
    clear_paragraph(p)
    p.add_run(text)

def add_cited_text(p, text):
    """Write body text and make [n] citation markers superscript ASCII."""
    parts = re.split(r"(\[\d+\])", text)
    for part in parts:
        if not part:
            continue
        r = p.add_run(part)
        if re.fullmatch(r"\[\d+\]", part):
            r.font.superscript = True
            set_run_font(r, "Times New Roman", 9)
        else:
            set_run_font(r, "Songti SC", 12)

def style_body(p, indent=True):
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(20)
    if indent:
        pf.first_line_indent = Cm(0.74)
    # Some template front-matter paragraphs explicitly disable wrapping.
    # Keep the paragraph style but allow a real abstract/declaration to flow.
    ww = p._p.pPr.find(qn("w:wordWrap")) if p._p.pPr is not None else None
    if ww is None and p._p.pPr is not None:
        ww = OxmlElement("w:wordWrap")
        p._p.pPr.append(ww)
    if ww is not None:
        ww.set(qn("w:val"), "1")
    return p

def add_p(target, text, style="Normal", indent=True, align=None):
    p = target.insert_paragraph_before()
    p.style = style
    if text:
        add_cited_text(p, text)
    if style == "Normal":
        style_body(p, indent=indent)
    if align is not None:
        p.alignment = align
    return p

def add_heading(target, text, level=1):
    style = f"Heading {level}"
    p = target.insert_paragraph_before()
    p.style = style
    set_paragraph_text(p, text)
    for r in p.runs:
        set_run_font(r, "Heiti SC", 15 if level == 1 else (14 if level == 2 else 13), bold=True)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(20)
    return p

def add_caption(target, text, figure=True):
    style = "Heading 6" if figure else "Heading 5"
    p = target.insert_paragraph_before()
    p.style = style
    set_paragraph_text(p, text)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.space_before = Pt(6)
    pf.space_after = Pt(12)
    for r in p.runs:
        set_run_font(r, "Heiti SC", 11)
    return p

def add_image(target, path, caption):
    p = target.insert_paragraph_before()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run()
    # The school template uses an 18 pt automatic line box.  LibreOffice and
    # Word then clip an inline picture to that box, leaving only the caption
    # visible in the rendered document.  Make the line box at least as tall as
    # the actual picture so the image remains visible in both editors.
    picture = r.add_picture(str(path), width=Cm(15.3))
    height_pt = picture.height / 12700.0
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    p.paragraph_format.line_spacing = Pt(height_pt + 4)
    add_caption(target, caption, figure=True)

def add_figure_context(target, context, path, caption):
    """Add the required textual lead-in before a numbered figure."""
    add_p(target, context)
    add_image(target, path, caption)

def set_cell_text(cell, text, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1
    r = p.add_run(str(text))
    set_run_font(r, "Songti SC", 10.5, bold=bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def set_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = tblPr.first_child_found_in("w:tblBorders")
    if borders is not None:
        tblPr.remove(borders)
    borders = OxmlElement("w:tblBorders")
    for edge, sz in (("top", "12"), ("bottom", "12"), ("insideH", "0"), ("left", "0"), ("right", "0"), ("insideV", "0")):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single" if sz != "0" else "nil")
        el.set(qn("w:sz"), sz)
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tblPr.append(borders)
    # The header separator is the only internal horizontal rule in a normal
    # three-line table.  Do not add vertical or body-row grid lines.
    first_row = table.rows[0]
    for cell in first_row.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        cb = tcPr.first_child_found_in("w:tcBorders")
        if cb is None:
            cb = OxmlElement("w:tcBorders")
            tcPr.append(cb)
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:space"), "0")
        bottom.set(qn("w:color"), "000000")
        cb.append(bottom)

def add_table(target, headers, rows, caption):
    table = target.part.document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i,h in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], h, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i,v in enumerate(row):
            set_cell_text(cells[i], v)
    set_table_borders(table)
    # Keep each row together and repeat the header when a long test table
    # continues onto the next page.
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        trPr.append(cant_split)
    header_pr = table.rows[0]._tr.get_or_add_trPr()
    header_repeat = OxmlElement("w:tblHeader")
    header_repeat.set(qn("w:val"), "true")
    header_pr.append(header_repeat)
    # Move the table just before the section break target.
    target._p.addprevious(table._tbl)
    add_caption(target, caption, figure=False)
    return table

def add_page_break_before(target):
    p = target.insert_paragraph_before()
    p.add_run().add_break(WD_BREAK.PAGE)
    return p

def clear_paragraph(p):
    for child in list(p._p):
        if child.tag != qn("w:pPr"):
            p._p.remove(child)

def enable_update_fields(doc):
    settings = doc.settings.element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")

def replace_toc(doc):
    entries = [
        ("第1章　绪论", 1), ("1.1　研究背景与问题提出", 1), ("1.2　研究内容与技术路线", 2), ("1.3　论文组织结构", 2),
        ("第2章　需求分析与总体设计", 3), ("2.1　业务需求与可行性", 3), ("2.2　功能与非功能需求", 4), ("2.3　系统总体架构", 5), ("2.4　数据库与接口设计", 6),
        ("第3章　数据处理与模型设计", 9), ("3.1　数据来源与字段定义", 9), ("3.2　数据清洗与 HDFS 链路", 10), ("3.3　互信息特征加权", 12), ("3.4　模型训练与评价指标", 13),
        ("第4章　系统详细设计与实现", 16), ("4.1　后端服务实现", 16), ("4.2　SQLite 持久化实现", 17), ("4.3　Web 控制台实现", 18),
        ("第5章　系统测试与结果分析", 24), ("5.1　测试环境与测试用例", 24), ("5.2　模型实验结果", 25), ("5.3　系统联调与交付验证", 25), ("5.4　限制与风险", 27),
        ("结　　论", 28), ("参考文献", 29), ("致　　谢", 31), ("附录A　复现实验与接口样例", 32),
    ]
    ps = doc.paragraphs
    for idx, (text, page) in enumerate(entries):
        pi = 47 + idx
        if pi >= 100:
            break
        p = ps[pi]
        p.style = "toc 1" if text.startswith("第") or text in {"结　　论","参考文献","致　　谢"} else ("toc 2" if text[:1].isdigit() and text.count(".") == 1 else "toc 3")
        set_paragraph_text(p, f"{text}\t{page}")
        p.paragraph_format.space_after = Pt(5)
        for r in p.runs:
            set_run_font(r, "Songti SC", 11)
    for pi in range(47+len(entries), 100):
        set_paragraph_text(ps[pi], "")
    # Preserve a real TOC field for Word/LibreOffice refresh. The visible
    # entries above are cached values for deterministic local rendering;
    # this hidden field lets the target editor rebuild the same 1–3 levels
    # after a page break or heading change.
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), ' TOC \\o "1-3" \\h \\z \\u ')
    # Leave the field result empty.  LibreOffice otherwise exposes a cached
    # literal ``TOC`` marker in the rendered PDF; Word can still refresh the
    # field because the instruction remains in the document XML.
    ps[47]._p.append(fld)

def fill_front_matter(doc):
    # Cover tables: keep the school logo, borders and template layout.
    if len(doc.tables) >= 2:
        cover_title = doc.tables[0].rows[1].cells[0]
        cover_title.text = TITLE
        for p in cover_title.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                set_run_font(r, "Heiti SC", 16)
        t = doc.tables[1]
        values = {0: "", 1: "", 2: "人工智能学院", 3: "大数据工程技术", 4: "", 5: "", 6: ""}
        for row_idx, value in values.items():
            set_cell_text(t.rows[row_idx].cells[1], value)
        set_cell_text(t.rows[4].cells[3], "")
        set_cell_text(t.rows[5].cells[3], "")
    # Replace declaration and authorization placeholders without inventing signatures/dates.
    ps = doc.paragraphs
    # The template places the date paragraph at a section boundary; leaving it
    # empty avoids creating a date-only page while preserving a blank date slot.
    set_paragraph_text(ps[9], "")
    set_paragraph_text(ps[13], f"本人所提交的毕业设计《{TITLE}》，是在导师的指导下，独立进行研究工作所取得的原创性成果。除文中已经注明引用的内容外，本毕业设计不包含任何其他个人或集体已经发表或撰写过的研究成果。对本文的研究做出重要贡献的个人和集体，均已在文中标明。")
    style_body(ps[13], indent=True)
    for r in ps[13].runs: set_run_font(r, "Songti SC", 12)
    set_paragraph_text(ps[17], "作者签名：　　　　　　　　　指导教师签名：")
    set_paragraph_text(ps[18], "年　　月　　日　　　　　　　　　年　　月　　日")
    set_paragraph_text(ps[31], "作者签名：　　　　　　　　　指导教师签名：")
    set_paragraph_text(ps[32], "年　　月　　日　　　　　　　　　年　　月　　日")
    set_paragraph_text(ps[35], "针对冷库环境记录分散、人工巡检难以及时识别高风险记录的问题，本文设计并实现了一套生鲜仓储传感器记录损耗风险预测原型系统。系统采用 Mendeley Data 公开冷库传感器记录数据，完成字段统一、缺失值与数值范围检查、Good/Bad 标签标准化，并通过 Hadoop HDFS 完成原始文件上传、清洗结果回传与 SHA-256 一致性核验。在模型层，使用训练集互信息进行特征筛选和缩放，比较原始 XGBoost 与互信息加权 XGBoost 二分类模型；在应用层，使用 Spring Boot、SQLite 和静态 Web 页面实现记录浏览、风险预测、预警保存和实验指标展示。数据集包含 10,995 条记录，不含时间戳，因此本文将研究对象限定为传感器记录分类，不将结果表述为严格的时间序列预测。固定随机种子实验中，基线模型 Accuracy 为 0.999090，加权模型 Recall 为 1.000000、ROC-AUC 为 0.999998。原型能够形成从数据处理、模型推理到 Web 预警的可追溯链路，但加权策略没有在所有指标上超过基线，结论仍受数据来源和静态标签限制。")
    style_body(ps[35], indent=True)
    ps[35].paragraph_format.space_before = Pt(0)
    ps[35].paragraph_format.space_after = Pt(0)
    for r in ps[35].runs: set_run_font(r, "Songti SC", 12)
    set_paragraph_text(ps[36], "关键词：冷库传感器记录；Hadoop；互信息；XGBoost；风险预警")
    for r in ps[36].runs: set_run_font(r, "Songti SC", 12)
    set_paragraph_text(ps[37], "")
    set_paragraph_text(ps[41], "This thesis designs and implements a prototype for spoilage-risk classification from cold-storage sensor records. The system validates and cleans a public Mendeley Data CSV, verifies an HDFS round trip, computes mutual information on the training split, scales selected features, and compares baseline XGBoost with a mutual-information-weighted XGBoost classifier. A Spring Boot and SQLite service provides record browsing, prediction, alert persistence, and experiment-result views. The dataset contains 10,995 records but no timestamp, so the work is described as classification of sensor records rather than strict time-series forecasting. The fixed experiment achieved 0.999090 accuracy for the baseline and 1.000000 recall with 0.999998 ROC-AUC for the weighted model. The project also verifies a Hadoop 3.5.0 single-node run on macOS arm64 and a Windows x64 model-runner executable smoke test. The evidence shows a traceable prototype chain, while the conclusions remain limited by the public static dataset and the fact that weighting does not improve every metric.")
    style_body(ps[41], indent=True)
    ps[41].paragraph_format.space_before = Pt(0)
    ps[41].paragraph_format.space_after = Pt(0)
    for r in ps[41].runs: set_run_font(r, "Times New Roman", 12)
    for r in ps[42].runs: set_run_font(r, "Times New Roman", 11)
    set_paragraph_text(ps[42], "Key words：cold-storage sensor records；Hadoop；mutual information；XGBoost；risk alert")
    for i in (10, 23, 34, 40, 46):
        if i < len(ps):
            for r in ps[i].runs:
                set_run_font(r, "Heiti SC", 15, bold=True)

def references():
    return [
        "[1] Müller M, et al. Enhancing food safety in the cold chain through Internet of Things and artificial intelligence[J]. Journal of Food Science, 2026, 91(2): e70871. DOI:10.1111/1750-3841.70871.",
        "[2] Liang M, Ni Y, He X, et al. Deep learning models for shelf life prediction and regulation of various foods: a systematic review[J]. Journal of Food Science, 2026, 91(3): e70945. DOI:10.1111/1750-3841.70945.",
        "[3] Guo Z, Zhang Y, Xiao H, et al. Multi-sensor fusion and deep learning for batch monitoring and real-time warning of apple spoilage[J]. Food Control, 2025, 160: 111174. DOI:10.1016/j.foodcont.2025.111174.",
        "[4] Wang D, Zhang M, Zhu Q, et al. Intelligent vegetable freshness monitoring system developed by integrating eco-friendly fluorescent sensor arrays with deep convolutional neural networks[J]. Chemical Engineering Journal, 2024, 488: 150739. DOI:10.1016/j.cej.2024.150739.",
        "[5] Luo Z, Liu W, Wu J, et al. Prediction of cold chain loading environment for agricultural products based on K-medoids-LSTM-XGBoost ensemble model[J]. PeerJ Computer Science, 2024, 10: e2510. DOI:10.7717/peerj-cs.2510.",
        "[6] Hardiansyah B A, Sukoco H, Wijaya S H. Monitoring and controlling system for mango logistics based on machine learning[J]. Jurnal RESTI, 2024, 8(1): 150-159. DOI:10.29207/resti.v8i1.5226.",
        "[7] Xia J, Huang W, Wang X, et al. Flexible sensing technology for fruit quality control in the cold chain: characterization, application, and improvement[J]. Food Control, 2023, 154: 109976. DOI:10.1016/j.foodcont.2023.109976.",
        "[8] Huang W, Wang X, Xia J, et al. Flexible sensing enabled agri-food cold chain quality control: a review of mechanism analysis, emerging applications, and system integration[J]. Trends in Food Science & Technology, 2023, 133: 189-204. DOI:10.1016/j.tifs.2023.02.010.",
        "[9] Zou Y, Wu J, Wang X, et al. An improved artificial neural network using multi-source data to estimate food temperature during multi-temperature delivery[J]. Journal of Food Engineering, 2023, 351: 111518. DOI:10.1016/j.jfoodeng.2023.111518.",
        "[10] Yuan Y, Chen X. Vegetable and fruit freshness detection based on deep features and principal component analysis[J]. Current Research in Food Science, 2024, 8: 100656. DOI:10.1016/j.crfs.2023.100656.",
        "[11] Reka S S, Bagelikar A, Venugopal P, et al. Deep learning-based classification of rotten fruits and identification of shelf life[J]. Computers, Materials & Continua, 2024, 78(1): 781-794. DOI:10.32604/cmc.2023.043369.",
        "[12] Srinivasagan R, Mohammed M, Alzahrani A. TinyML-sensor for shelf life estimation of fresh date fruits[J]. Sensors, 2023, 23(16): 7081. DOI:10.3390/s23167081.",
        "[13] Friedman J H. Greedy function approximation: a gradient boosting machine[J]. The Annals of Statistics, 2001, 29(5): 1189-1232. DOI:10.1214/aos/1013203451.",
        "[14] Kraskov A, Stögbauer H, Grassberger P. Estimating mutual information[J]. Physical Review E, 2004, 69(6): 066138. DOI:10.1103/PhysRevE.69.066138.",
        "[15] Acquaticci L. Study of meat shelf-life markers and food quality through different instrumental analytical methods[D]. Camerino: University of Camerino, 2023. https://hdl.handle.net/11581/484285.",
        "[16] Dang S. Assessment and optimisation of sustainable food cold chain logistics from a circular economy perspective[D]. Liverpool: University of Liverpool, 2024. DOI:10.17638/03183538.",
        "[17] Bourely J A P. Biodegradable and printed chipless environmental sensors for sustainable Internet-of-Things applications[D]. Lausanne: EPFL, 2024. DOI:10.5075/epfl-thesis-10803.",
        "[18] Ince V. Application of explainable artificial intelligence and generative data modelling to enhance food safety in meat products[D]. Portsmouth: University of Portsmouth, 2026.",
    ]

def build_body(doc):
    allp = doc.paragraphs
    body_heading_idx = next(
        i for i, p in enumerate(allp)
        if p.style.name == "Heading 1" and p.text.startswith("第1章")
    )
    breaks = [p for p in allp[body_heading_idx:] if p._p.pPr is not None and p._p.pPr.sectPr is not None]
    break_ids = {id(p._p) for p in breaks}
    # Remove the template's sample body while preserving its section-break paragraphs.
    for p in list(doc.paragraphs)[body_heading_idx:]:
        if id(p._p) not in break_ids:
            p._p.getparent().remove(p._p)
    breaks = [p for p in doc.paragraphs[body_heading_idx:] if p._p.pPr is not None and p._p.pPr.sectPr is not None]
    if len(breaks) < 7:
        raise RuntimeError(f"expected 7 body section breaks, got {len(breaks)}")

    c1, c2, c3, c4, c5, c6, cref = breaks[:7]

    # Keep the template's Roman-numbered section break after the TOC and the
    # decimal section break after Chapter 1.  Extra TOC spacing above fills the
    # second Roman page, so LibreOffice does not materialize an empty section
    # page between the TOC and Chapter 1.

    # The template includes a demonstration table containing “11 pt宋体”. It
    # is not part of the submitted paper and would otherwise create a blank
    # page before Chapter 1.
    if len(doc.tables) > 2:
        demo = doc.tables[2]._tbl
        demo.getparent().remove(demo)

    # Chapter 1
    add_heading(c1, "第1章　绪论", 1)
    add_p(c1, "随着冷链仓储和物联网传感器的普及，温度、湿度、光照和二氧化碳等环境记录被持续采集。数据本身并不会自动转化为管理动作：字段命名不统一、异常值未处理、记录与模型结果脱节，都会使管理人员只能依赖经验巡检。已有研究表明，温度管理、传感器网络、智能包装和多传感器模型是降低易腐食品损耗的重要基础[1][2][3][4][7][8]。因此，本项目选择一个可复现的公开记录集，构建从数据清洗到风险提示的完整原型，而不是宣称替代实际冷库的质量检测。")
    add_heading(c1, "1.1　研究背景与问题提出", 2)
    add_p(c1, "在冷库管理场景中，管理人员需要回答三个相互关联的问题：当前记录是否完整可信，记录对应的损耗风险是否值得优先处理，以及模型结果能否回写到业务系统形成可追溯的预警。传统脚本通常只完成其中一环，清洗结果、模型文件和页面展示之间缺少固定接口。本文将问题转化为一个可验收的工程链路：以公开传感器记录为输入，以 Good/Bad 二分类为输出，以 SQLite 保存业务记录，以 Web 页面展示结果，并使用 Hadoop HDFS 验证离线文件链路。")
    add_p(c1, "需要特别说明的是，所用数据集没有时间戳。它能支持静态记录分类，却不能直接支持按小时或按批次的时间序列预测，也不能据此计算真实货架期。本文在题目和正文中使用“传感器记录损耗预测系统”这一工程表述，但在方法和结论中将其限定为记录级风险分类。")
    add_p(c1, "输入由水果类别和四个环境数值组成，输出 Good/Bad 及 Bad 类概率；服务层固定 0.5 生成 HIGH 预警。该阈值是系统规则，现场应用需用独立数据重新标定。")
    add_p(c1, "近期研究从多传感器融合、冷链温度估计、鲜度识别和智能包装等方向展开[5][6][9][10][11][12]；相关学位工作关注货架期、冷链物流、传感器材料和可解释模型[15][16][17][18]。")
    add_p(c1, "本文还把“不能验证”的范围写进系统边界。没有时间戳意味着不能做时间窗口切分，没有现场传感器意味着不能验证传感器漂移，没有 Windows 全应用包意味着不能把模型 EXE 烟测写成完整客户端验收。边界被明确记录后，实验结果的解释就不会超过证据能够支持的范围。")
    add_heading(c1, "1.2　研究内容与技术路线", 2)
    add_p(c1, "本文的工作分为四个部分。第一，固定数据来源、版本和文件 SHA-256，完成字段映射、标签编码、数值转换和清洗报告。第二，使用 Hadoop 3.5.0 单节点伪分布式 HDFS 完成原始文件上传、处理结果存储、回读和哈希核验。第三，在训练集上计算互信息，按中位数筛选特征并缩放输入，比较基线 XGBoost 和互信息加权 XGBoost。第四，使用 Spring Boot、SQLite 和静态 Web 页面实现记录、预测、预警和实验指标的闭环。")
    add_p(c1, "算法实验采用两条并行路径。基线模型使用标准化后的全部编码特征；加权模型只使用训练集互信息达到中位数的特征，并按互信息比例缩放。两条路径使用同一随机种子、同一训练测试划分和同一 XGBoost 参数，比较结果才具有可比性。")
    add_heading(c1, "1.3　论文组织结构", 2)
    add_p(c1, "第一章说明研究背景、问题边界和主要工作；第二章给出需求、架构、数据实体和接口设计；第三章说明数据、HDFS、互信息和模型实验；第四章说明后端、SQLite 和 Web 实现；第五章按照自动化测试、模型指标、API 联调、HDFS 实机和 Windows 模型 EXE 烟测给出证据；第六章总结研究结果并说明后续工作。")
    add_p(c1, "全文按照“需求—设计—实现—测试—结论”的顺序组织。需求章节只提出可验证的功能和非功能目标，设计章节说明模块和数据关系，实现章节对应源码目录，测试章节引用仓库中的执行记录，结论章节只归纳已经完成和已经验证的部分。图题采用章号点序号，正文在图前给出用途说明，避免出现只放图片不解释的情况。")

    # Chapter 2
    add_heading(c2, "第2章　需求分析与总体设计", 1)
    add_p(c2, "系统面向需要查看冷库环境记录并处理风险提示的管理人员，当前交付定位为毕业设计原型。设计的首要目标是让数据、模型和页面使用同一套字段口径，第二目标是让每一次预测都可以在数据库中追溯，第三目标是为离线 HDFS 处理和 Windows 模型运行器保留清晰的边界。")
    add_p(c2, "系统的主要使用场景可以分为查看、预测、追踪和复核四类。查看场景读取已经保存的传感器记录；预测场景提交一条记录并接收模型结果；追踪场景查看 HIGH 预警及其创建时间；复核场景查看实验指标和模型版本。四类场景均由页面标签进入，并由后端接口提供数据。")
    add_p(c2, "本项目只有一个实际业务角色，即管理人员。管理人员不负责重新训练模型，也不直接修改模型权重；模型训练属于离线实验流程，页面只展示导入的实验指标和当前服务使用的模型版本。将这两个角色边界分开，可以避免在论文中虚构管理员、审核员或设备操作员等当前系统没有实现的权限。")
    add_p(c2, "系统输入分为两类：一类是 CSV 文件，用于批量清洗和训练；另一类是页面表单或 REST JSON，用于单条预测。两类输入最终都映射为 fruit、temp、humid、light 和 co2 五个模型特征。source 字段只记录来源说明，不进入模型特征，避免把文件名或人工备注泄漏到训练过程。")
    add_p(c2, "系统输出也分为两类：离线输出包括清洗报告、模型指标和模型文件，在线输出包括预测标签、风险概率、模型版本和预警级别。离线输出用于复现和论文实验，在线输出用于页面操作和业务追踪，两者通过固定的字段名和版本值连接。")
    add_heading(c2, "2.1　业务需求与可行性", 2)
    add_p(c2, "业务上，用户可以浏览已经保存的传感器记录，输入一条水果和环境记录，提交模型预测，并查看预测历史和 HIGH 预警。由于数据集只有 Good/Bad 标签，页面中的“风险概率”是分类模型对 Bad 类的概率，不代表百分比损耗，也不表示经过校准的食品安全概率。")
    add_p(c2, "技术上，数据清洗和模型训练使用 Python；离线文件链路使用 Hadoop HDFS；服务层使用 Spring Boot 3.3.5；数据库使用 SQLite；前端使用静态 HTML、CSS 和 JavaScript。各组件通过 CSV、JSON 和 REST 连接，依赖边界清楚，适合在开发机上完成复现。经济上，项目使用公开数据集和开源软件，不要求部署付费云服务。")
    add_heading(c2, "2.2　功能与非功能需求", 2)
    add_table(c2, ["编号", "功能需求", "验收口径"], [
        ("F1", "传感器记录管理", "记录 fruit、temp、humid、light、co2、source，并支持查询"),
        ("F2", "风险预测", "提交 JSON 后返回 label、riskProbability、modelVersion"),
        ("F3", "预警管理", "Bad 或风险概率不低于 0.5 时保存 HIGH 预警"),
        ("F4", "实验指标", "返回基线和加权模型的 Accuracy、Recall、F1、ROC-AUC 等"),
        ("F5", "错误反馈", "模型缺失、输入错误和接口异常返回明确错误，不生成假结果"),
    ], "表2.1　功能需求与验收口径")
    add_p(c2, "F1 的验收重点是输入记录能够被保存并再次查询，查询结果必须包含模型真正使用的五个字段和来源说明。F2 的验收重点是模型协议与页面字段一致，返回值必须同时包含标签、概率和模型版本。F3 的验收重点是风险条件能够落到 alert_record，页面查询到的 HIGH 预警必须可以回到对应 prediction_record。")
    add_p(c2, "F4 读取离线实验结果，不在在线请求中重新计算训练指标；这使页面加载不会触发训练，也避免模型指标因请求时间不同而变化。F5 贯穿所有功能，输入错误、模型缺失和接口异常都必须有可读提示，异常路径不产生一条看似成功的预测记录。")
    add_p(c2, "输入字段的业务约束与模型约束分开处理。fruit 必须属于训练时出现的类别；temp、humid、light 和 co2 必须能够转换为有限数值；source 可以为空但不能覆盖模型字段。后端负责最终校验，前端校验只用于减少明显的操作错误，不能把浏览器校验当作唯一安全边界。")
    add_p(c2, "响应时间在本项目中只作为本机联调观察项，没有设置未经测试的统一小于2秒承诺。服务端的模型调用有超时配置，超时后返回模型不可用错误；数据库写入失败和模型返回错误分别记录在对应异常分支。后续若要提出性能指标，需要以实际并发、负载、持续时间和统计口径为前提。")
    add_p(c2, "系统暂不实现用户登录、权限分级和多租户隔离。这个限制不是遗漏后再用文字掩盖，而是当前毕业设计原型的范围决定。论文中只把管理人员作为实际角色，安全部分集中说明输入校验、路径配置、错误反馈和不保存凭据，避免在没有实现的模块上写出虚假的验收结论。")
    add_p(c2, "非功能需求包括可追溯性、可复现性和可维护性。可追溯性要求保存数据来源、模型版本和预测时间；可复现性要求固定随机种子并记录配置；可维护性要求模型运行协议与后端解耦，数据库路径和模型命令可由环境变量替换。系统不在本阶段承诺高并发、生产级权限体系或多租户部署。")
    add_heading(c2, "2.3　系统总体架构", 2)
    add_p(c2, "系统按数据层、离线处理层、算法层、服务层和展示层组织。原始数据和清洗结果属于数据层；HDFS 负责离线文件存取和链路核验；算法层保存互信息权重和 XGBoost 模型；服务层把模型调用和 SQLite 持久化封装为 REST 接口；展示层只消费接口返回的数据，不在浏览器内置假数据。")
    add_figure_context(c2, "如图2.1所示，系统将公开记录、离线文件处理、互信息特征工程、模型服务和 Web 展示串成一条数据流；每层通过稳定的文件或接口边界交接，便于单独复现和定位错误。", FIG / "fig2_1_architecture.png", "图2.1　系统总体架构")
    add_p(c2, "数据层不改变原始文件内容，清洗结果以新的文件保存。离线处理层只负责文件和报告，不直接写入在线 SQLite；算法层的模型文件由训练脚本产生，服务层通过环境变量定位。展示层没有自己的数据副本，刷新页面时重新请求后端，这样可以发现数据库状态和页面状态不一致的问题。")
    add_p(c2, "模块间的接口边界按数据方向划分：CSV 到 ETL 是文件接口，ETL 到 HDFS 是目录接口，模型运行器到服务层是标准输入输出接口，服务层到前端是 REST 接口。每个边界都保留错误反馈，避免某一层失败后下一层仍以默认值继续运行。")
    add_heading(c2, "2.4　数据库与接口设计", 2)
    add_p(c2, "SQLite 设计四类核心实体：sensor_record 保存输入记录，prediction_record 保存一次模型调用，alert_record 保存预警状态，experiment_metric 保存离线实验指标。prediction_record 通过 sensor_record_id 关联输入；alert_record 通过 prediction_id 关联预测。核心接口包括 GET /api/health、GET/POST /api/records、POST /api/predict、GET /api/predictions、GET /api/alerts 和 GET /api/experiments。")
    add_p(c2, "POST /api/records 只负责把传感器记录写入 sensor_record，适合在预测前先保存原始输入；POST /api/predict 则完成保存输入、调用模型、保存预测和必要时生成预警的一次闭环。GET /api/predictions 返回模型版本和概率，GET /api/alerts 通过关联查询同时返回标签、概率、级别、提示和时间，页面无需自行拼接数据库关系。")
    add_figure_context(c2, "图2.2给出了从管理人员提交记录到生成预警的主流程。流程中先校验输入，再调用模型并写入预测记录；模型不可用或输入非法时沿异常分支返回错误，不写入伪造结果。", FIG / "fig2_2_flow.png", "图2.2　预测与预警业务流程")
    add_figure_context(c2, "为明确角色能够操作的功能范围，图2.3展示管理人员与五个实际用例的对应关系。用例名称与 Web 控制台的标签和接口保持一致。", FIG / "fig2_4_usecase.png", "图2.3　管理人员用例图")
    add_figure_context(c2, "图2.4进一步把记录、预测、预警、指标和控制台拆成实际模块，说明模块之间的数据方向。该模块划分没有加入当前系统不存在的登录、设备控制或多租户功能。", FIG / "fig2_5_modules.png", "图2.4　系统功能模块图")
    add_figure_context(c2, "数据库关系如图2.5所示。sensor_record 是输入事实，prediction_record 保存模型调用，alert_record 保存风险状态，experiment_metric 保存离线比较结果；这种关系支持从预警回查输入和模型版本。", FIG / "fig2_3_er.png", "图2.5　SQLite 核心实体关系")

    # Chapter 3
    add_heading(c3, "第3章　数据处理与模型设计", 1)
    add_p(c3, "本章说明数据来源、字段处理、HDFS 实测、互信息加权定义和模型评价。所有统计结果均来自仓库中的 CSV、JSON 报告和模型指标文件；正文不把公开数据集的标签分布解释为现实仓储损耗率。")
    add_heading(c3, "3.1　数据来源与字段定义", 2)
    add_p(c3, "数据来自 Mendeley Data 数据集 A Multi-Parameter Dataset for Machine Learning Based Fruit Spoilage Prediction in an IoT-Enabled Cold Storage System，数据集标识为 czz68d9fwj/1，DOI 为 10.17632/czz68d9fwj.1，许可证为 CC BY 4.0。项目保存了下载文件 SHA-256、来源 JSON 和标签映射，原始文件包含 Fruit、Temp、Humid (%)、Light (Fux)、CO2 (pmm) 和 Class 六列。")
    add_p(c3, "选择该数据集的依据是字段与课题中的冷库环境记录口径相近，并且能够公开下载、固定版本和重复读取。数据集名称中虽然出现 IoT-enabled cold storage，但当前文件本身只提供表格记录，不包含设备编号、时间戳、位置或批次信息。论文因此使用“传感器记录表”描述实际输入，不把数据集标题扩展成已接入现场 IoT 设备的证明。")
    add_p(c3, "原始字段存在大小写、单位拼写和标签名称不统一的问题。ETL 将 Fruit、Temp、Humid (%)、Light (Fux)、CO2 (pmm) 和 Class 映射为小写规范字段，并把 Class 的 Good/Bad 映射为0/1。映射规则在清洗报告和模型代码中同时保留，保证训练、预测和论文表格使用同一语义。")
    add_p(c3, "fruit 是类别特征，其他四项是连续特征。模型训练时先对 fruit 做独热编码，再对数值列进行标准化；在线预测时使用训练阶段保存的类别集合和标准化器，输入字段编码顺序不能变化。source 字段用于审计来源，不进入编码矩阵。")
    add_table(c3, ["字段", "类型", "工程含义"], [
        ("fruit", "类别", "Orange、Pineapple、Banana、Tomato"),
        ("temp", "浮点数", "温度，单位 °C"),
        ("humid", "浮点数", "相对湿度，单位 %"),
        ("light", "浮点数", "光照强度，单位 Lux"),
        ("co2", "浮点数", "二氧化碳浓度，单位 ppm"),
        ("label / label_name", "整数 / 类别", "Good=0，Bad=1"),
    ], "表3.1　清洗后字段定义")
    add_p(c3, "ETL 清洗后保留 10,995 条记录，没有因缺失或非法范围而删除记录；Good 为 5,667 条，Bad 为 5,328 条。数据没有 timestamp 字段，schema.json 明确将 dataset_type 标记为 tabular_sensor_records，将 has_timestamp 标记为 false。")
    add_p(c3, "清洗脚本对每一列做了不同检查。类别列检查是否为空以及是否落在训练类别集合内；数值列先转换为浮点数，再检查空值、无穷值和项目定义的合理范围；标签列检查是否能归一化为 Good 或 Bad。任何校验失败都会中止处理并返回错误，不会静默把错误值替换成平均数。")
    add_figure_context(c3, "图3.1给出了清洗后 Good/Bad 标签数量和数据范围。该图只描述公开记录表的样本组成，不将标签比例解释为现场损耗率。", FIG / "fig3_2_distribution.png", "图3.1　标签分布与数据集范围")
    add_heading(c3, "3.2　数据清洗与 HDFS 链路", 2)
    add_p(c3, "清洗脚本首先检查输入文件是否存在，再读取表头并完成字段重命名；随后将温度、湿度、光照和二氧化碳转换为数值，检查空值、无穷值和标签集合，最后输出清洗 CSV、schema.json 和 cleaning_report.json。清洗报告记录输入行数、输出行数、标签分布、源文件哈希和执行时间，便于复查。")
    add_p(c3, "清洗过程具有可重复性。脚本不依赖当前工作目录，而是根据命令行参数或项目根路径定位输入和输出；输出文件先写入明确路径，再由后续模型脚本读取。重复执行时会覆盖同一份处理结果，但不会修改 data/raw/Dataset.csv，原始文件保持只读证据的角色。")
    add_p(c3, "HDFS 实测脚本把目录划分为 raw 和 processed 两层。raw 保存原始 Dataset.csv，processed 保存 cleaned_dataset.csv、schema.json 和 cleaning_report.json。目录分层让读者可以区分原始输入和处理输出，避免清洗文件覆盖原始文件后无法比较哈希。")
    add_p(c3, "上传阶段先检查 NameNode 和 DataNode 可用，再创建目录和复制文件；回读阶段把 HDFS 中的原始文件下载到临时路径，使用本地 sha256sum 与源文件比较。哈希一致只能证明文件传输完整，不能证明数据内容本身正确，因此仍需要结合清洗报告检查字段和标签。")
    add_p(c3, "本次实机环境是 macOS arm64 的 Hadoop 3.5.0 单节点伪分布式，Java 版本为17.0.21.1，在线 DataNode 为1。该环境用于验证脚本和文件链路，不代表多节点集群的吞吐、容错或生产容量。论文将这一边界写入测试结果，避免把单节点通过表述成集群验收。")
    add_p(c3, "HDFS 链路使用 hadoop/hdfs_ingest.sh：创建 /m09/cold-storage 下的 raw 与 processed 目录，将原始 Dataset.csv 上传到 raw，将清洗结果和报告写入 processed，再将原始文件回读到本地并比较 SHA-256。2026 年 11 月 22 日在 macOS arm64 上使用 Hadoop 3.5.0、Java 17.0.21.1 完成单节点伪分布式实机运行，NameNode 为 hdfs://localhost:9000，在线 DataNode 数为 1。原始文件和 HDFS 回读文件的 SHA-256 均为 218f76f061a12b0a38c55107e5be3b377e9eecb33f1a1840ef2b4e4618a5e5aa。")
    add_figure_context(c3, "如图3.2所示，ETL 与 HDFS 链路包含本地字段检查、清洗文件生成、raw/processed 目录写入和 SHA-256 回读四个可核验阶段。", FIG / "fig3_1_etl_hdfs.png", "图3.2　ETL 与 HDFS 实测链路")
    add_heading(c3, "3.3　互信息特征加权", 2)
    add_p(c3, "互信息用于度量特征与标签之间的非线性相关程度，计算口径参考互信息估计方法[14]。为避免测试集泄漏，本文只在训练集上完成独热编码、标准化和互信息计算，测试集只在最后评价时使用。对保留特征 j，定义权重为：")
    add_p(c3, "互信息的计算对象是训练样本中的编码特征和二分类标签。对类别变量，独热编码后每个类别成为一个二值列；对连续变量，先使用训练集拟合的 StandardScaler 变换。测试集不参与互信息排序、中位数阈值或权重均值的计算，避免把测试标签的信息泄漏到模型输入。")
    add_p(c3, "w_j = (MI_j + ε) / (mean(MI) + ε)，其中 ε=10^-6；缩放后的输入为 x'_j = x_j × w_j。以训练集互信息中位数为筛选阈值，并设置至少保留一个特征的保护条件。最终保留 fruit=Tomato、temp、humid、light 和 co2，light 的权重最高，为 1.945273；humid 为 1.194765；temp 为 1.051216；co2 为 0.795719。")
    add_p(c3, "权重的含义是输入缩放，而不是改变标签、样本数量或损失函数。light 的权重较高表示在当前训练划分中它的互信息分数相对较大；co2 的权重低于1表示其相对信息量较小。这个解释只对当前数据和固定切分成立，不能直接解释为真实冷库中某种传感器始终更重要。")
    add_figure_context(c3, "图3.3对比训练集互信息得分和由此得到的特征缩放系数，展示了加权模型并非重新定义标签，而是在训练输入侧改变特征尺度。", FIG / "fig3_3_mi_weights.png", "图3.3　训练集互信息得分与加权系数")
    add_heading(c3, "3.4　模型训练与评价指标", 2)
    add_p(c3, "实验固定随机种子 20261122，采用 8:2 分层划分，训练集 8,796 条，测试集 2,199 条。XGBoost 参数为 n_estimators=160、max_depth=4、learning_rate=0.08、subsample=0.9、colsample_bytree=0.9。模型评价以二分类指标为主，包括 Accuracy、Precision、Recall、F1 和 ROC-AUC；MSE、MAE、R² 只作为概率输出与 0/1 标签之间的辅助指标。")
    add_p(c3, "Accuracy 表示整体分类正确比例，Precision 表示被预测为 Bad 的记录中真正为 Bad 的比例，Recall 表示实际 Bad 记录被找出的比例，F1 是 Precision 与 Recall 的调和平均，ROC-AUC 描述不同阈值下的排序能力。对于预警系统，Recall 直接关系到漏掉高风险记录的数量，但过度追求 Recall 可能带来更多误报，因此需要结合 Precision 和运营成本解释。")
    add_p(c3, "MSE、MAE 和 R² 不是本项目的主要分类指标，它们用于观察概率输出与0/1标签之间的数值偏差。把这些回归辅助指标放在表中，是为了与开题报告的评价口径保持对应；论文不根据它们单独宣称分类模型更好。")
    add_p(c3, "训练和测试使用同一数据源但不同样本索引。基线模型在标准化后的完整编码特征上训练，加权模型在筛选并缩放后的特征上训练，两个模型都使用 binary:logistic 目标和 logloss 评价；梯度提升模型的基本思想参考 Friedman 的工作[13]。模型文件保存完整的编码器、标准化器、互信息分数、特征权重和 XGBoost 模型，在线预测不会重新拟合。")
    add_p(c3, "测试阈值固定为0.5。这个阈值使在线服务的 label 规则与离线指标一致，但并不意味着0.5是现场最优阈值。若现场更重视漏报，应在独立验证集上比较不同阈值下的 Recall、Precision 和预警数量，再把阈值作为有版本记录的配置部署。")
    add_p(c3, "混淆矩阵按照测试集中每条记录的真实标签和预测标签计算，图3.5的 TN、FP、FN、TP 总和为2,199，与测试集行数一致。矩阵显示没有漏检 Bad，但存在3条 Good 被标成 Bad；这正好说明只看 Recall 会忽略误报代价。")
    add_p(c3, "当前实验没有进行多随机种子、交叉验证、概率校准或跨数据集外部验证，因此指标的统计稳定性尚未得到充分检验。公开数据集的标签可能已经包含与传感器数值高度相关的规则，接近满分的结果需要谨慎解释，不应直接替代现场抽检。")
    add_table(c3, ["模型", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "MSE", "MAE", "R²"], [
        ("原始 XGBoost", "0.999090", "0.999062", "0.999062", "0.999062", "0.999997", "0.000801", "0.004032", "0.996794"),
        ("互信息加权 XGBoost", "0.998636", "0.997194", "1.000000", "0.998595", "0.999998", "0.001130", "0.005502", "0.995476"),
    ], "表3.2　两种模型测试集指标")
    add_figure_context(c3, "图3.4把五个主要分类指标放在同一尺度下比较。由于不同指标的业务含义不同，图形只用于观察差异，最终结论仍以表3.2中的数值为准。", FIG / "fig3_4_metrics.png", "图3.4　基线与加权模型测试集指标")
    add_figure_context(c3, "图3.5是加权 XGBoost 在固定测试集上的逐样本混淆矩阵，其中实际 Good 被误判为 Bad 的数量为3，实际 Bad 未被漏检，矩阵与 evidence/models/confusion_matrix.json 一致。", FIG / "fig3_5_confusion.png", "图3.5　加权 XGBoost 测试集混淆矩阵")
    add_p(c3, "从固定切分结果看，加权模型 Recall 和 ROC-AUC 略高，但 Accuracy、Precision、F1、MSE、MAE 和 R² 不优于基线。因此本文将互信息缩放描述为一个可复现的特征工程方案，不作“全面提升”的结论。后续若要形成更强结论，应增加多随机种子、交叉验证和置信区间。")

    # Chapter 4
    add_heading(c4, "第4章　系统详细设计与实现", 1)
    add_p(c4, "系统实现围绕“输入记录—模型调用—结果持久化—风险展示”展开。后端和前端之间使用 JSON，模型运行器通过标准输入输出接收一条记录并返回一条预测结果。该设计让 Python 模型可以在 macOS 脚本、Windows x64 EXE 和后续容器中替换，而不改变业务接口。")
    add_p(c4, "服务启动时由 Spring Boot 读取 application.yml 和环境变量，初始化 SQLite 数据源并加载静态资源。模型文件不在 Java 进程中直接解析，而由配置的命令启动 Python 运行器；这种边界降低了 Java 与 Python 依赖的耦合，也使模型运行器可以单独打包。")
    add_heading(c4, "4.1　后端服务实现", 2)
    add_p(c4, "Spring Boot 后端提供健康检查、记录读写、预测、历史查询和实验指标接口。POST /api/predict 接收 fruit、temp、humid、light、co2，先校验必填字段和数值类型，再写入 sensor_record，随后调用 M09_MODEL_COMMAND 指向的模型运行器。模型返回 label、riskProbability 和 modelVersion 后，服务层保存 prediction_record，并根据标签为 Bad 或概率不低于 0.5 的条件生成 HIGH 预警。")
    add_p(c4, "记录接口和预测接口的字段均使用 JSON。fruit 是字符串，四个传感器值是数字，source 是可选字符串。后端将请求体映射为 Java record，再由服务层调用模型命令。输入校验放在控制器和服务边界，避免模型进程接收到无法解析的数据。")
    add_p(c4, "模型运行器通过标准输入读取一个对象，输出一个对象；输出至少包含 label、riskProbability、modelVersion 和 metricsJson。服务层对退出码、超时、空输出和错误字段进行检查。模型进程异常不会被吞掉，前端能够看到“模型调用未完成”以及后端返回的错误摘要。")
    add_p(c4, "预警生成规则是业务规则而不是模型代码的一部分。label 为 Bad 或 riskProbability 大于等于0.5 时，PredictionService 写入 HIGH 级别的 alert_record；Good 且概率低于阈值时只保存预测，不新增 HIGH 预警。规则在数据库记录中留下 prediction_id，方便审计。")
    add_p(c4, "接口查询按 id 倒序返回最近记录，limit 参数被限制在合理范围内。预警查询使用 alert_record 与 prediction_record 的关联查询，一次返回标签、概率、级别、提示和时间；实验指标查询返回数据库中的两种模型记录。前端不依赖字段排列顺序，而是按字段名称渲染。")
    add_p(c4, "服务与模型进程之间的协议还承担迁移边界。macOS 开发环境使用 scripts/run_model.sh 调用 Python，Windows x64 烟测使用 PyInstaller 生成的模型运行器；两者最终都向服务层返回同样的字段。全应用 Windows 包尚未完成，因此论文只把已验证的 EXE 范围写到交付结果。")
    add_heading(c4, "4.2　SQLite 持久化实现", 2)
    add_p(c4, "数据库路径由 M09_DB_PATH 配置，应用启动时创建 sensor_record、prediction_record、alert_record 和 experiment_metric 表。预测记录保存输入记录外键、预测标签、风险概率、模型版本和创建时间；预警记录保存级别、消息和关联预测。通过外键关系，可以从一条预警追溯到原始传感器值和模型版本。")
    add_p(c4, "sensor_record 的 source 字段记录数据来源，created_at 记录服务写入时间；它们不参与模型计算。prediction_record 的 metrics_json 用于保留当时的模型指标摘要，model_version 用于区分模型文件。alert_record 的 status 目前写入 OPEN，后续可扩展关闭和复核状态，但当前论文不把未实现的状态流转写成已完成。")
    add_p(c4, "数据库表名和字段名与 API 和页面保持一致，减少跨层映射错误。例如 risk_probability 在数据库、预测响应和页面格式化中使用同一含义；alert_level 和 alert_message 由查询直接给出，避免前端把 level、message 与预测表字段混淆。")
    add_table(c4, ["实体", "主键", "主要字段", "关联"], [
        ("sensor_record", "id", "fruit、temp、humid、light、co2、source", "1:N prediction_record"),
        ("prediction_record", "id", "label、risk_probability、model_version", "N:1 sensor_record"),
        ("alert_record", "id", "alert_level、alert_message、created_at", "N:1 prediction_record"),
        ("experiment_metric", "id", "model_name、accuracy、recall、f1、roc_auc", "独立指标表"),
    ], "表4.1　核心数据库实体")
    add_heading(c4, "4.3　Web 控制台实现", 2)
    add_p(c4, "前端采用静态页面实现总览、传感器记录、风险预测、预警记录和模型指标五个区域。页面加载时并行请求记录、预测、预警和指标接口；切换到风险预测区域后，用户选择水果并输入四项传感器值，提交成功后展示标签、风险概率、模型版本和预警级别。页面只渲染接口返回的数据，接口不可用时显示明确的错误状态。")
    add_p(c4, "总览页面把记录数、预测次数、高风险预警数和模型版本放在同一组统计卡中，帮助用户先判断服务是否有数据。记录页面用表格查看输入字段和来源；风险预测页面把表单和结果卡并列；预警页面显示关联的概率和消息；指标页面展示离线实验结果。五个页面通过同一组顶部标签切换。")
    add_p(c4, "风险预测表单的输入顺序与模型特征顺序一致：水果类型、温度、湿度、光照、二氧化碳和来源说明。提交后按钮状态和提示文字反映请求阶段，结果卡显示 Bad/Good 标签、概率条、模型版本和 HIGH 状态。截图中的输入值来自已运行的本机后端，不是静态设计稿。")
    add_p(c4, "预警列表的每一行可以从 label、risk_probability、alert_level、alert_message 和 created_at 解释其来源。页面修订前曾因接口字段没有直接返回关联预测字段而显示 NaN；本次将查询字段和前端兼容映射一并修复，并重新用浏览器截图检查，避免把空值截图作为最终证据。")
    add_p(c4, "实验指标页同时显示 Accuracy、Precision、Recall、F1、ROC-AUC、MSE、MAE 和 R²。页面显示的数值来自 SQLite 中导入的真实 metrics.json，而不是前端常量；如果指标表为空，页面会显示“暂无实验指标”，不会用假数据填充。")
    add_figure_context(c4, "图4.1汇总本机 API 联调的请求、状态码和返回摘要，说明后端功能已经由健康检查、记录写入、模型调用、历史查询和预警查询串联验证。", FIG / "fig4_1_api_evidence.png", "图4.1　本机 API 联调证据（后端功能）")
    add_p(c4, "本项目没有把“浏览器页面能打开”作为唯一验收标准。页面状态需要与后端接口和 SQLite 记录联动，测试中分别验证健康检查、页面返回、记录写入、预测保存、预测历史和预警查询。为了满足软件设计说明书对真实界面证据的要求，本节进一步使用本机运行版本截图覆盖总览、记录浏览、预测返回、预警列表和实验指标五类功能。")
    add_figure_context(c4, "图4.2是本机后端已连接时的总览页面，页面统计卡、最近记录和最近预警均来自 SQLite 与接口返回。", FIG / "ui-screenshots/fig4_2_ui_overview.png", "图4.2　本机 Web 控制台总览界面")
    add_figure_context(c4, "图4.3展示传感器记录浏览界面，表格中的水果、温度、湿度、光照、二氧化碳、来源和时间对应后端记录字段。", FIG / "ui-screenshots/fig4_3_ui_records.png", "图4.3　传感器记录浏览界面")
    add_figure_context(c4, "图4.4展示一次真实预测操作的输入与返回结果：输入 Tomato、30°C、95%、10 Lux 和900 ppm，返回 Bad、风险概率60.0%及 HIGH 预警级别。", FIG / "ui-screenshots/fig4_4_ui_predict.png", "图4.4　风险预测结果界面")
    add_figure_context(c4, "图4.5展示预警列表，标签、风险概率、预警级别、提示和时间由关联的 prediction_record 与 alert_record 联合返回。", FIG / "ui-screenshots/fig4_5_ui_alerts.png", "图4.5　预警记录界面")
    add_figure_context(c4, "图4.6展示实验指标页面，基线和互信息加权模型的主要分类指标及 MSE、MAE、R² 辅助指标来自 evidence/models/metrics.json 导入的 SQLite 记录。", FIG / "ui-screenshots/fig4_6_ui_experiments.png", "图4.6　模型指标界面")

    # Chapter 5
    add_heading(c5, "第5章　系统测试与结果分析", 1)
    add_p(c5, "测试分为数据与模型单元测试、后端 Maven 测试、前端语法检查、API 联调、HDFS 实机运行和 Windows x64 模型运行器烟测六类。测试报告保存在 evidence/tests/TEST_REPORT.md，交付证据分别保存在 evidence/runtime/api、evidence/delivery 和 evidence/hadoop/run。")
    add_p(c5, "测试数据与论文中的实验数据保持区分。模型测试集使用固定的2,199条记录，API 联调用一条 Tomato 记录触发服务链路，HDFS 测试使用完整 CSV 文件，界面截图使用本机 SQLite 中的演示记录。不同测试的目的和数据范围不同，不能把它们合并成一个准确率或一组样本。")
    add_heading(c5, "5.1　测试环境与测试用例", 2)
    add_table(c5, ["类别", "条件与操作", "预期", "实际", "状态", "证据"], [
        ("ETL、模型、运行器", "Python unittest discover -s tests -v", "测试用例完成且无异常", "5/5 通过", "通过", "evidence/tests/TEST_REPORT.md"),
        ("后端", "mvn -q -f backend/pom.xml test", "控制器与服务测试通过", "3 项通过", "通过", "backend/src/test"),
        ("前端", "node --check backend/src/main/resources/static/app.js", "静态脚本语法正确", "命令退出码0", "通过", "evidence/tests/TEST_REPORT.md"),
        ("本机联调", "health、记录、预测、历史和预警请求", "响应成功且数据入库", "health/记录/预测/预警均返回", "通过", "evidence/runtime/api/local_integration.json"),
        ("HDFS 实机", "Hadoop 3.5.0、Java 17、1 DataNode，上传并回读", "行数、目录和哈希可核对", "10,995 行；SHA 一致", "通过", "evidence/delivery/hadoop-real-run.json"),
        ("Windows 模型", "GitHub Actions 44996354530 构建并运行 PE32+ x86-64", "EXE 输出合法 JSON", "PyInstaller 构建与 smoke 通过", "通过", "evidence/delivery/model-exe-windows.json"),
        ("全应用 Windows", "Windows 10/11 x64 解压、双击、重启和迁移", "全应用页面可用", "尚未取得目标环境", "未验证", "evidence/delivery/ENVIRONMENT_STATUS.md"),
    ], "表5.1　测试环境、步骤与结果")
    add_heading(c5, "5.2　模型实验结果", 2)
    add_p(c5, "固定测试集上，原始 XGBoost Accuracy 为 0.999090，互信息加权模型 Accuracy 为 0.998636；加权模型 Recall 达到 1.000000，ROC-AUC 为 0.999998。对于预警场景，Recall 代表 Bad 记录被识别出来的比例，因此加权模型在该指标上具有工程吸引力；但是其 Precision、F1 和概率误差指标略低，说明不能只用单一指标判断模型优劣。")
    add_p(c5, "混淆矩阵中 TN=1130、FP=3、FN=0、TP=1066。对于当前测试集，FN=0带来了1.000000的 Recall，但这并不能保证在新冷库数据上仍然没有漏报。矩阵只对固定切分有效，外部数据和时间切分需要重新计算。")
    add_p(c5, "高指标还可能与公开数据的标签生成方式有关。若标签与传感器阈值直接相关，树模型容易在同分布测试集上取得接近满分的结果；这不等于模型能够识别所有真实损耗原因。因此结论把模型定位为记录级风险分类原型，未来需要现场标签和跨批次验证。")
    add_heading(c5, "5.3　系统联调与交付验证", 2)
    add_p(c5, "本机 API 联调使用 macOS、Java 17、Spring Boot 3.3.5、SQLite 和 ml/model_runner.py。GET /api/health 返回 200；GET / 返回静态页面；POST /api/records 成功写入 SQLite；使用 Tomato、温度 30、湿度 95、光照 10、二氧化碳 900 的记录调用 POST /api/predict，返回 Bad、risk_probability=0.60024434，并生成 HIGH 预警；预测和预警查询接口可以读回结果。")
    add_p(c5, "真实 Web 截图使用同一个本机后端和 SQLite 数据库，浏览器视口为1440×1000。图4.2至图4.6分别覆盖总览、传感器记录、风险预测、预警记录和模型指标。截图中的风险概率为60.0%，与 API 联调返回的0.60024434在显示精度上对应，页面不再出现 NaN。")
    add_p(c5, "HDFS 实机验证与 API 联调相互独立。HDFS 证明离线文件可以上传、回读和校验，API 证明服务可以读取模型并保存预测；两者都不直接证明目标 Windows 上的全应用已经启动。论文将它们列为不同证据，避免把“数据链路通过”扩大为“部署链路通过”。")
    add_figure_context(c5, "图5.1列出 HDFS 实机运行所使用的版本、节点、目录、行数和回读结果，读者可以据此定位 evidence/delivery/hadoop-real-run.json。", FIG / "fig5_1_hdfs_evidence.png", "图5.1　HDFS 实机运行证据")
    add_p(c5, "HDFS 实机证据显示，NameNode 和 DataNode 正常运行，raw、processed 目录中的对象可列出，原始文件回读后 SHA-256 与本地源文件一致。HDFS 运行不改变模型评价口径，只验证了离线数据链路的可复现性。")
    add_figure_context(c5, "图5.2给出 Windows x64 模型运行器 EXE 的构建和烟测范围，图中明确区分模型运行器验证与全应用离线包验收。", FIG / "fig5_2_exe_evidence.png", "图5.2　Windows x64 模型运行器 EXE 烟测")
    add_p(c5, "Windows x64 交付范围仅为模型运行器 EXE。GitHub Actions 运行 44996354530 构建出 PE32+ x86-64 文件，Release model-exe-6 中的烟测输入为 Tomato、30、95、10、900，输出标签为 Bad，风险概率 0.67811358，模型版本为 weighted-xgboost-mi-v1。项目没有把模型 EXE 扩展为全应用 Windows x64 离线包。")
    add_heading(c5, "5.4　限制与风险", 2)
    add_p(c5, "第一，数据没有时间戳，无法验证时间窗口、批次漂移和真实货架期；第二，公开数据集的标签分布和采集条件有限，不能代替现场传感器校准；第三，模型只进行一次固定分层切分，尚未完成多次随机种子、交叉验证和概率校准；第四，当前系统没有用户登录、权限和生产级审计；第五，HDFS 实测是 macOS 单节点伪分布式，不代表多节点集群吞吐；第六，Windows 只验证模型 EXE，不代表全应用离线部署。")
    add_p(c5, "此外，参考文献的最终准入还需要按照学校工作包逐条核对 CNKI/维普记录、出版年份、J/D 类型和正文论点支持；当前台账中仍有待核验条目，因此论文交付前不能把文献数量当作已经完全通过。签名、日期和企业指导教师字段也只在取得真实信息后填写。")

    # Conclusion section before references
    add_heading(c6, "结　　论", 1)
    add_p(c6, "本文围绕公开冷库传感器记录，完成了数据清洗、HDFS 文件链路、互信息特征工程、原始与加权 XGBoost 对比、Spring Boot 与 SQLite 后端、静态 Web 控制台以及风险预警联动。系统把记录字段、模型输入、预测结果和预警状态放在同一条可追溯链路中，自动化测试、API 联调、HDFS 实机运行和 Windows x64 模型运行器烟测均有仓库证据。")
    add_p(c6, "从工程实现看，项目形成了三个可以复核的接口：清洗脚本输出规范 CSV 和报告，模型运行器通过 JSON 与服务层交换数据，服务层通过 SQLite 保存输入、预测和预警。接口稳定后，页面能够在真实后端响应的基础上展示记录、风险和指标，避免了只做静态页面或只给出命令行结果的不足。")
    add_p(c6, "从实验结果看，互信息缩放改变了特征输入和部分错误结构，尤其把 Recall 提高到1.000000，但没有让所有指标同时变好。这个结论比“模型准确率很高”更具体，也与固定测试集、公开数据和单次切分的证据范围一致。")
    add_p(c6, "实验结果显示，互信息加权模型的 Recall 和 ROC-AUC 略高于基线，但 Accuracy、Precision、F1、MSE、MAE 和 R² 不优于基线。这个结果支持“加权策略改变了模型对特征的关注并改善了部分指标”的判断，不支持“加权策略全面提升性能”的判断。")
    add_p(c6, "后续工作应优先补充带时间戳和批次信息的真实冷库数据，建立按时间切分的测试方案；其次增加多随机种子、交叉验证、阈值分析和概率校准；再次增加用户权限、操作审计和模型回滚；最后在 Windows 环境完成全应用离线包、中文路径、断网和无预装 Python 场景的验收。")
    add_p(c6, "论文提交前还需要完成文献逐条核验、正式目录更新、签名日期填写和目标 Word 环境复核。若学校或指导教师对题名、字数、文献年份和图表格式有针对本专业或届次的正式要求，应在项目卡中记录并以对应材料为准；当前规范仓库的 v1.0 是工作依据，不替代未提供的正式校级通知。")

    # References section
    # The source template uses the last section-break paragraph for one
    # illustrative bibliography item. Keep that paragraph as the insertion
    # anchor, but clear the sample text before writing the real list.
    if cref.text.strip().startswith("[10]万锦坤"):
        clear_paragraph(cref)
    add_heading(cref, "参考文献", 1)
    add_p(cref, "本文正文使用上标方括号编号引用，同一文献重复引用时沿用原编号。以下条目按 J（期刊）和 D（学位论文）整理；其中 D 类和部分国际条目的 CNKI/维普收录状态仍需提交前逐条核验，当前文档作为按河北工职大论文 1.0 模板排版的项目说明书工作稿。", indent=False)
    for ref in references():
        p=add_p(cref, ref, indent=False)
        p.paragraph_format.left_indent = Cm(0)
        p.paragraph_format.first_line_indent = Cm(-0.74)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p.paragraph_format.line_spacing = Pt(16)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        for r in p.runs:
            set_run_font(r, "Times New Roman", 10.5)

    # Final section: acknowledgements and appendix. The final body sectPr is not a paragraph.
    final_sect = doc._body._element.sectPr
    # helper that inserts before final sectPr through a temporary paragraph
    def final_p(text="", style="Normal", indent=True):
        p=doc.add_paragraph()
        p._p.getparent().remove(p._p)
        final_sect.addprevious(p._p)
        p.style=style
        if text: add_cited_text(p,text)
        if style=="Normal": style_body(p,indent=indent)
        return p
    def final_heading(text,level=1):
        p=final_p("",f"Heading {level}",False); set_paragraph_text(p,text); p.alignment=WD_ALIGN_PARAGRAPH.CENTER if level==1 else WD_ALIGN_PARAGRAPH.JUSTIFY
        for r in p.runs: set_run_font(r, "Heiti SC", 15 if level == 1 else (14 if level == 2 else 13), bold=True)
        return p
    final_heading("致　　谢",1)
    final_p("本说明书的完成离不开指导教师在选题、方案设计、实验记录和论文修改过程中的指导。感谢指导教师对研究边界、工程实现和材料整理提出的建议。感谢开源数据集、Hadoop、XGBoost、Spring Boot 和 SQLite 社区提供的工具与资料。本文所有实验结果均以仓库中的代码、数据和证据文件为准，未将尚未核验的现场数据写入结论。")
    final_p("由于企业指导教师、签名和提交日期尚未由本人提供，封面和声明页保留空白栏位，待正式提交前补齐。", indent=False)
    final_p("", indent=False).add_run().add_break(WD_BREAK.PAGE)
    final_heading("附录A　复现实验与接口样例",1)
    final_p("A.1　主要复现实验命令",2)
    final_p("python3 pipeline/etl/clean_dataset.py\n.m09-worktrees/m09-model/.venv/bin/python -m unittest discover -s tests -v\nmvn -q -f backend/pom.xml test\nnode --check backend/src/main/resources/static/app.js\nHADOOP_CONF_DIR=.hadoop/conf HDFS_BIN=.../hdfs HDFS_ROOT=/m09/cold-storage hadoop/hdfs_ingest.sh", indent=False)
    final_p("A.2　模型输入输出样例",2)
    final_p('{"fruit":"Tomato","temp":30,"humid":95,"light":10,"co2":900}\n→ {"label":"Bad","riskProbability":0.67811358,"modelVersion":"weighted-xgboost-mi-v1"}', indent=False)
    final_p("A.3　交付证据索引",2)
    final_p("数据来源：evidence/data/dataset_source.json；模型指标：evidence/models/metrics.json；本机 API：evidence/runtime/api/local_integration.json；HDFS 实机：evidence/delivery/hadoop-real-run.json；Windows 模型 EXE：evidence/delivery/model-exe-windows.json；测试记录：evidence/tests/TEST_REPORT.md。", indent=False)

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE, OUT)
    OUT.chmod(0o644)
    doc = Document(OUT)
    doc.core_properties.author = "m09 project"
    doc.core_properties.last_modified_by = "m09 project"
    fill_front_matter(doc)
    replace_toc(doc)
    build_body(doc)
    enable_update_fields(doc)
    doc.save(OUT)
    source_urls = [
        "https://doi.org/10.1111/1750-3841.70871",
        "https://doi.org/10.1111/1750-3841.70945",
        "https://doi.org/10.1016/j.foodcont.2025.111174",
        "https://doi.org/10.1016/j.cej.2024.150739",
        "https://doi.org/10.7717/peerj-cs.2510",
        "https://doi.org/10.29207/resti.v8i1.5226",
        "https://doi.org/10.1016/j.foodcont.2023.109976",
        "https://doi.org/10.1016/j.tifs.2023.02.010",
        "https://doi.org/10.1016/j.jfoodeng.2023.111518",
        "https://doi.org/10.1016/j.crfs.2023.100656",
        "https://doi.org/10.32604/cmc.2023.043369",
        "https://doi.org/10.3390/s23167081",
        "https://doi.org/10.1214/aos/1013203451",
        "https://doi.org/10.1103/PhysRevE.69.066138",
        "https://hdl.handle.net/11581/484285",
        "https://livrepository.liverpool.ac.uk/3183538/",
        "https://doi.org/10.5075/epfl-thesis-10803",
        "https://researchportal.port.ac.uk/en/studentTheses/application-of-explainable-artificial-intelligence-and-generative/",
    ]
    ledger = {
        "profile": "河北工业职业技术大学规则草案.v1.0",
        "status": "publisher_metadata_checked_cnki_vip_pending",
        "note": "18 条文献均已按 J/D 类型整理并保留 DOI 或机构库入口；提交前仍需按学校工作包在 CNKI/维普逐条核对收录状态。",
        "references": [
            {"no": i + 1, "type": "J" if i < 14 else "D", "year": int(y), "verification": "publisher_or_institutional_repository_checked", "source": url}
            for i, (y, url) in enumerate(zip([2026, 2026, 2025, 2024, 2024, 2024, 2023, 2023, 2023, 2024, 2024, 2023, 2001, 2004, 2023, 2024, 2024, 2026], source_urls))
        ]
    }
    (ROOT / "thesis" / "文献核验台账.json").write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding="utf-8")
    print(OUT)

if __name__ == "__main__":
    main()
