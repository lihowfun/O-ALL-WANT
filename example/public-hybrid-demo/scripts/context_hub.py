#!/usr/bin/env python3

import os
import pathlib
import runpy

HERE = pathlib.Path(__file__).resolve()
os.environ["AGENT_MEMORY_BASE_DIR"] = str(HERE.parents[1])
runpy.run_path(str(HERE.parents[3] / "scripts" / "context_hub.py"), run_name="__main__")
