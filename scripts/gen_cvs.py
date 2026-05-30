"""Generate 3 realistic fake CV PDFs for Hellio HR demo / testing."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from pathlib import Path

OUT = Path(__file__).parent.parent / "CVsJobs" / "cvs"
OUT.mkdir(parents=True, exist_ok=True)

ACCENT = colors.HexColor("#4338CA")   # indigo-700

def make_styles():
    base = getSampleStyleSheet()
    return {
        "name":    ParagraphStyle("name",    fontSize=20, leading=24, textColor=ACCENT, spaceAfter=2),
        "tagline": ParagraphStyle("tagline", fontSize=11, leading=14, textColor=colors.grey, spaceAfter=12),
        "section": ParagraphStyle("section", fontSize=10, leading=13, textColor=ACCENT,
                                  fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4),
        "body":    ParagraphStyle("body",    fontSize=9,  leading=13),
        "bold":    ParagraphStyle("bold",    fontSize=9,  leading=13, fontName="Helvetica-Bold"),
        "bullet":  ParagraphStyle("bullet",  fontSize=9,  leading=13, leftIndent=12, bulletIndent=0),
    }

def rule(): return HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4)

def section(title, s): return [Paragraph(title.upper(), s["section"]), rule()]

def build(filename: str, blocks):
    path = OUT / filename
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    doc.build(blocks)
    print(f"  wrote {path}")


# ─────────────────────────────────────────────────────────────────────────────
# CV 1 — Noa Shapiro, ML Engineer
# ─────────────────────────────────────────────────────────────────────────────
def cv_noa():
    s = make_styles()
    b = []
    b += [Paragraph("Noa Shapiro", s["name"])]
    b += [Paragraph("Machine Learning Engineer · Tel Aviv", s["tagline"])]
    b += [Paragraph("noa.shapiro@gmail.com  |  050-3344556  |  https://linkedin.com/in/noa-shapiro  |  https://github.com/noashapiro", s["body"])]
    b += [Spacer(1, 6)]

    b += section("Summary", s)
    b += [Paragraph("ML engineer with 6 years of experience building production-grade recommendation and NLP systems at scale. "
                    "Comfortable across the full ML lifecycle: data pipelines, model training, evaluation, and serving. "
                    "Strong Python, PyTorch, and AWS background.", s["body"])]

    b += section("Experience", s)
    for role, co, years, bullets in [
        ("Senior ML Engineer", "Walla! Communications", "2021–Present", [
            "Led rebuild of article recommendation engine — CTR +18%.",
            "Deployed BERT-based topic classifier serving 40M requests/day on SageMaker.",
            "Reduced inference latency 40% via quantisation and ONNX export.",
        ]),
        ("ML Engineer", "IronSource (Unity)", "2018–2021", [
            "Built bidding prediction models for programmatic ad platform.",
            "Maintained feature store serving 200+ real-time features to 12 ML models.",
        ]),
        ("Data Scientist", "Startup — Stealth Mode", "2017–2018", [
            "Exploratory NLP research on Hebrew social-media text.",
        ]),
    ]:
        b += [Paragraph(f"<b>{role}</b> — {co} <font color='grey'>({years})</font>", s["body"])]
        for bl in bullets:
            b += [Paragraph(f"• {bl}", s["bullet"])]
        b += [Spacer(1, 4)]

    b += section("Skills", s)
    b += [Paragraph("Python · PyTorch · TensorFlow · SageMaker · Spark · Kafka · SQL · Docker · Kubernetes · Hebrew NLP", s["body"])]

    b += section("Education", s)
    b += [Paragraph("<b>M.Sc. Computer Science (Machine Learning)</b> — Technion, 2017", s["body"])]
    b += [Paragraph("<b>B.Sc. Mathematics &amp; Computer Science</b> — Hebrew University, 2015", s["body"])]

    b += section("Certifications", s)
    b += [Paragraph("AWS Certified Machine Learning Specialty (2022)", s["body"])]

    build("cv_noa_shapiro.pdf", b)


# ─────────────────────────────────────────────────────────────────────────────
# CV 2 — Daniel Peretz, Full-Stack Engineer
# ─────────────────────────────────────────────────────────────────────────────
def cv_daniel():
    s = make_styles()
    b = []
    b += [Paragraph("Daniel Peretz", s["name"])]
    b += [Paragraph("Full-Stack Engineer · Herzliya", s["tagline"])]
    b += [Paragraph("daniel.peretz@outlook.com  |  052-7788990  |  https://linkedin.com/in/daniel-peretz-dev  |  https://github.com/dperetz", s["body"])]
    b += [Spacer(1, 6)]

    b += section("Summary", s)
    b += [Paragraph("Full-stack engineer with 8 years shipping consumer and B2B products. "
                    "Product-minded, opinionated about developer experience, and comfortable in TypeScript/React "
                    "on the front end and Python/Node on the back end. Led teams of up to 5 engineers.", s["body"])]

    b += section("Experience", s)
    for role, co, years, bullets in [
        ("Staff Engineer", "Lemonade", "2020–Present", [
            "Architected micro-frontend platform adopted across 4 product teams.",
            "Drove migration from REST to GraphQL — reduced over-fetching 60%.",
            "Mentored 3 engineers to senior level.",
        ]),
        ("Senior Full-Stack Engineer", "Fiverr", "2017–2020", [
            "Built seller analytics dashboard (React + D3, 500k DAU).",
            "Implemented A/B testing infrastructure integrated with feature flags.",
        ]),
        ("Frontend Engineer", "Zap Group", "2016–2017", [
            "Rewrote product comparison tool in React, replacing legacy jQuery.",
        ]),
    ]:
        b += [Paragraph(f"<b>{role}</b> — {co} <font color='grey'>({years})</font>", s["body"])]
        for bl in bullets:
            b += [Paragraph(f"• {bl}", s["bullet"])]
        b += [Spacer(1, 4)]

    b += section("Skills", s)
    b += [Paragraph("TypeScript · React · Next.js · Node.js · Python · GraphQL · PostgreSQL · Redis · AWS · Terraform", s["body"])]

    b += section("Education", s)
    b += [Paragraph("<b>B.Sc. Software Engineering</b> — Bar-Ilan University, 2012–2016", s["body"])]

    b += section("Languages", s)
    b += [Paragraph("Hebrew (native) · English (fluent) · French (conversational)", s["body"])]

    build("cv_daniel_peretz.pdf", b)


# ─────────────────────────────────────────────────────────────────────────────
# CV 3 — Maya Cohen, DevOps / Platform Engineer
# ─────────────────────────────────────────────────────────────────────────────
def cv_maya():
    s = make_styles()
    b = []
    b += [Paragraph("Maya Cohen", s["name"])]
    b += [Paragraph("Platform Engineer · Ramat Gan", s["tagline"])]
    b += [Paragraph("maya.cohen@proton.me  |  054-1122334  |  https://linkedin.com/in/maya-cohen-platform  |  https://github.com/mayacohen", s["body"])]
    b += [Spacer(1, 6)]

    b += section("Summary", s)
    b += [Paragraph("Platform engineer specialising in cloud-native infrastructure, CI/CD, and developer productivity. "
                    "Built internal developer platforms at two fintech companies. "
                    "Strong Kubernetes, Terraform, and observability background. CKA certified.", s["body"])]

    b += section("Experience", s)
    for role, co, years, bullets in [
        ("Lead Platform Engineer", "Payoneer", "2022–Present", [
            "Designed multi-tenant EKS platform serving 60+ microservices across 3 regions.",
            "Built GitOps deployment pipeline (ArgoCD) cutting release cycle from 2 days to 2 hours.",
            "Owned observability stack: Prometheus, Grafana, Loki, PagerDuty.",
        ]),
        ("DevOps Engineer", "Rapyd", "2019–2022", [
            "Managed Terraform for 15 AWS accounts; introduced Atlantis for PR-driven plans.",
            "Automated container security scanning into CI — reduced critical CVEs by 70%.",
        ]),
        ("Systems Engineer", "Rafael Advanced Defense Systems", "2016–2019", [
            "Maintained on-prem Linux cluster for simulation workloads.",
            "Automated deployment scripts (Ansible), reducing manual config time 80%.",
        ]),
    ]:
        b += [Paragraph(f"<b>{role}</b> — {co} <font color='grey'>({years})</font>", s["body"])]
        for bl in bullets:
            b += [Paragraph(f"• {bl}", s["bullet"])]
        b += [Spacer(1, 4)]

    b += section("Skills", s)
    b += [Paragraph("Kubernetes · Terraform · AWS · ArgoCD · Helm · Prometheus · Grafana · Python · Bash · Linux", s["body"])]

    b += section("Education", s)
    b += [Paragraph("<b>B.Sc. Information Systems Engineering</b> — Ben-Gurion University, 2012–2016", s["body"])]

    b += section("Certifications", s)
    b += [Paragraph("Certified Kubernetes Administrator (CKA, 2021)", s["body"])]
    b += [Paragraph("AWS Solutions Architect Associate (2020)", s["body"])]

    build("cv_maya_cohen.pdf", b)


if __name__ == "__main__":
    print("Generating CVs...")
    cv_noa()
    cv_daniel()
    cv_maya()
    print("Done.")
