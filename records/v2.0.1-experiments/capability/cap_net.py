#!/usr/bin/env python3
"""cap_net: the only way out of an answering sandbox (capability/PLAN.md section 3, "network while answering").

The sandbox has no network of its own (a new network namespace with loopback only). Two small programs connect it
to the hosts on an allowlist and to nothing else:

  serve    runs outside the sandbox. Listens on a Unix socket, accepts only `CONNECT host:port`, opens the
           connection when host:port is on the allowlist and answers 403 otherwise. Plain HTTP requests are refused.
           Every request is written to a log as one JSON line: time, host, port, allowed, bytes each way.
  forward  runs inside the sandbox as the parent of the session. Listens on 127.0.0.1:<port>, passes every
           connection to the Unix socket byte for byte, starts the session's command and exits with its exit code.

The session gets HTTPS_PROXY=http://127.0.0.1:<port>; a program that ignores the variable has no route at all.
"""
import json
import os
import select
import signal
import socket
import subprocess
import sys
import threading
import time


def pipe(one, two, counts=None):
    """Copy bytes both ways until either side closes; counts gets [one->two, two->one]."""
    sockets = [one, two]
    try:
        while True:
            ready, _w, _x = select.select(sockets, [], [], 600)
            if not ready:
                break
            done = False
            for source in ready:
                target = two if source is one else one
                try:
                    data = source.recv(65536)
                except OSError:
                    data = b""
                if not data:
                    done = True
                    break
                try:
                    target.sendall(data)
                except OSError:
                    done = True
                    break
                if counts is not None:
                    counts[0 if source is one else 1] += len(data)
            if done:
                break
    finally:
        for item in sockets:
            try:
                item.close()
            except OSError:
                pass


def read_head(conn, limit=16384):
    data = b""
    while b"\r\n\r\n" not in data and len(data) < limit:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def serve(path, log_path, allowed):
    allowed = {entry.lower() for entry in allowed}
    if os.path.exists(path):
        os.unlink(path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(path)
    server.listen(64)
    lock = threading.Lock()

    def record(row):
        with lock, open(log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def handle(conn):
        row = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": "", "port": 0, "allowed": False, "up": 0,
               "down": 0, "note": ""}
        try:
            conn.settimeout(60)
            head = read_head(conn)
            words = head.split(b"\r\n", 1)[0].decode("latin-1").split()
            if len(words) < 2 or words[0].upper() != "CONNECT":
                row["note"] = "not a CONNECT request: " + (words[0][:12] if words else "empty")
                if len(words) > 1:
                    row["host"] = words[1][:100]
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                return
            host, _colon, port = words[1].rpartition(":")
            row["host"], row["port"] = host.lower(), int(port or 0)
            if f"{row['host']}:{row['port']}" not in allowed:
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                return
            row["allowed"] = True
            try:
                upstream = socket.create_connection((host, row["port"]), timeout=30)
            except OSError as error:
                row["note"] = f"upstream: {type(error).__name__}"
                conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                return
            conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            conn.settimeout(None)
            upstream.settimeout(None)
            rest = head.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in head else b""
            if rest:
                upstream.sendall(rest)
            counts = [len(rest), 0]
            pipe(conn, upstream, counts)
            row["up"], row["down"] = counts
        except (OSError, ValueError) as error:
            row["note"] = f"{type(error).__name__}"
        finally:
            try:
                conn.close()
            except OSError:
                pass
            record(row)

    signal.signal(signal.SIGTERM, lambda *_args: os._exit(0))
    print("ready", flush=True)
    while True:
        conn, _address = server.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


def forward(port, path, argv):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", port))
    listener.listen(64)

    def relay(conn):
        try:
            out = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            out.connect(path)
        except OSError:
            conn.close()
            return
        pipe(conn, out)

    def accept():
        while True:
            try:
                conn, _address = listener.accept()
            except OSError:
                return
            threading.Thread(target=relay, args=(conn,), daemon=True).start()

    threading.Thread(target=accept, daemon=True).start()
    child = subprocess.Popen(argv)
    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, lambda received, _frame: child.send_signal(received))
    return child.wait()


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "serve":
        return serve(sys.argv[2], sys.argv[3], sys.argv[4:])
    if len(sys.argv) >= 6 and sys.argv[1] == "forward" and sys.argv[4] == "--":
        return forward(int(sys.argv[2]), sys.argv[3], sys.argv[5:])
    raise SystemExit("usage: cap_net.py serve <socket> <log> <host:port>... | forward <port> <socket> -- <command>...")


if __name__ == "__main__":
    sys.exit(main())
