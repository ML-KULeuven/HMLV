import itertools
import json
import random

from utils.costant import ASM, KIT, FLASHLIGHT_CLIPPED, FLASHLIGHT_SCREWS, PACK


def data_gen(
    total=10,
    name='instance',

    # --- workstation counts ---
    min_kit_ws=1,          max_kit_ws=4,
    min_grip_ws=1,         max_grip_ws=2,
    min_grip_screw_ws=0,   max_grip_screw_ws=2,
    min_pack_ws=1,         max_pack_ws=3,

    # --- item demand counts ---
    min_clipped_items=0,   max_clipped_items=8,
    min_screwed_items=0,   max_screwed_items=8,

    # --- mobile robot / operator counts ---
    min_robot=0,           max_robot=4,
    min_operator=1,        max_operator=4,

    # --- conveyor belt connection caps ---
    min_conv_KB=0,         max_conv_KB=3,  # Kitting  -> Build (grip)
    min_conv_BP=0,         max_conv_BP=3,  # Build    -> Pack
    min_conv_B12=0,        max_conv_B12=2, # Grip     -> Grip&Screw

    frozen_time=True
):
    """
    Generate `total` random factory instances and save them as JSON files under ./data/instances/.

    Each instance describes:
    - how many workstations of each type exist (kit / grip / grip_screw / pack),
    - how many items need clipping/screwing,
    - how many robots / operators are available,
    - which conveyor belt connections exist between stages,
    - (optionally) fixed action durations for humans, robots, arms, and conveyors.

    Parameters like min_kit_ws / max_kit_ws define the range from which we will
    randomly draw the count for that resource in each generated instance.
    Action times are NOT randomized: they are either attached as fixed values
    (if frozen_time=True) or omitted (if frozen_time=False).
    """

    # Make sure the output directory exists so open(...) doesn't fail
    os.makedirs("./data/instances", exist_ok=True)

    for index in range(total):
        dict_to_json = {}

        # -------------------------------------------------
        # 1. Generate workstation IDs for each workstation type
        #    We'll assign each physical workstation a unique integer ID.
        #    We do this sequentially so IDs never conflict.
        # -------------------------------------------------

        # Sample how many of each workstation type we have
        no_kit          = random.randint(min_kit_ws,        max_kit_ws)
        no_grip_ws      = random.randint(min_grip_ws,       max_grip_ws)
        no_grip_screw_ws= random.randint(min_grip_screw_ws, max_grip_screw_ws)
        no_pack         = random.randint(min_pack_ws,       max_pack_ws)

        # We'll give IDs starting from 1 and increasing across all workstation pools
        next_id = 1

        # Kit workstations take IDs [next_id, next_id+no_kit-1]
        dict_to_json['kit'] = list(range(next_id, next_id + no_kit))
        next_id += no_kit

        # Grip workstations
        dict_to_json['grip'] = list(range(next_id, next_id + no_grip_ws))
        next_id += no_grip_ws

        # Grip & Screw workstations
        dict_to_json['grip_screw'] = list(range(next_id, next_id + no_grip_screw_ws))
        next_id += no_grip_screw_ws

        # Pack workstations
        dict_to_json['pack'] = list(range(next_id, next_id + no_pack))
        next_id += no_pack  # (not really needed afterwards, but keeps logic symmetric)

        # -------------------------------------------------
        # 2. Generate item requirements
        #    "clipped" and "screwed" here look like total demand counts.
        # -------------------------------------------------
        no_clipped = random.randint(min_clipped_items, max_clipped_items)
        no_screwed = random.randint(min_screwed_items, max_screwed_items)

        dict_to_json['clipped'] = no_clipped
        dict_to_json['screwed'] = no_screwed

        # -------------------------------------------------
        # 3. Generate available resources
        #    - number of mobile robots
        #    - number of human operators
        # -------------------------------------------------
        no_robot = random.randint(min_robot, max_robot)
        dict_to_json['no_robot'] = no_robot

        no_operator = random.randint(min_operator, max_operator)
        dict_to_json['no_operators'] = no_operator

        # -------------------------------------------------
        # 4. Generate conveyor belt connections
        #
        # We create directed edges (a, b) describing that material can flow
        # from workstation a to workstation b.
        #
        #   KB  = from kitting   -> grip (build)
        #   B12 = from grip      -> grip_screw
        #   BP  = from build(*)  -> pack
        #
        # Important: we only sample up to the number of available possible pairs,
        # so we never sample more unique pairs than exist.
        # -------------------------------------------------

        # --- Kitting -> Grip
        # how many links we attempt
        no_connections_KB = random.randint(min_conv_KB, max_conv_KB)
        # all possible directed pairs (kit WS, grip WS)
        all_pairs_KB = list(itertools.product(dict_to_json['kit'], dict_to_json['grip']))
        # cannot pick more than exist
        no_connections_KB = min(no_connections_KB, len(all_pairs_KB))
        # sample that many unique pairs
        conn_KB = random.sample(all_pairs_KB, no_connections_KB)

        # --- Grip -> Grip & Screw
        no_connections_B12 = random.randint(min_conv_B12, max_conv_B12)
        all_pairs_B12 = list(itertools.product(dict_to_json['grip'], dict_to_json['grip_screw']))
        no_connections_B12 = min(no_connections_B12, len(all_pairs_B12))
        conn_B12 = random.sample(all_pairs_B12, no_connections_B12)

        # --- Build -> Pack
        # build stage is effectively "grip OR grip_screw"
        build_like_nodes = dict_to_json['grip'] + dict_to_json['grip_screw']
        no_connections_BP = random.randint(min_conv_BP, max_conv_BP)
        all_pairs_BP = list(itertools.product(build_like_nodes, dict_to_json['pack']))
        no_connections_BP = min(no_connections_BP, len(all_pairs_BP))
        conn_BP = random.sample(all_pairs_BP, no_connections_BP)

        # Merge all conveyor arcs into a single list
        dict_to_json['conn'] = conn_KB + conn_B12 + conn_BP

        # -------------------------------------------------
        # 5. Fixed action durations
        #    If frozen_time=True we attach deterministic times
        #    for each action type, grouped by who/what performs it.
        #
        # -------------------------------------------------
        if frozen_time:
            dict_to_json['operator_action_time'] = {
                "Kit workstation - make kit": 20,
                "Kit workstation - add screws": 10,
                "Build workstation - build from kit": 30,
                "Build workstation - add screws": 20,
                "Pack workstation - make package": 5,
                "Transport": 5
            }

            dict_to_json['mobile_robot_action_time'] = {
                "Transport": 8
            }

            dict_to_json['kitting_arm_action_time'] = {
                "Kit workstation - make kit": 10
            }

            dict_to_json['grip_arm_action_time'] = {
                "Build workstation - build from kit": 10
            }

            dict_to_json['grip_screw_arm_action_time'] = {
                "Build workstation - build from kit": 20,
                "Build workstation - add screws": 15
            }

            dict_to_json['pack_arm_action_time'] = {
                "Pack workstation - make package": 15
            }

            dict_to_json['conveyor_action_time'] = {
                "Transport": 3
            }

        # -------------------------------------------------
        # 6. Dump instance to disk as JSON
        #    ./data/instances/{name}_{index}.json
        # -------------------------------------------------
        out_path = f"./data/instances/{name}_{index}.json"
        with open(out_path, "w") as f:
            json.dump(dict_to_json, f, indent=4)

