

import json
import plotly.graph_objects as go
import math
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative as q
# from collections import Counter


# def plot_time_perf(output_dir="results", y_max=None):
#     """
#     Plot time performance across all CSV files in `output_dir`,
#     using *the exact same style* as plot_time_perf.
#
#     Each CSV is treated as one method, with its own avg_time and std_time.
#     The legend label is the CSV filename (without .csv).
#     """
#
#     ensure_directory_exists(output_dir)
#
#     csv_files = sorted(glob.glob(os.path.join(output_dir, "*.csv")))
#     if not csv_files:
#         raise FileNotFoundError(f"No CSV files found in {output_dir}")
#
#     # Read first CSV to get the x-axis
#     df0 = pd.read_csv(csv_files[0])
#     x = df0["number_of_items"]
#
#     plt.figure(figsize=(12, 7))
#
#     # Iterate over all CSVs and plot each as a separate method
#     for csv_path in csv_files:
#         df = pd.read_csv(csv_path)
#         label = os.path.splitext(os.path.basename(csv_path))[0]
#
#         # Extract avg & std columns
#         avg = df["avg_time"]
#         std = df["std_time"]
#
#         plt.errorbar(
#             x,
#             avg,
#             yerr=std,
#             fmt='o',  # EXACT same style as your code
#             capsize=5,
#             label=label
#         )
#
#     # Formatting (identical)
#     plt.xlabel("Number of items")
#     plt.ylabel("Time (s)")
#     max_x = int(np.max(x))
#     plt.xticks(np.arange(0, max_x + 1, 2))
#     plt.xlim(0, max_x)
#
#     if y_max is not None:
#         plt.ylim(0, y_max)
#
#     plt.grid(True, alpha=0.3)
#     plt.legend()
#     plt.tight_layout()
#     plt.show()

def make_ws_topology_from_json(json_file, title="Workstation Topology", location=None, scale=1.25):
    """
    Draw a topology of the system from a JSON file with keys:
      - orderbook
      - resources:
          - workstations
          - operators
          - mobile_robots
          - conveyor_belts

    The figure shows:
      - Workstations grouped in columns: Kitting | Build | Packing
      - Operators and mobile robots as summary blocks
      - Conveyor belts as arrows from 'from' WS to 'to' WS
      - A global summary box showing how many items of each product
        are in the orderbook (by volume).
    """

    # ------------------------------------------------------------------
    # Load JSON
    # ------------------------------------------------------------------
    with open(json_file, "r") as f:
        data = json.load(f)

    orderbook = data.get("orderbook", {})
    resources = data.get("resources", {})

    workstations = resources.get("workstations", {})
    human_ws = resources.get("ws-human", {})
    all_workstations = {**workstations, **human_ws}
    operators = resources.get("operators", {})
    robots = resources.get("mobile_robots", {})
    conveyors = resources.get("conveyor_belts", {})

    S = scale

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def ws_category(ws_id: str, ws_type: str) -> str:
        """
        Map workstation 'type' string or 'ws_id' from JSON to a column:
          - contains 'kit'   -> 'Kitting'
          - contains 'pack'  -> 'Packing'
          - everything else  -> 'Build'
        """
        t = (ws_type or "").lower()
        i = (ws_id or "").lower()
        if "kit" in t or "kit" in i:
            return "Kitting"
        if "pack" in t or "pack" in i:
            return "Packing"
        return "Build"

    def node_label(ws_id: str, ws_info: dict) -> str:
        """
        Label for each workstation box.
        Example: 'kit-1 kit'
        """
        # Exact mapping for 'type'
        type_map = {
            "kit": "Kit WS",
            "grip": "Build WS 1",
            "grip & screw": "Build WS 2",
            "arm": "Build WS 3",
            "pack": "Pack WS"
        }
        
        # Mapping for specific ws_id if type isn't enough or for exceptions
        id_map = {
            "kit-human-1": "Kit WS",
            "build-human-1": "Build WS",
            "pack-human-1": "Pack WS"
        }
        
        t = (ws_info.get("type", "") or "").lower().strip()
        is_human = ws_info.get("human", False)
        
        base_label = None
        if t in type_map:
            base_label = type_map[t]
        elif ws_id in id_map:
            base_label = id_map[ws_id]
        else:
            # Fallback for IDs
            if "kit" in ws_id.lower(): base_label = "Kit WS"
            elif "grip-1" in ws_id.lower() or "grip-5" in ws_id.lower(): base_label = "Build WS 1"
            elif "grip-2" in ws_id.lower() or "grip-3" in ws_id.lower(): base_label = "Build WS 2"
            elif "grip-4" in ws_id.lower(): base_label = "Build WS 3"
            elif "pack" in ws_id.lower(): base_label = "Pack WS"
            else: base_label = f"{ws_id} {t}"
            
        if is_human:
            return f"<b>{base_label}</b><br>(Employee)"
        return f"<b>{base_label}</b>"

    # ------------------------------------------------------------------
    # Columns: Kitting | Build | Packing
    # ------------------------------------------------------------------
    # Flatten workstations in case of nesting (like the grip-4/grip-5 issue)
    flattened_workstations = {}
    def flatten_ws(ws_dict, prefix=""):
        for k, v in ws_dict.items():
            if isinstance(v, dict):
                # If it looks like a workstation (has 'type' or 'durations'), keep it
                if "type" in v or "durations" in v:
                    flattened_workstations[k] = v
                # Also recurse in case of nested definitions
                flatten_ws(v, k)
    
    flatten_ws(all_workstations)
    
    ws_kit_auto, ws_kit_human = [], []
    ws_build_auto, ws_build_human = [], []
    ws_pack_auto, ws_pack_human = [], []

    for ws_id, ws_info in flattened_workstations.items():
        cat = ws_category(ws_id, ws_info.get("type", ""))
        is_human = ws_info.get("human", False)
        if cat == "Kitting":
            if is_human: ws_kit_human.append(ws_id)
            else: ws_kit_auto.append(ws_id)
        elif cat == "Packing":
            if is_human: ws_pack_human.append(ws_id)
            else: ws_pack_auto.append(ws_id)
        else:
            if is_human: ws_build_human.append(ws_id)
            else: ws_build_auto.append(ws_id)

    ws_kit = sorted(ws_kit_auto) + sorted(ws_kit_human)
    ws_build = sorted(ws_build_auto) + sorted(ws_build_human)
    ws_pack = sorted(ws_pack_auto) + sorted(ws_pack_human)

    columns = [
        ("Kitting", ws_kit),
        ("Build", ws_build),
        ("Packing", ws_pack),
    ]

    # ------------------------------------------------------------------
    # Layout / style
    # ------------------------------------------------------------------
    box_w, box_h = 3.0 * S, 0.75 * S
    x_gap, y_gap = 2.3 * S, 1.4 * S
    group_gap = 3.0 * S
    font_color = "#FFFFFF"

    LABEL_FONT_SIZE = 40
    GROUP_TITLE_FONT_SIZE = int(30 * S)
    HR_FONT_SIZE = 40
    TITLE_FONT_SIZE = int(22 * S)

    col_bg = [
        "rgba(66,135,245,0.10)",   # Kitting col background
        "rgba(255,159,67,0.10)",   # Build col background
        "rgba(235,87,87,0.10)",    # Packing col background
    ]

    color_map = {
        "kitting": "rgba(66,135,245,1)",
        "build": "rgba(40,199,111,1)",
        "packing": "rgba(235,87,87,1)",
        "neutral": "rgba(160,160,160,1)",
    }

    max_rows = max(1, *(len(col_ids) for _, col_ids in columns))
    start_y = (max_rows - 1) * y_gap / 2.0

    pos = {}     # ws_id -> (x, y)
    shapes = []  # rectangles, backgrounds
    annos = []   # text + arrows

    # ------------------------------------------------------------------
    # Draw workstation columns
    # ------------------------------------------------------------------
    x_offset = 0.0
    first_x, last_x = None, None

    for c, (col_title, mids) in enumerate(columns):
        x = x_offset
        if first_x is None:
            first_x = x
        last_x = x

        # Column background
        shapes.append(dict(
            type="rect", xref="x", yref="y",
            x0=x - box_w / 1.2, x1=x + box_w / 1.2,
            y0=-start_y - 0.9 * S, y1=start_y + 0.9 * S,
            line=dict(width=0), fillcolor=col_bg[c % len(col_bg)]
        ))

        # Column title
        annos.append(dict(
            x=x, y=start_y + 1.0 * S, xref="x", yref="y",
            text=f"<b>{col_title}</b>",
            showarrow=False,
            font=dict(size=GROUP_TITLE_FONT_SIZE, color="#FFFFFF"),
            xanchor="center"
        ))

        # Individual workstations in this column
        for r, ws_id in enumerate(mids):
            y = start_y - r * y_gap
            pos[ws_id] = (x, y)

            ws_info = flattened_workstations[ws_id]
            cat = ws_category(ws_id, ws_info.get("type", ""))
            is_human = ws_info.get("human", False)

            if cat == "Kitting":
                fill = color_map["kitting"]
            elif cat == "Packing":
                fill = color_map["packing"]
            elif cat == "Build":
                fill = color_map["build"]
            else:
                fill = color_map["neutral"]

            # Adjust box size for human WS
            current_w = box_w * 1.15 if is_human else box_w
            current_h = box_h * 1.3 if is_human else box_h

            # Workstation rectangle
            shapes.append(dict(
                type="rect", xref="x", yref="y",
                x0=x - current_w / 2, x1=x + current_w / 2,
                y0=y - current_h / 2, y1=y + current_h / 2,
                line=dict(color="white", width=2), fillcolor=fill
            ))

            # Workstation label
            annos.append(dict(
                x=x, y=y, xref="x", yref="y",
                text=node_label(ws_id, ws_info),
                showarrow=False,
                font=dict(size=LABEL_FONT_SIZE if not is_human else int(LABEL_FONT_SIZE * 0.8), color=font_color),
                xanchor="center", yanchor="middle"
            ))

        # Move to next column
        x_offset += x_gap + group_gap

    # ------------------------------------------------------------------
    # Employees / mobile robots summary blocks
    # ------------------------------------------------------------------
    human_ids = list(operators.keys())
    robot_ids = list(robots.keys())

    if human_ids or robot_ids:
        # Larger summary blocks
        hw, hh = 3.8 * S, 1.4 * S
        y_h = start_y + 2.5 * S
        # roughly center above the middle column
        build_x_center = x_gap + group_gap

        if human_ids and robot_ids:
            x_robot = build_x_center - 2.4 * S
            x_human = build_x_center + 2.4 * S
        elif human_ids:
            x_human = build_x_center
            x_robot = None
        else:
            x_robot = build_x_center
            x_human = None

        # Employees block
        if human_ids and x_human is not None:
            shapes.append(dict(
                type="rect", xref="x", yref="y",
                x0=x_human - hw / 2, x1=x_human + hw / 2,
                y0=y_h - hh / 2, y1=y_h + hh / 2,
                line=dict(color="white", width=2),
                fillcolor="#C64191"
            ))
            label = "employee" if len(human_ids) == 1 else f"{len(human_ids)} employees"
            annos.append(dict(
                x=x_human, y=y_h, xref="x", yref="y",
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=HR_FONT_SIZE, color="#000000"),
                xanchor="center", yanchor="middle"
            ))

        # Robots block
        if robot_ids and x_robot is not None:
            shapes.append(dict(
                type="rect", xref="x", yref="y",
                x0=x_robot - hw / 2, x1=x_robot + hw / 2,
                y0=y_h - hh / 2, y1=y_h + hh / 2,
                line=dict(color="white", width=2),
                fillcolor="#DCABDF"
            ))
            label = "robot" if len(robot_ids) == 1 else f"{len(robot_ids)} robots"
            annos.append(dict(
                x=x_robot, y=y_h, xref="x", yref="y",
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=HR_FONT_SIZE, color="#000000"),
                xanchor="center", yanchor="middle"
            ))

    # ------------------------------------------------------------------
    # Conveyor arrows between workstations
    # ------------------------------------------------------------------
    for c_id, c_info in conveyors.items():
        m1 = c_info.get("from")
        m2 = c_info.get("to")
        if m1 not in pos or m2 not in pos:
            continue

        x1, y1 = pos[m1]
        x2, y2 = pos[m2]

        src_top = (x1, y1 + box_h / 2)
        src_bottom = (x1, y1 - box_h / 2)
        src_left = (x1 - box_w / 2, y1)
        src_right = (x1 + box_w / 2, y1)

        dst_top = (x2, y2 + box_h / 2)
        dst_bottom = (x2, y2 - box_h / 2)
        dst_left = (x2 - box_w / 2, y2)
        dst_right = (x2 + box_w / 2, y2)

        # try four possible arrow placements and take the shortest
        connections = [
            (src_top, dst_bottom),
            (src_bottom, dst_top),
            (src_left, dst_right),
            (src_right, dst_left),
        ]

        best = None
        best_dist = float("inf")
        for (ax, ay), (tx, ty) in connections:
            dist = ((tx - ax) ** 2 + (ty - ay) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = (ax, ay, tx, ty)

        if best:
            ax, ay, tx, ty = best
            annos.append(dict(
                x=tx, y=ty, xref="x", yref="y",
                ax=ax, ay=ay, axref="x", ayref="y",
                text="",     # conveyor id label on arrow removed
                showarrow=True,
                arrowhead=3,
                arrowsize=2.2,
                arrowwidth=4,
                arrowcolor="#DDDDDD",
                opacity=1.0,
                font=dict(color="#DDDDDD", size=18),
            ))

    # ------------------------------------------------------------------
    # Figure bounds
    # ------------------------------------------------------------------
    if first_x is None:
        first_x = 0.0
    if last_x is None:
        last_x = 0.0

    content_left = first_x - box_w / 1.2
    content_right = last_x + box_w / 1.2

    if human_ids or robot_ids:
        y_top_bg = start_y + 2.5 * S + (0.5 * S)
    else:
        y_top_bg = start_y + 0.9 * S
    y_bot_bg = -start_y - 0.9 * S

    pad = 0.5 * S
    x_min = content_left - pad
    x_max = content_right + pad
    y_min = y_bot_bg - pad
    y_max = y_top_bg + pad

    # ------------------------------------------------------------------
    # Final figure
    # ------------------------------------------------------------------
    fig = go.Figure()

    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor="center",
            font=dict(size=TITLE_FONT_SIZE, color="#FFFFFF"),
            pad=dict(t=20, b=20),
        ),
        paper_bgcolor="black",
        plot_bgcolor="black",
        xaxis=dict(visible=False, range=[x_min, x_max]),
        yaxis=dict(
            visible=False,
            range=[y_min, y_max],
            scaleanchor="x",
            scaleratio=1,
        ),
        margin=dict(l=40, r=40, t=100, b=40),
        shapes=shapes,
        annotations=annos,
        width=int(1600 * S),
        height=int(900 * S),
        autosize=False,
    )

    if location is not None:
        fig.write_image(
            location,
            format="png",
            width=int(1600 * S),
            height=int(900 * S),
            scale=1,
        )
    else:
        fig.update_layout(width=1400, height=600)
        fig.show()


import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative as q


def plot_solution_gantt(
    problem,
    title="FJ Transport – Schedule",
    file_html=None,
    file_png=None,
    width=1400,
    height=600,
    show=True,
):
    """
    Plot an interactive Gantt chart for a solved FJTransportProblem instance.

    Uses:
      - problem.S[item_id][op_name]
      - problem.D[item_id][op_name]
      - problem.Z_auto_ws[item_id][op_name][ws_id]
      - problem.Z_human_ws[item_id][op_name][hws_id]
      - problem.Z_op[item_id][op_name][op_id]
      - problem.Z_tr[item_id][t_op][agent_id]
    """

    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px

    # ---------- resources & helper functions ----------
    resources = problem.resources
    ws_auto_ids = problem.auto_ws_ids
    ws_human_ids = problem.human_ws_ids
    op_ids = problem.operator_ids
    rob_ids = problem.robot_ids
    conv_ids = problem.conveyor_ids

    def agent_type(a):
        if a in ws_auto_ids:
            return "workstation_auto"
        if a in ws_human_ids:
            return "workstation_human"
        if a in conv_ids:
            return "conveyor"
        if a in rob_ids:
            return "robot"
        if a.startswith("skill_"): # Handling skill pools as operators for visualization
            return "operator"
        if a == "robot_pool":
            return "robot"
        return "other"

    def agent_label(a):
        t = agent_type(a)
        if t == "workstation_auto":
            return f"WS {a}"
        if t == "workstation_human":
            return f"WS-H {a}"
        if t == "operator":
            if a.startswith("skill_"):
                return f"SKILL POOL {a[len('skill_'):]}"
            return f"OP {a}"
        if t == "robot":
            if a == "robot_pool":
                return "ROBOT_POOL"
            return f"MR {a}"
        if t == "conveyor":
            return f"CV {a}"
        return str(a)

    # ---------- collect bars + per-op info ----------
    rows = []
    op_times = {}       # (item_id, op_name) -> (start, end)
    op_lane_label = {}  # (item_id, op_name) -> primary lane label (for flow lines)

    for item_id in problem.items:
        product_name = problem.item_product[item_id]

        for op_name in problem.item_operations[item_id]:
            S_var = problem.S[item_id][op_name]
            # D_var for FJTransportProblemFinal is computed as a sum,
            # so we use duration_expr to get the value
            D_val = problem.duration_expr(item_id, op_name).value()

            Sv = S_var.value()

            # skip unsolved ops
            if Sv is None or D_val is None:
                continue

            start = int(Sv)
            dur = int(D_val)
            end = start + dur
            if end < start:
                continue  # safety, but shouldn't happen

            ot = "transport" if problem.is_transport(op_name) else "processing"

            # ------------ TRANSPORT OPS ------------
            if problem.is_transport(op_name):
                chosen_agent = None
                for agent_id, z_var in problem.Z_tr[item_id][op_name].items():
                    zv = z_var.value()
                    if zv is not None and zv:
                        chosen_agent = agent_id
                        break

                if chosen_agent is None:
                    # no agent chosen for this transport (model inconsistent / not solved?)
                    continue

                lane = agent_label(chosen_agent)

                rows.append(
                    {
                        "Item": item_id,
                        "Product": product_name,
                        "Operation": op_name,
                        "OpType": ot,
                        "Agent": lane,
                        "AgentId": chosen_agent,
                        "Start": start,
                        "End": end,
                        "Duration": dur,
                    }
                )

                op_times[(item_id, op_name)] = (start, end)
                op_lane_label[(item_id, op_name)] = lane
                continue

            # ------------ PROCESSING OPS ------------
            # chosen automatic WS (if any)
            chosen_auto_ws = None
            for ws_id, z_ws in problem.Z_auto_ws[item_id][op_name].items():
                zv = z_ws.value()
                if zv is not None and zv:
                    chosen_auto_ws = ws_id
                    break

            # chosen human WS (if any)
            chosen_hws = None
            for hws_id, z_hws in problem.Z_human_ws[item_id][op_name].items():
                zv = z_hws.value()
                if zv is not None and zv:
                    chosen_hws = hws_id
                    break

            # Automatic mode: one bar on auto WS lane
            if chosen_auto_ws is not None:
                lane_ws = agent_label(chosen_auto_ws)
                rows.append(
                    {
                        "Item": item_id,
                        "Product": product_name,
                        "Operation": op_name,
                        "OpType": ot,
                        "Agent": lane_ws,
                        "AgentId": chosen_auto_ws,
                        "Start": start,
                        "End": end,
                        "Duration": dur,
                    }
                )
                op_times[(item_id, op_name)] = (start, end)
                op_lane_label[(item_id, op_name)] = lane_ws

            # Human mode: bar on human WS lane
            if chosen_hws is not None:
                lane_hws = agent_label(chosen_hws)
                rows.append(
                    {
                        "Item": item_id,
                        "Product": product_name,
                        "Operation": op_name,
                        "OpType": ot,
                        "Agent": lane_hws,
                        "AgentId": chosen_hws,
                        "Start": start,
                        "End": end,
                        "Duration": dur,
                    }
                )
                op_times[(item_id, op_name)] = (start, end)
                op_lane_label[(item_id, op_name)] = lane_hws

    if not rows:
        raise ValueError(
            "No scheduled operations found to plot. "
            "Make sure you solved the model before calling plot_solution_gantt()."
        )

    df = pd.DataFrame(rows)

    # ---------- lane ordering ----------
    def lane_rank(agent_label_str, agent_id):
        """
        Order: workstations (auto & human), conveyors, robots, operators/skill_pools, other.
        """
        t = agent_type(agent_id)
        if t == "workstation_auto":
            base = 0
        elif t == "workstation_human":
            base = 1
        elif t == "conveyor":
            base = 2
        elif t == "robot":
            base = 3
        elif t == "operator":  # This will now include skill pools
            base = 4
        else:
            base = 5
        return base, str(agent_label_str)

    ranks = {
        (row.Agent, row.AgentId): lane_rank(row.Agent, row.AgentId)
        for row in df.itertuples()
    }

    unique_agents = sorted(ranks.keys(), key=lambda k: ranks[k])
    lane_order = [agent for (agent, _) in unique_agents]

    df["Agent"] = pd.Categorical(df["Agent"], categories=lane_order, ordered=True)

    # ---------- colors & patterns ----------
    palette = q.Plotly

    item_ids = sorted(df["Item"].unique())
    item_color = {
        item: palette[idx % len(palette)] for idx, item in enumerate(item_ids)
    }

    def op_type_of(item_id, op_name): # New helper function
        return "transport" if problem.is_transport(op_name) else "processing"

    def op_pattern(op_type):
        # processing: solid; transport: diagonal stripe
        return "" if op_type == "processing" else "/"

    df["PatternShape"] = df.apply(lambda row: op_pattern(op_type_of(row.Item, row.Operation)), axis=1)

    # ---------- build bar traces ----------
    fig = go.Figure()

    for item in item_ids:
        dfi = df[df["Item"] == item]
        color = item_color[item]
        legend_name = f"{item} ({dfi['Product'].iloc[0]})"

        hovertext = [
            f"Item: {row.Item}<br>"
            f"Product: {row.Product}<br>"
            f"Op: {row.Operation} ({op_type_of(row.Item, row.Operation)})<br>"
            f"Agent: {row.Agent}<br>"
            f"Start: {row.Start}  End: {row.End}"
            for _, row in dfi.iterrows()
        ]

        fig.add_bar(
            x=dfi["Duration"],
            y=dfi["Agent"],
            base=dfi["Start"],
            orientation="h",
            name=legend_name,
            hovertext=hovertext,
            hoverinfo="text",
            marker=dict(
                color=color,
                line=dict(width=2, color="white"),
                pattern=dict(
                    shape=dfi["PatternShape"].tolist(),
                    size=8,
                    solidity=0.5,
                ),
            ),
            legendgroup=str(item),
        )

    # ---------- flow lines: connect prev – transport – next ----------
    def safe_lane(label):
        return label if label in lane_order else None

    for item in item_ids:
        ops = problem.item_operations[item]
        color = item_color[item]
        lg = str(item)

        for idx, op_name in enumerate(ops):
            if op_type_of(item, op_name) != "transport":
                continue
            if idx == 0 or idx == len(ops) - 1:
                continue

            prev_op = ops[idx - 1]
            next_op = ops[idx + 1]

            key_t = (item, op_name)
            key_p = (item, prev_op)
            key_n = (item, next_op)
            if key_t not in op_times or key_p not in op_times or key_n not in op_times:
                continue

            S_prev, E_prev = op_times[key_p]
            S_t,   E_t     = op_times[key_t]
            S_next, _      = op_times[key_n]

            lane_prev = safe_lane(op_lane_label.get(key_p, None))
            lane_t    = safe_lane(op_lane_label.get(key_t, None))
            lane_next = safe_lane(op_lane_label.get(key_n, None))
            if lane_prev is None or lane_t is None or lane_next is None:
                continue

            EPS_IN, EPS_OUT = 0.05, 0.05
            x_prev_out = E_prev - EPS_OUT
            x_t_in     = S_t   + EPS_IN
            x_t_out    = E_t   - EPS_OUT
            x_next_in  = S_next + EPS_IN

            fig.add_scatter(
                x=[x_prev_out, x_t_in],
                y=[lane_prev, lane_t],
                mode="lines",
                line=dict(width=2, color=color),
                showlegend=False,
                hoverinfo="skip",
                legendgroup=lg,
                name=f"{lg} flow",
            )
            fig.add_scatter(
                x=[x_t_out, x_next_in],
                y=[lane_t, lane_next],
                mode="lines",
                line=dict(width=2, color=color),
                showlegend=False,
                hoverinfo="skip",
                legendgroup=lg,
                name=f"{lg} flow",
            )

    # ---------- layout ----------
    try:
        makespan_val = problem.makespan.value()
        max_time = int(makespan_val) if makespan_val is not None else int(df["End"].max())
    except Exception:
        max_time = int(df["End"].max())

    fig.update_layout(
        title=title if max_time is None else f"{title} – Makespan {max_time}",
        width=width,
        height=height,
        autosize=False,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white"),
        title_font=dict(color="white"),
        legend_title=dict(text="Item", font=dict(color="white")),
        barmode="overlay",
        bargap=0.15,
        margin=dict(l=80, r=40, t=60, b=50),
        xaxis=dict(
            title="Time",
            showgrid=True,
            gridcolor="lightgray",
            color="white",
        ),
        yaxis=dict(
            title="Agent",
            showgrid=True,
            gridcolor="lightgray",
            color="white",
            categoryorder="array",
            categoryarray=lane_order,
        ),
    )

    fig.update_xaxes(range=[0, max_time * 1.05])

    # ---------- save / show ----------
    if file_png is not None:
        fig.write_image(file_png, scale=2)

    if file_html is not None:
        fig.write_html(file_html)

    if show and file_png is None and file_html is None:
        fig.show()

