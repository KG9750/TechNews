#!/usr/bin/env python3
"""Generate the bilingual architecture review HTML UI."""

from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def output_path() -> Path:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    safe_stamp = stamp.replace(":", "-")
    tmpdir = Path(os.environ.get("TMPDIR") or "/tmp")
    return tmpdir / f"architecture-review-bilingual-{safe_stamp}.html"


def html() -> str:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"""<!doctype html>
<html lang="en" class="lang-en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TechNews Briefing Architecture Review</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      :root {{
        --ink: #1f2937;
        --paper: #f8fafc;
        --line: #cbd5e1;
        --green: #047857;
        --amber: #b45309;
        --red: #b91c1c;
      }}
      body {{ background: var(--paper); color: var(--ink); }}
      .lang-en [data-lang="zh"], .lang-zh [data-lang="en"] {{ display: none !important; }}
      .lang-button {{ border: 1px solid var(--line); background: #ffffff; color: #475569; }}
      .lang-en #lang-en, .lang-zh #lang-zh {{ background: #1f2937; color: #f8fafc; border-color: #1f2937; }}
      .module-box {{ border: 1px solid var(--line); background: #ffffff; }}
      .deep-module {{ background: #1f2937; color: #f8fafc; }}
      .seam {{ border-top: 2px dashed #64748b; }}
      .leak {{ color: var(--red); }}
      .rule {{ border-color: var(--line); }}
    </style>
  </head>
  <body class="antialiased">
    <main class="mx-auto max-w-6xl px-5 py-8 sm:px-8 lg:py-12">
      <header class="mb-10 grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
        <div class="space-y-4">
          <div class="flex flex-wrap gap-2 text-xs uppercase tracking-wider text-slate-500">
            <span data-lang="en">Architecture Review</span>
            <span data-lang="zh">架构审查</span>
            <span>/</span>
            <span>{generated_at}</span>
          </div>
          <div>
            <h1 class="text-4xl font-semibold tracking-normal sm:text-5xl">TechNews Briefing</h1>
            <p class="mt-3 max-w-2xl text-base leading-7 text-slate-600" data-lang="en">
              A bilingual review UI for the current pre-development architecture and the implementation work now added to the repo.
            </p>
            <p class="mt-3 max-w-2xl text-base leading-7 text-slate-600" data-lang="zh">
              这是一份中英可切换的架构审查 UI，用来说明当前预开发架构状态，以及这次已经落到仓库里的优化工作。
            </p>
          </div>
        </div>
        <div class="flex rounded-md border border-slate-300 bg-white p-1 shadow-sm" aria-label="Language switcher">
          <button id="lang-en" class="lang-button rounded px-4 py-2 text-sm font-semibold" type="button">EN</button>
          <button id="lang-zh" class="lang-button rounded px-4 py-2 text-sm font-semibold" type="button">中文</button>
        </div>
      </header>

      <section class="mb-8 grid gap-4 lg:grid-cols-5">
        <div class="module-box rounded-lg p-4 lg:col-span-2">
          <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">Current State</p>
          <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">当前状态</p>
          <p class="mt-3 text-2xl font-semibold" data-lang="en">Live evidence complete; final gate pending.</p>
          <p class="mt-3 text-2xl font-semibold" data-lang="zh">Live evidence 已完成，最终 gate 待跑。</p>
        </div>
        <div class="module-box rounded-lg p-4">
          <p class="text-sm text-slate-500" data-lang="en">Production-enabled sources</p>
          <p class="text-sm text-slate-500" data-lang="zh">可生产自动摄入来源</p>
          <p class="mt-2 text-3xl font-semibold text-emerald-700">7</p>
        </div>
        <div class="module-box rounded-lg p-4">
          <p class="text-sm text-slate-500" data-lang="en">Deferred sources</p>
          <p class="text-sm text-slate-500" data-lang="zh">MVP 延后来源</p>
          <p class="mt-2 text-3xl font-semibold text-slate-800">25</p>
        </div>
        <div class="module-box rounded-lg p-4">
          <p class="text-sm text-slate-500" data-lang="en">MVP issues guarded</p>
          <p class="text-sm text-slate-500" data-lang="zh">受保护的 MVP Issues</p>
          <p class="mt-2 text-3xl font-semibold text-slate-800">11</p>
        </div>
      </section>

      <section class="mb-10 rounded-lg border border-amber-300 bg-amber-50 p-5">
        <p class="font-semibold text-amber-900" data-lang="en">Readiness gate remains intact.</p>
        <p class="font-semibold text-amber-900" data-lang="zh">Readiness gate 仍然保持有效。</p>
        <p class="mt-2 text-sm leading-6 text-amber-950" data-lang="en">
          The repo now has foundational modules and live evidence. The remaining readiness closure is the clean-worktree manifest plus final local and GitHub gates.
        </p>
        <p class="mt-2 text-sm leading-6 text-amber-950" data-lang="zh">
          仓库现在已经加入基础 Module，live evidence 也已完成。剩余收口点是 clean worktree manifest，以及最终本地和 GitHub gates。
        </p>
      </section>

      <section class="space-y-8">
        {candidate_contracts()}
        {candidate_source_policy()}
        {candidate_spike_adapters()}
        {candidate_run()}
        {candidate_tests()}
      </section>

      <section class="mt-10 rounded-lg border border-emerald-300 bg-emerald-50 p-6">
        <p class="text-xs uppercase tracking-wider text-emerald-800" data-lang="en">Top recommendation</p>
        <p class="text-xs uppercase tracking-wider text-emerald-800" data-lang="zh">首要建议</p>
        <p class="mt-3 text-xl font-semibold text-emerald-950" data-lang="en">
          Keep building from the Contract Module outward: it is now the highest-leverage seam for fixtures, tests, and future product code.
        </p>
        <p class="mt-3 text-xl font-semibold text-emerald-950" data-lang="zh">
          后续继续从 Contract Module 向外推进：它现在是 fixtures、测试和未来产品代码最有杠杆的 seam。
        </p>
      </section>
    </main>

    <script>
      const root = document.documentElement;
      function setLang(lang) {{
        root.classList.toggle("lang-en", lang === "en");
        root.classList.toggle("lang-zh", lang === "zh");
        root.lang = lang === "zh" ? "zh-CN" : "en";
        localStorage.setItem("technews-review-lang", lang);
      }}
      document.getElementById("lang-en").addEventListener("click", () => setLang("en"));
      document.getElementById("lang-zh").addEventListener("click", () => setLang("zh"));
      setLang(localStorage.getItem("technews-review-lang") || "en");
    </script>
  </body>
</html>
"""


def badge(strength_en: str, strength_zh: str, tone: str) -> str:
    colors = {
        "strong": "border-emerald-300 bg-emerald-50 text-emerald-800",
        "worth": "border-amber-300 bg-amber-50 text-amber-800",
    }
    return f"""
      <span class="rounded border px-2 py-1 text-xs font-semibold {colors[tone]}" data-lang="en">{strength_en}</span>
      <span class="rounded border px-2 py-1 text-xs font-semibold {colors[tone]}" data-lang="zh">{strength_zh}</span>
    """


def card(title_en: str, title_zh: str, files: str, body: str, strength_en: str, strength_zh: str, tone: str) -> str:
    return f"""
      <article class="module-box rounded-lg p-6 shadow-sm">
        <div class="flex flex-wrap items-start gap-3">
          <div class="flex-1">
            <h2 class="text-2xl font-semibold tracking-normal" data-lang="en">{title_en}</h2>
            <h2 class="text-2xl font-semibold tracking-normal" data-lang="zh">{title_zh}</h2>
          </div>
          {badge(strength_en, strength_zh, tone)}
        </div>
        <p class="mt-3 font-mono text-sm text-slate-600">{files}</p>
        {body}
      </article>
    """


def two_col(left: str, right: str) -> str:
    return f"""
      <div class="mt-5 grid gap-4 lg:grid-cols-2">
        <div class="rounded-lg border rule bg-slate-50 p-4">{left}</div>
        <div class="rounded-lg border rule bg-slate-50 p-4">{right}</div>
      </div>
    """


def candidate_contracts() -> str:
    body = two_col(
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">Before</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">之前</p>
        <div class="mt-4 grid gap-3 text-sm">
          <div class="module-box rounded p-3">minimal-contracts.md</div>
          <div class="module-box rounded p-3">fixture assertions</div>
          <div class="module-box rounded p-3">future product models</div>
        </div>
        <p class="leak mt-4 text-sm" data-lang="en">Contract knowledge repeated across callers.</p>
        <p class="leak mt-4 text-sm" data-lang="zh">Contract 知识散落在多个调用方。</p>
        """,
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">After</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">现在</p>
        <div class="deep-module mt-4 rounded p-5">
          <p class="text-lg font-semibold">Contract Module</p>
          <p class="mt-2 text-sm opacity-85">CandidateItem · BriefingItem · ArchiveMetadata · BriefingRun</p>
        </div>
        <div class="seam my-4"></div>
        <div class="grid grid-cols-3 gap-2 text-xs">
          <div class="module-box rounded p-2">fixtures</div>
          <div class="module-box rounded p-2">tests</div>
          <div class="module-box rounded p-2">product code</div>
        </div>
        """,
    )
    body += summary(
        "Problem: markdown contracts were strong but not executable. Solution: Python data models now validate core fixtures and future callers can cross one Interface.",
        "问题：Markdown contracts 很强，但不是可执行 Interface。方案：Python data models 已经能验证核心 fixtures，未来调用方可以跨同一个 Interface。",
    )
    return card(
        "Deepen the Contract Module",
        "加深 Contract Module",
        "technews_briefing/contracts.py · scripts/test_product_modules.py",
        body,
        "Strong",
        "强建议",
        "strong",
    )


def candidate_source_policy() -> str:
    body = two_col(
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">Before</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">之前</p>
        <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div class="module-box rounded p-3">RSS</div>
          <div class="module-box rounded p-3">arXiv</div>
          <div class="module-box rounded p-3">Manual URL</div>
          <div class="module-box rounded p-3">Media</div>
        </div>
        <p class="leak mt-4 text-sm" data-lang="en">Each Source Connector could interpret eligibility differently.</p>
        <p class="leak mt-4 text-sm" data-lang="zh">每个 Source Connector 都可能各自解释 eligibility。</p>
        """,
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">After</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">现在</p>
        <div class="deep-module mt-4 rounded p-5 text-center">Source Access Policy Module</div>
        <div class="seam my-4"></div>
        <div class="grid grid-cols-3 gap-2 text-xs">
          <div class="module-box rounded p-2">allow</div>
          <div class="module-box rounded p-2">block</div>
          <div class="module-box rounded p-2">explain</div>
        </div>
        """,
    )
    body += summary(
        "Problem: 25 first-version sources are deferred from the MVP. Solution: one Source Access Policy module now decides whether a Candidate Item can enter production auto-ingestion.",
        "问题：25 个 first-version source 已从 MVP 延后。方案：现在由一个 Source Access Policy Module 决定 Candidate Item 是否可进入生产自动摄入。",
    )
    return card(
        "Centralize Source Access Policy",
        "集中 Source Access Policy",
        "technews_briefing/source_policy.py · fixtures/source-ingestion/source-access-policy.json",
        body,
        "Strong",
        "强建议",
        "strong",
    )


def candidate_spike_adapters() -> str:
    body = two_col(
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">Risk</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">风险</p>
        <div class="mt-4 space-y-3 text-sm">
          <div class="module-box rounded p-3">scripts/spikes/feishu_delivery_spike.py</div>
          <div class="module-box rounded p-3">scripts/spikes/model_provider_spike.py</div>
          <div class="module-box rounded p-3">scripts/spikes/archive_storage_spike.py</div>
        </div>
        <p class="leak mt-4 text-sm" data-lang="en">Evidence-writing behaviour should not leak into product adapters.</p>
        <p class="leak mt-4 text-sm" data-lang="zh">Evidence 写入逻辑不应该泄漏进产品 adapters。</p>
        """,
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">Decision</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">决策</p>
        <div class="mt-4 grid gap-3 text-sm">
          <div class="deep-module rounded p-4">Product modules</div>
          <div class="module-box rounded p-3">Spike runners stay as proof harnesses</div>
        </div>
        """,
    )
    body += summary(
        "Problem: spike runners mix live proof, redaction, and packets. Solution: product modules were added separately and do not import spike runners.",
        "问题：spike runners 混合了 live proof、redaction 和 packets。方案：这次新增的产品 Module 独立存在，不导入 spike runners。",
    )
    return card(
        "Keep Spike Runners Outside Product Adapters",
        "让 Spike Runners 留在产品 Adapters 之外",
        "scripts/spikes/* · technews_briefing/*",
        body,
        "Strong",
        "强建议",
        "strong",
    )


def candidate_run() -> str:
    body = two_col(
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">Before</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">之前</p>
        <div class="mt-4 grid gap-2 text-sm">
          <div class="module-box rounded p-2">Source Connectors</div>
          <div class="module-box rounded p-2">Policy checks</div>
          <div class="module-box rounded p-2">Run warnings</div>
        </div>
        """,
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">After</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">现在</p>
        <div class="deep-module mt-4 rounded p-5">Automatic Briefing Run Module</div>
        <div class="seam my-4"></div>
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div class="module-box rounded p-2">accepted candidates</div>
          <div class="module-box rounded p-2">excluded candidates</div>
          <div class="module-box rounded p-2">connector status</div>
          <div class="module-box rounded p-2">run warnings</div>
        </div>
        """,
    )
    body += summary(
        "Problem: no module owned first-pass run preparation. Solution: AutomaticBriefingRun now applies Source Access Policy and creates a BriefingRun record.",
        "问题：之前没有 Module 负责第一阶段 run preparation。方案：AutomaticBriefingRun 现在会应用 Source Access Policy，并生成 BriefingRun 记录。",
    )
    return card(
        "Make Automatic Briefing Run Deep",
        "让 Automatic Briefing Run 变深",
        "technews_briefing/run.py · technews_briefing/contracts.py",
        body,
        "Worth exploring",
        "值得继续",
        "worth",
    )


def candidate_tests() -> str:
    body = two_col(
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">Before</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">之前</p>
        <div class="module-box mt-4 rounded p-4 text-sm">unittest discover: 0 tests</div>
        <div class="module-box mt-3 rounded p-4 text-sm">CI listed test scripts manually</div>
        """,
        """
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="en">After</p>
        <p class="text-xs uppercase tracking-wider text-slate-500" data-lang="zh">现在</p>
        <div class="deep-module mt-4 rounded p-5">scripts/run_tests.py</div>
        <div class="module-box mt-3 rounded p-4 text-sm" data-lang="en">Local and CI cross one test Interface.</div>
        <div class="module-box mt-3 rounded p-4 text-sm" data-lang="zh">本地和 CI 跨同一个测试 Interface。</div>
        """,
    )
    body += summary(
        "Problem: test execution knowledge lived in CI. Solution: one local entrypoint now runs readiness, existing helper tests, and new product module tests.",
        "问题：测试执行知识主要藏在 CI 里。方案：现在有一个本地入口统一运行 readiness、既有 helper tests 和新增产品 Module tests。",
    )
    return card(
        "Add One Test Entrypoint",
        "增加统一测试入口",
        "scripts/run_tests.py · .github/workflows/pre-development-readiness.yml",
        body,
        "Worth exploring",
        "值得继续",
        "worth",
    )


def summary(en: str, zh: str) -> str:
    return f"""
      <div class="mt-5 border-t rule pt-4 text-sm leading-6 text-slate-700">
        <p data-lang="en">{en}</p>
        <p data-lang="zh">{zh}</p>
      </div>
    """


def write_report(path: Path) -> None:
    path.write_text(html(), encoding="utf-8")


def open_report(path: Path) -> None:
    subprocess.run(["open", str(path)], check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None, help="HTML output path. Defaults to the OS temp directory.")
    parser.add_argument("--open", action="store_true", help="Open the generated HTML report.")
    args = parser.parse_args()
    path = args.output or output_path()
    write_report(path)
    print(path)
    if args.open:
        open_report(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
