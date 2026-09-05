#!/usr/bin/env python3
"""从现有 ubuntu 快照启动沙盒、预装 LibreOffice、捕获为新快照。

用法:
    source .env   # 需要 LANGSMITH_API_KEY
    python preinstall_libreoffice.py
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from langsmith.sandbox import SandboxClient

load_dotenv()

BASE_SNAPSHOT_ID = os.environ.get("BASE_SNAPSHOT_ID", "5dfc2572-8a52-447c-901b-04595c6961bc")
NEW_SNAPSHOT_NAME = "ubuntu-libreoffice"
# LibreOffice 体积很大，根文件系统容量给足（单位字节）。
# 注意：不能小于来源快照的容量（你的快照是 20 GiB），这里给 24 GiB。
FS_CAPACITY = 24 * 1024**3


def main() -> None:
    client = SandboxClient()

    print(f"从快照 {BASE_SNAPSHOT_ID} 启动临时沙盒 ...")
    with client.sandbox(
        name="libreoffice-builder",
        snapshot_id=BASE_SNAPSHOT_ID,
        fs_capacity_bytes=FS_CAPACITY,
        timeout=120,
    ) as sandbox:
        print("运行 apt 更新与安装 LibreOffice（可能较慢）...")
        result = sandbox.run(
            "export DEBIAN_FRONTEND=noninteractive && "
            "apt-get update -qq && "
            "apt-get install -y -qq --no-install-recommends libreoffice-writer "
            "libreoffice-calc && "
            "libreoffice --version"
        )
        if result.exit_code != 0:
            raise SystemExit(f"安装失败, exit={result.exit_code}: {result.output}")

        print("捕获为新快照 ...")
        snapshot = sandbox.capture_snapshot(
            NEW_SNAPSHOT_NAME,
            timeout=600,
        )
        print(f"完成! 新快照 id={snapshot.id} status={snapshot.status}")

        # 可选: 用新快照起一个沙盒验证
        verify = input("是否用新快照起一个沙盒验证 libreoffice? [y/N] ").strip().lower()
        if verify in ("y", "yes"):
            with client.sandbox(
                name="libreoffice-verify",
                snapshot_id=snapshot.id,
                timeout=120,
            ) as check:
                print(check.run("libreoffice --version").stdout)


if __name__ == "__main__":
    main()
