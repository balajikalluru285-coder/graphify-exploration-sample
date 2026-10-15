"""
cobc_c_to_graph.py

Reads C files produced by `cobc -C` and rebuilds the COBOL-level structure from
the comments the compiler leaves in them, instead of parsing the C itself.

What it recovers (all with COBOL file + line numbers):
  - programs                         (PROGRAM-ID)
  - paragraphs and sections          (nodes inside each program)
  - PERFORM edges                    (paragraph -> paragraph, incl. PERFORM A THRU B)
  - CALL edges with a literal name   (paragraph -> program)
What it reports but does NOT turn into edges:
  - PERFORMs whose target it cannot resolve
  - CALLs whose target is held in a variable (dynamic) or could not be found

Tested against GnuCOBOL cobc 3.1.2 output only. The comment format is not a
documented, stable interface, so other cobc versions may need adjustments.

Usage:
    python cobc_c_to_graph.py default\\orderprg.c default\\payment.c
    python cobc_c_to_graph.py default            (a folder: reads every *.c in it)
    python cobc_c_to_graph.py default -o cobol_graph.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

LINE_RE = re.compile(r"/\*\s*Line:\s*(\d+)\s*:\s*(.*?)\s*:\s*(.+?)\s*\*/")
PROGRAM_RE = re.compile(r"^\s*/\*\s*PROGRAM-ID\s+'([^']+)'\s*\*/")
END_PROGRAM_RE = re.compile(r"^\s*/\*\s*End PROGRAM-ID\s+'([^']+)'\s*\*/")
STRUCT_RE = re.compile(r"(Entry|Paragraph|Section)\s+(\S+)$")
PERFORM_RE = re.compile(r"^\s*/\*\s*PERFORM\s+(.+?)\s*\*/\s*$")
PERFORM_TARGET_RE = re.compile(
    r"([A-Za-z0-9][A-Za-z0-9-]*)(?:\s+THRU\s+([A-Za-z0-9][A-Za-z0-9-]*))?$", re.I
)
RESOLVE_RE = re.compile(r'cob_resolve_cobol\s*\(\s*("([^"]*)"|[^,]+?)\s*,')


def slug(*parts):
    return re.sub(r"[^a-z0-9]+", "_", "_".join(parts).lower()).strip("_")


def parse_c_file(path, model):
    """Walk one generated C file line by line, collecting COBOL-level facts."""
    prog = None          # current COBOL program
    para = None          # current paragraph/section inside that program
    marker = None        # latest "Line: N : <statement> : <file>" comment
    pending_call = None  # a CALL marker still waiting for its target string
    markers_seen = 0

    def flush_call():
        nonlocal pending_call
        if pending_call is not None:
            pending_call["target"] = None
            pending_call["reason"] = "target not found in the generated C"
            model["calls"].append(pending_call)
            pending_call = None

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = PROGRAM_RE.match(raw)
        if m:
            flush_call()
            prog = m.group(1).upper()
            para = None
            marker = None
            model["programs"].setdefault(prog, {"name": prog, "line": None, "file": None})
            continue

        if END_PROGRAM_RE.match(raw):
            flush_call()
            prog = None
            para = None
            marker = None
            continue

        m = LINE_RE.search(raw)
        if m:
            markers_seen += 1
            flush_call()
            line_no = int(m.group(1))
            text = m.group(2).strip()
            src = m.group(3).strip()
            marker = (line_no, text, src)
            if prog is None:
                continue
            s = STRUCT_RE.match(text)
            if s:
                kind, name = s.group(1), s.group(2).upper()
                if kind == "Entry":
                    info = model["programs"][prog]
                    if name == prog and info["line"] is None:
                        info["line"], info["file"] = line_no, src
                else:
                    model["paragraphs"].append(
                        {"prog": prog, "name": name, "line": line_no, "file": src}
                    )
                    para = name
            elif text.upper() == "CALL":
                pending_call = {
                    "prog": prog, "para": para, "line": line_no, "file": src,
                    "target": None, "reason": None,
                }
            continue

        m = PERFORM_RE.match(raw)
        if m and prog and marker and marker[1].upper() == "PERFORM":
            model["performs"].append(
                {"prog": prog, "para": para, "text": m.group(1),
                 "line": marker[0], "file": marker[2]}
            )
            continue

        if pending_call is not None:
            m = RESOLVE_RE.search(raw)
            if m:
                if m.group(2) is not None:      # quoted literal -> program name
                    pending_call["target"] = m.group(2).strip().upper()
                else:                           # a variable -> cannot know statically
                    pending_call["target"] = None
                    pending_call["reason"] = "target held in a variable (dynamic CALL)"
                model["calls"].append(pending_call)
                pending_call = None

    flush_call()
    if markers_seen == 0:
        model["warnings"].append(
            f"{path}: no 'Line:' comments found - is this really `cobc -C` output?"
        )


def build_graph(model):
    nodes = {}
    links = []
    unresolved = []

    prog_names = list(model["programs"].keys())
    community_of = {name: i for i, name in enumerate(prog_names)}
    external_community = len(prog_names)

    paras_by_prog = {}
    for p in model["paragraphs"]:
        paras_by_prog.setdefault(p["prog"], []).append(p)

    def node_base(node_id, label, community, community_name, src_file, line):
        return {
            "id": node_id,
            "label": label,
            "_callable": True,
            "_origin": "cobc",
            "community": community,
            "community_name": community_name,
            "file_type": "code",
            "norm_label": label.lower(),
            "source_file": src_file or "",
            "source_location": f"L{line}" if line else "",
        }

    for name, info in model["programs"].items():
        nid = slug("cobol", name)
        nodes[nid] = node_base(nid, name, community_of[name], name, info["file"], info["line"])
        nodes[nid]["cobol_kind"] = "program"

    for p in model["paragraphs"]:
        nid = slug("cobol", p["prog"], p["name"])
        label = f'{p["prog"]}.{p["name"]}'
        nodes[nid] = node_base(nid, label, community_of[p["prog"]], p["prog"], p["file"], p["line"])
        nodes[nid]["cobol_kind"] = "paragraph"
        links.append(
            make_link(slug("cobol", p["prog"]), nid, "contains", "structure", p["file"], p["line"])
        )

    # Entering a program starts at its first paragraph. Without this edge, a CALL to a
    # program would stop at the program node and impact analysis could not continue
    # into the paragraphs inside it.
    for prog_name, plist in paras_by_prog.items():
        first = plist[0]
        links.append(
            make_link(slug("cobol", prog_name), slug("cobol", prog_name, first["name"]),
                      "calls", "entry (first paragraph)", first["file"], first["line"])
        )

    def source_id(prog, para):
        return slug("cobol", prog, para) if para else slug("cobol", prog)

    # PERFORM edges (including PERFORM A THRU B -> every paragraph in the range)
    for perf in model["performs"]:
        paras = paras_by_prog.get(perf["prog"], [])
        names = [x["name"] for x in paras]
        m = PERFORM_TARGET_RE.match(perf["text"])
        where = f'{perf["prog"]} {perf["file"]}:L{perf["line"]}'
        if not m:
            unresolved.append(f'{where}: PERFORM {perf["text"]} (not a simple paragraph name)')
            continue
        first = m.group(1).upper()
        last = (m.group(2) or "").upper()
        if first not in names:
            unresolved.append(f'{where}: PERFORM {perf["text"]} (target not a known paragraph)')
            continue
        i = names.index(first)
        j = i
        if last:
            if last not in names or names.index(last) < i:
                unresolved.append(f'{where}: PERFORM {perf["text"]} (THRU target not found)')
                continue
            j = names.index(last)
        context = "perform" if i == j else f"perform thru ({first} thru {last})"
        for k in range(i, j + 1):
            target = slug("cobol", perf["prog"], names[k])
            links.append(
                make_link(source_id(perf["prog"], perf["para"]), target, "calls",
                          context, perf["file"], perf["line"])
            )

    # CALL edges with a literal program name
    for call in model["calls"]:
        where = f'{call["prog"]} {call["file"]}:L{call["line"]}'
        if call["target"] is None:
            unresolved.append(f'{where}: CALL ({call["reason"]})')
            continue
        target_id = slug("cobol", call["target"])
        if target_id not in nodes:
            nodes[target_id] = node_base(target_id, call["target"], external_community,
                                         "external programs (not scanned)", "", None)
            nodes[target_id]["cobol_kind"] = "external program"
        links.append(
            make_link(source_id(call["prog"], call["para"]), target_id, "calls",
                      "call", call["file"], call["line"])
        )

    graph = {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": list(nodes.values()),
        "links": links,
    }
    return graph, unresolved


def make_link(source, target, relation, context, src_file, line):
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "_origin": "cobc",
        "confidence": "EXTRACTED",
        "confidence_score": 1.0,
        "context": context,
        "source_file": src_file or "",
        "source_location": f"L{line}" if line else "",
        "weight": 1.0,
    }


def print_summary(graph, unresolved, warnings):
    label = {n["id"]: n["label"] for n in graph["nodes"]}
    kinds = {}
    for n in graph["nodes"]:
        kinds[n["cobol_kind"]] = kinds.get(n["cobol_kind"], 0) + 1
    print(f"Nodes: {len(graph['nodes'])}  {kinds}")
    print(f"Edges: {len(graph['links'])}")
    print("\nPERFORM / CALL edges (with COBOL location):")
    for link in graph["links"]:
        if link["relation"] == "calls":
            print(f"  {label[link['source']]} -> {label[link['target']]}"
                  f"   [{link['context']}]  {link['source_file']}:{link['source_location']}")
    print(f"\nUnresolved or dynamic items: {len(unresolved)}")
    for item in unresolved:
        print("  -", item)
    for w in warnings:
        print("WARNING:", w)


def main():
    ap = argparse.ArgumentParser(description="Build a COBOL-level graph from cobc -C output.")
    ap.add_argument("inputs", nargs="+", help="generated .c files, or folders containing them")
    ap.add_argument("-o", "--out", default="cobol_graph.json", help="output JSON path")
    args = ap.parse_args()

    files = []
    for item in args.inputs:
        p = Path(item)
        files.extend(sorted(p.glob("*.c")) if p.is_dir() else [p])
    if not files:
        sys.exit("No .c files found.")

    model = {"programs": {}, "paragraphs": [], "performs": [], "calls": [], "warnings": []}
    for f in files:
        parse_c_file(f, model)

    graph, unresolved = build_graph(model)
    Path(args.out).write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Read {len(files)} file(s). Wrote {args.out}\n")
    print_summary(graph, unresolved, model["warnings"])


if __name__ == "__main__":
    main()
