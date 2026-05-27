---
name: gen-drawio
description: Generate draw.io diagrams as .drawio files, optionally export to PNG/SVG/PDF with embedded XML
allowed-tools: Bash, Write
---

## Purpose
Produce professional, editable draw.io diagrams from natural language descriptions — architecture, flowcharts, ER diagrams, CI/CD pipelines, infrastructure maps. Output is native `.drawio` XML (or exported PNG/SVG/PDF with embedded XML so the file stays editable).

## When to Use
Invoke whenever the user asks to visualize a system, flow, architecture, or process — even if they don't say "draw.io". Trigger phrases: "diagram", "visualize", "draw", "map out", "show me the flow", "architecture diagram", "flowchart". Prefer this over ASCII art or Mermaid when the user is in a desktop environment.

## Instructions

1. **Plan the layout** — identify the main flow or architecture; decide on visual grouping and spacing
2. **Identify icons needed** — cloud services (AWS/K8s/Docker/Azure/GCP), databases, CI/CD platforms → use icon libraries below
3. **Generate draw.io XML** in mxGraphModel format, following design principles
4. **Write the XML** to a `.drawio` file using the Write tool
5. **Validate the XML** — run `python3 -c "import xml.etree.ElementTree as ET; ET.parse('file.drawio'); print('Valid')"` — fix any errors before proceeding
6. **Export if requested** (png/svg/pdf) — use draw.io CLI with `--embed-diagram`, then delete the source `.drawio` file
7. **Open the result** — `xdg-open` (Linux), `open` (macOS), `start` (Windows)

---

## Design principles

1. **Clarity first** — each element immediately understandable; ambiguity is worse than missing detail
2. **Essential information only** — omit implementation details, verbose labels, tangential components
3. **Generous whitespace** — prefer wider layouts over dense ones; cramped diagrams are unreadable
4. **Purposeful color** — color indicates category/state/relationship, not decoration; max 4-5 distinct colors
5. **Icon-based** — use AWS/K8s/Docker icons whenever available; they communicate faster than text
6. **At-a-glance** — the diagram should make sense in 5 seconds without reading every label

## Spacing and layout

**Element sizing:** icons 60–100px · text labels 12–14pt · containers leave ≥50px internal padding

**Spacing:** horizontal ≥40px · vertical ≥60px · between groups ≥100px

**Layout strategies:**
- Linear flow (pipelines, sequences): horizontal/vertical chain with consistent spacing
- Hierarchical (architecture): top-to-bottom, swimlanes for environments/regions
- Clustered (microservices): group by function/team, containers, critical paths only
- Avoid: diagonal connections, overlapping elements, dense clusters

**Color palette:**
- Background: `#f5f5f5` / `#ffffff` / `#f0f4ff`
- AWS: `#FF9900` orange family
- Kubernetes: `#326CE5` blue family
- Docker: `#2496ED`
- External/user: `#4CAF50` green or `#9C27B0` purple
- Error/failure: `#E74C3C` · Healthy/success: `#27AE60`

## mxGraphModel setup

Always use this base (grid off, full workspace, shadows on elements):

```xml
<mxGraphModel dx="1200" dy="800" grid="0" gridSize="0" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2800" pageHeight="1600">
```

**Page size presets:**

| Size | pageWidth | pageHeight | Good for |
|---|---|---|---|
| Small (A4 landscape) | 1169 | 827 | Simple flowcharts |
| Medium (A3 landscape) | 1587 | 1123 | Moderate architecture |
| Large | 2800 | 1600 | Detailed multi-section |
| Extra large | 3600 | 2400 | Full infrastructure |

Estimate content area first, pick next size up, add ~20% margin.

## XML structure

```xml
<mxGraphModel dx="1200" dy="800" grid="0" gridSize="0" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2800" pageHeight="1600">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <mxCell id="2" value="Example" style="rounded=1;shadow=1;" vertex="1" parent="1">
      <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

- `id="0"` = root layer · `id="1"` = default parent layer
- All elements use `parent="1"` unless inside a container
- Add `shadow=1` to individual element styles for depth

## Containers and swimlanes

```xml
<mxCell id="region" value="Region Name" style="swimlane;startSize=36;fillColor=#f0f4ff;strokeColor=#1976d2;collapsible=0;" vertex="1" parent="1">
  <mxGeometry x="40" y="40" width="800" height="600" as="geometry"/>
</mxCell>
<mxCell id="child" value="Service" style="rounded=1;" vertex="1" parent="region">
  <mxGeometry x="20" y="50" width="120" height="60" as="geometry"/>
</mxCell>
```

Child x/y coords are **relative to the container**. Use `collapsible=0` always.

## Cross-container edges — most common failure point

When connecting cells in **different** containers, the edge **must** use `parent="1"`, not either container:

```xml
<mxCell id="edge" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="cellInA" target="cellInB" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

Edges between cells in the **same** container can use that container as parent.

## Common styles

| Shape | Style |
|---|---|
| Rounded rect | `rounded=1;whiteSpace=wrap;shadow=1;` |
| Diamond | `rhombus;whiteSpace=wrap;` |
| Cylinder (DB) | `shape=cylinder3;whiteSpace=wrap;` |
| Orthogonal edge | `edgeStyle=orthogonalEdgeStyle;` |
| Dashed edge | `edgeStyle=orthogonalEdgeStyle;dashed=1;` |
| Swimlane | `swimlane;startSize=36;collapsible=0;` |

## Icon libraries

### AWS (`mxgraph.aws4.*`)
```xml
<mxCell value="EC2"      style="shape=mxgraph.aws4.ec2;"                      vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="RDS"      style="shape=mxgraph.aws4.rds_database;"              vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="Lambda"   style="shape=mxgraph.aws4.lambda;"                    vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="S3"       style="shape=mxgraph.aws4.s3;"                        vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="ALB"      style="shape=mxgraph.aws4.elastic_load_balancing;"    vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
```

### Kubernetes (`mxgraph.kubernetes.*`)
```xml
<mxCell value="Pod"        style="shape=mxgraph.kubernetes.pod;"        vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="Deployment" style="shape=mxgraph.kubernetes.deployment;" vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="Service"    style="shape=mxgraph.kubernetes.service;"    vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="Ingress"    style="shape=mxgraph.kubernetes.ingress;"    vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="Cluster"    style="shape=mxgraph.kubernetes.cluster;"    vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
```

### Docker (`mxgraph.docker.*`)
```xml
<mxCell value="Container" style="shape=mxgraph.docker.container;" vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="Image"     style="shape=mxgraph.docker.image;"     vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
<mxCell value="Registry"  style="shape=mxgraph.docker.registry;"  vertex="1" parent="1"><mxGeometry width="80" height="80" as="geometry"/></mxCell>
```

### Other libraries
- **Azure**: `mxgraph.azure.<resource>` (vm, sql_database, app_service…)
- **GCP**: `mxgraph.gcp.<resource>` (compute_engine, cloud_storage…)
- **Databases**: `mxgraph.databases.<type>` (mysql, postgresql, mongodb…)
- **Flowchart**: `mxgraph.flowchart.<shape>` (document, process, decision…)

Icon sizing: 60–100px square · `fillColor` usually ignored by icon shapes · set `fontSize` + `fontColor` for labels

## Output format

| Format | Embed XML | Notes |
|---|---|---|
| `.drawio` | — | Default; editable directly |
| `png` | Yes (`-e`) | Viewable everywhere, editable in draw.io |
| `svg` | Yes (`-e`) | Scalable, editable in draw.io |
| `pdf` | Yes (`-e`) | Printable, editable in draw.io |

Parse user request: `/drawio png flowchart` → `flowchart.drawio.png` · `/drawio svg: ER` → `er-diagram.drawio.svg` · no format → `.drawio` file

## draw.io CLI export

```bash
drawio -x -f <format> -e -b 10 -o <output> <input.drawio>
```

Find CLI: try `which drawio` first · macOS: `/Applications/draw.io.app/Contents/MacOS/draw.io` · Linux: `drawio` (snap/apt/flatpak)

After successful export: delete the source `.drawio` file (exported file contains full XML).

## File naming

`lowercase-with-hyphens.drawio` · exports: `name.drawio.png` (double extension signals embedded XML)

## CRITICAL: XML well-formedness

- **No XML comments** — `<!-- -->` with `--` causes parse errors; draw.io ignores them anyway; use descriptive `id` values instead
- Escape in attribute values: `&amp;` `&lt;` `&gt;` `&quot;`
- All `id` values must be unique
- **Always validate** before opening: `python3 -c "import xml.etree.ElementTree as ET; ET.parse('file.drawio'); print('Valid')"`

## Learnings

### Uncertain icon paths (2026-05-27)
- Condition: `mxgraph.infographic.jenkins`, `mxgraph.infographic.github` — paths not from official docs; may render as blank boxes
- Impact: silent failure — diagram opens but icon is invisible
- Recovery: fall back to styled rounded rectangle with text label; log the failed path here when confirmed broken

### CLI export on Linux snap install (2026-05-27)
- Condition: `drawio` (snap) fails with "not a snap cgroup" when called from a non-snap shell (e.g. Claude Code terminal)
- Fix: call the binary directly — `/snap/drawio/current/drawio --no-sandbox -x -f png -e -b 20 -o out.png in.drawio`
- dbus errors in stderr are harmless; check exit code and output file existence instead
- `xdg-open file.drawio` opens the editor, not a rendered image — always export to PNG/SVG first if you want a visual