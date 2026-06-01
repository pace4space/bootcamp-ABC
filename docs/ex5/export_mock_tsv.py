#!/usr/bin/env python3
"""Self-contained TSV export for TensorFlow Embedding Projector.

No running Postgres, no Bedrock credentials needed.
Uses MockEmbeddingClient (sha256-seeded unit-norm vectors — same implementation
as the automated test suite) to generate 512-dim vectors for a representative
set of candidates and positions.

Writes two line-aligned files (Projector format):
  docs/ex5/vectors.tsv   — one row per record, 512 tab-separated floats, no header
  docs/ex5/metadata.tsv  — header + one row per record (id, kind, label, secondary, top_terms)

Usage (no docker, no venv needed — only stdlib + no external deps):
  python3 docs/ex5/export_mock_tsv.py

To use real Titan v2 embeddings from a running Postgres instead, run:
  docker compose up -d db
  cd api && .venv/bin/python -m alembic upgrade head
  .venv/bin/python ../docs/ex5/backfill.py
  .venv/bin/python ../docs/ex5/export_embeddings.py
"""
import hashlib
import math
import random
import sys
from pathlib import Path

_OUT_DIR = Path(__file__).parent


# ── MockEmbeddingClient (mirrors api/tests/embeddings/conftest.py exactly) ────

def mock_embed(text: str) -> list[float]:
    """sha256-seeded unit-norm vector, 512-dim. Same as test suite."""
    seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    v = [rng.uniform(-1, 1) for _ in range(512)]
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


# ── Embedding texts (output of build_candidate_text / build_position_text) ─────
# These mirror what the real text builders produce for a representative HR dataset.

CANDIDATES = [
    {
        "id": "cv_001", "full_name": "Alice Chen", "headline": "Senior DevOps Engineer",
        "top_skills": "Kubernetes, Terraform, AWS EKS, Docker, CI/CD",
        "text": (
            "Role: Senior DevOps Engineer\n"
            "Summary: Platform engineer with 7 years building Kubernetes-based infrastructure on AWS.\n"
            "Skills: Kubernetes, Terraform, AWS EKS, Docker, CI/CD, Helm\n"
            "Experience:\n"
            "- Platform Lead at CloudCo (2020–present)\n"
            "- DevOps Engineer at FinTech Inc (2017–2020)\n"
            "Languages: English, Hebrew"
        ),
    },
    {
        "id": "cv_002", "full_name": "Bob Levy", "headline": "DevOps Engineer",
        "top_skills": "Terraform, Ansible, AWS, Jenkins, Linux",
        "text": (
            "Role: DevOps Engineer\n"
            "Summary: Infrastructure automation specialist with strong Ansible and Terraform skills.\n"
            "Skills: Terraform, Ansible, AWS, Jenkins, Linux, Bash\n"
            "Experience:\n"
            "- DevOps Engineer at StartupX (2021–present)\n"
            "Languages: English"
        ),
    },
    {
        "id": "cv_003", "full_name": "Carol Singh", "headline": "Senior Frontend Developer",
        "top_skills": "React, TypeScript, Tailwind CSS, Next.js, Figma",
        "text": (
            "Role: Senior Frontend Developer\n"
            "Summary: React and TypeScript specialist, 6 years building design systems and SPAs.\n"
            "Skills: React, TypeScript, Tailwind CSS, Next.js, Figma, Storybook\n"
            "Experience:\n"
            "- Frontend Lead at DesignCo (2019–present)\n"
            "- UI Developer at AgencyAB (2018–2019)\n"
            "Languages: English, French"
        ),
    },
    {
        "id": "cv_004", "full_name": "David Park", "headline": "Full-Stack Engineer",
        "top_skills": "React, Node.js, PostgreSQL, GraphQL, Docker",
        "text": (
            "Role: Full-Stack Engineer\n"
            "Summary: Node.js and React developer building scalable SaaS products.\n"
            "Skills: React, Node.js, PostgreSQL, GraphQL, Docker, TypeScript\n"
            "Experience:\n"
            "- Senior Engineer at SaaSCo (2020–present)\n"
            "Languages: English, Korean"
        ),
    },
    {
        "id": "cv_005", "full_name": "Eva Müller", "headline": "Junior DevOps Engineer",
        "top_skills": "Docker, Kubernetes, GitHub Actions, Python, Bash",
        "text": (
            "Role: Junior DevOps Engineer\n"
            "Summary: Recent graduate learning container orchestration and CI/CD automation.\n"
            "Skills: Docker, Kubernetes, GitHub Actions, Python, Bash\n"
            "Experience:\n"
            "- DevOps Intern at CloudCo (2023–2024)\n"
            "Languages: English, German"
        ),
    },
    {
        "id": "cv_006", "full_name": "Frank Liu", "headline": "Senior Data Engineer",
        "top_skills": "Apache Spark, Airflow, BigQuery, Python, dbt",
        "text": (
            "Role: Senior Data Engineer\n"
            "Summary: Building large-scale ETL pipelines on GCP with Spark and Airflow.\n"
            "Skills: Apache Spark, Airflow, BigQuery, Python, dbt, SQL\n"
            "Experience:\n"
            "- Data Engineer at DataCo (2021–present)\n"
            "- Analytics Engineer at RetailX (2019–2021)\n"
            "Languages: English, Mandarin"
        ),
    },
    {
        "id": "cv_007", "full_name": "Grace Teller", "headline": "Machine Learning Engineer",
        "top_skills": "PyTorch, MLflow, Kubernetes, Python, scikit-learn",
        "text": (
            "Role: Machine Learning Engineer\n"
            "Summary: Deep learning and MLOps practitioner, model training and deployment at scale.\n"
            "Skills: PyTorch, MLflow, Kubernetes, Python, scikit-learn, ONNX\n"
            "Experience:\n"
            "- ML Engineer at AILab (2022–present)\n"
            "- Research Intern at UniversityX (2021–2022)\n"
            "Languages: English"
        ),
    },
    {
        "id": "cv_008", "full_name": "Hannah Weiss", "headline": "Backend Engineer",
        "top_skills": "FastAPI, Python, PostgreSQL, Redis, Docker",
        "text": (
            "Role: Backend Engineer\n"
            "Summary: Python backend developer specialising in high-throughput REST APIs.\n"
            "Skills: FastAPI, Python, PostgreSQL, Redis, Docker, asyncio\n"
            "Experience:\n"
            "- Backend Engineer at APIco (2022–present)\n"
            "Languages: English, Hebrew"
        ),
    },
    {
        "id": "cv_009", "full_name": "Ivan Sorin", "headline": "Site Reliability Engineer",
        "top_skills": "Kubernetes, Prometheus, Grafana, Terraform, PagerDuty",
        "text": (
            "Role: Site Reliability Engineer\n"
            "Summary: SRE focused on observability, on-call runbooks, and chaos engineering.\n"
            "Skills: Kubernetes, Prometheus, Grafana, Terraform, PagerDuty, Go\n"
            "Experience:\n"
            "- SRE at BigTechCo (2020–present)\n"
            "Languages: English, Romanian"
        ),
    },
]

POSITIONS = [
    {
        "id": "pos_001", "title": "Senior Platform Engineer", "seniority": "Senior",
        "top_terms": "Kubernetes, Terraform, AWS",
        "text": (
            "Title: Senior Platform Engineer\n"
            "Seniority: Senior\n"
            "Description: Design and operate Kubernetes-based infrastructure on AWS EKS at scale.\n"
            "Must-have: Kubernetes, Terraform, AWS EKS\n"
            "Nice-to-have: Prometheus, Helm, ArgoCD"
        ),
    },
    {
        "id": "pos_002", "title": "DevOps Engineer", "seniority": "Mid",
        "top_terms": "Docker, CI/CD, Linux",
        "text": (
            "Title: DevOps Engineer\n"
            "Seniority: Mid\n"
            "Description: Automate infrastructure and CI/CD pipelines for a growing SaaS platform.\n"
            "Must-have: Docker, CI/CD, Linux, Bash\n"
            "Nice-to-have: Ansible, Terraform, Kubernetes"
        ),
    },
    {
        "id": "pos_003", "title": "Frontend Engineer", "seniority": "Mid",
        "top_terms": "React, TypeScript, Tailwind CSS",
        "text": (
            "Title: Frontend Engineer\n"
            "Seniority: Mid\n"
            "Description: Build React component libraries and integrate with a design system.\n"
            "Must-have: React, TypeScript\n"
            "Nice-to-have: Next.js, Tailwind CSS, Storybook"
        ),
    },
    {
        "id": "pos_004", "title": "Senior Data Engineer", "seniority": "Senior",
        "top_terms": "Apache Spark, Airflow, SQL",
        "text": (
            "Title: Senior Data Engineer\n"
            "Seniority: Senior\n"
            "Description: Design and maintain petabyte-scale data pipelines on GCP.\n"
            "Must-have: Apache Spark, Airflow, SQL\n"
            "Nice-to-have: dbt, BigQuery, Kafka"
        ),
    },
    {
        "id": "pos_005", "title": "ML Platform Engineer", "seniority": "Senior",
        "top_terms": "Kubernetes, Python, MLOps",
        "text": (
            "Title: ML Platform Engineer\n"
            "Seniority: Senior\n"
            "Description: Build ML infrastructure and MLOps tooling for production model serving.\n"
            "Must-have: Kubernetes, Python, MLOps tooling\n"
            "Nice-to-have: PyTorch, MLflow, Kubeflow"
        ),
    },
    {
        "id": "pos_006", "title": "Backend Python Engineer", "seniority": "Mid",
        "top_terms": "Python, PostgreSQL, FastAPI",
        "text": (
            "Title: Backend Python Engineer\n"
            "Seniority: Mid\n"
            "Description: Build scalable REST APIs for a fintech platform using FastAPI and Postgres.\n"
            "Must-have: Python, PostgreSQL, REST APIs\n"
            "Nice-to-have: FastAPI, Redis, asyncio"
        ),
    },
    {
        "id": "pos_007", "title": "Site Reliability Engineer", "seniority": "Senior",
        "top_terms": "Kubernetes, Prometheus, Terraform",
        "text": (
            "Title: Site Reliability Engineer\n"
            "Seniority: Senior\n"
            "Description: Own reliability and observability for a high-traffic distributed system.\n"
            "Must-have: Kubernetes, Prometheus, Terraform\n"
            "Nice-to-have: Grafana, PagerDuty, Go"
        ),
    },
]


def main() -> None:
    records: list[tuple[str, str, str, str, str, list[float]]] = []

    for c in CANDIDATES:
        vec = mock_embed(c["text"])
        records.append((c["id"], "candidate", c["full_name"], c["headline"], c["top_skills"], vec))

    for p in POSITIONS:
        vec = mock_embed(p["text"])
        records.append((p["id"], "position", p["title"], p["seniority"], p["top_terms"], vec))

    vectors_path = _OUT_DIR / "vectors.tsv"
    metadata_path = _OUT_DIR / "metadata.tsv"

    # vectors.tsv — no header, one row per record
    with vectors_path.open("w", encoding="utf-8") as fv:
        for *_, vec in records:
            fv.write("\t".join(f"{v:.8f}" for v in vec) + "\n")

    # metadata.tsv — header + data rows
    with metadata_path.open("w", encoding="utf-8") as fm:
        fm.write("id\tkind\tlabel\tsecondary\ttop_terms\n")
        for id_, kind, label, secondary, top_terms, _ in records:
            fm.write(f"{id_}\t{kind}\t{label}\t{secondary}\t{top_terms}\n")

    n = len(records)
    n_cand = sum(1 for r in records if r[1] == "candidate")
    n_pos  = sum(1 for r in records if r[1] == "position")

    print(f"Exported {n} rows ({n_cand} candidates, {n_pos} positions)")
    print(f"  vectors.tsv  → {vectors_path}  ({vectors_path.stat().st_size:,} bytes)")
    print(f"  metadata.tsv → {metadata_path}  ({metadata_path.stat().st_size:,} bytes)")
    print()
    print("Load in TF Projector:")
    print("  1. Open https://projector.tensorflow.org")
    print("  2. Click 'Load' → upload vectors.tsv (no header), then metadata.tsv")
    print("  3. Switch projection to UMAP, color by 'kind'")
    print()
    print("NOTE: mock vectors are sha256-seeded (same as test suite), not semantic.")
    print("Run backfill.py + export_embeddings.py with live Bedrock for real clusters.")

    # Sanity check
    v_lines = len(vectors_path.read_text().strip().splitlines())
    m_lines = len(metadata_path.read_text().strip().splitlines()) - 1  # minus header
    assert v_lines == m_lines == n, f"Line count mismatch: vectors={v_lines} metadata={m_lines} records={n}"
    print(f"\n✓ Line alignment verified: {n} rows in both files.")


if __name__ == "__main__":
    main()
