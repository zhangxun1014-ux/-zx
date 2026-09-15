"""Run five visible live-HTTP checks, or recreate the archived API evidence."""
import argparse
import importlib.metadata
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:5000/api"
ROOT = Path(__file__).parent


def call(method, path, body=None, *, base=BASE, display=True):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(base + path, data=data, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        payload = json.loads(response.read().decode("utf-8"))
    if display:
        print(
            f"{method} {path}\nHTTP {status}\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
        )
    return status, payload, content_type


def scenarios(base=BASE, *, display=True):
    cases = [
        ("M-01", "GET", "/books", None, 200),
        ("M-02", "POST", "/loans", {"book_id": 1}, 201),
        ("M-03", "POST", "/loans", {"book_id": "wrong"}, 400),
        ("M-04", "POST", "/loans/999/return", None, 404),
    ]
    results = []
    for case_id, method, path, body, expected in cases:
        status, payload, content_type = call(method, path, body, base=base, display=display)
        if status != expected:
            raise AssertionError(f"{case_id}: expected HTTP {expected}, got {status}")
        results.append({
            "id": case_id, "method": method, "path": "/api" + path,
            "body": body, "expected_status": expected, "actual_status": status,
            "response": payload, "content_type": content_type,
        })
    new_loan = results[1]["response"]["loan"]["id"]
    path = f"/loans/{new_loan}/return"
    status, payload, content_type = call("POST", path, base=base, display=display)
    if status != 200:
        raise AssertionError(f"M-05: expected HTTP 200, got {status}")
    results.append({
        "id": "M-05", "method": "POST", "path": "/api" + path,
        "body": None, "expected_status": 200, "actual_status": status,
        "response": payload, "content_type": content_type,
    })
    return results


def draw_console(record, base, destination):
    """Draw the actual request/response transcript in a legible console panel."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 850), (24, 41, 51))
    draw = ImageDraw.Draw(image)
    white = (245, 248, 250)
    title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    mono_size = 14 if record["id"] == "M-01" else 16
    mono = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", mono_size)
    chinese = ImageFont.truetype("C:/Windows/Fonts/NotoSansSC-VF.ttf", mono_size)
    subtitle = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
    draw.text((44, 64), "Library API test console", font=title_font, fill=white)
    draw.text(
        (44, 118),
        "Live request / response capture · Computer Systems and Networks",
        font=subtitle,
        fill=white,
    )
    draw.line((44, 151, 1156, 151), fill=(99, 118, 128), width=1)

    request_url = base + record["path"].removeprefix("/api")
    lines = [f'{record["method"]} {request_url}']
    if record["body"] is not None:
        lines.append(json.dumps(record["body"], ensure_ascii=False))
    lines.extend([
        "", f'HTTP {record["actual_status"]}',
        f'Content-Type: {record["content_type"].split(";")[0]}',
        "",
    ])
    lines.extend(json.dumps(record["response"], ensure_ascii=False, indent=2).splitlines())
    line_height = 16 if record["id"] == "M-01" else 20
    if 175 + len(lines) * line_height > image.height - 10:
        raise ValueError(f'{record["id"]} transcript does not fit its evidence image')
    for index, line in enumerate(lines):
        x, y = 44, 175 + index * line_height
        for character in line:
            font = chinese if ord(character) > 127 else mono
            draw.text((x, y), character, font=font, fill=white)
            x += draw.textlength(character, font=font)
    image.save(destination)


def regenerate_evidence(destination=ROOT / "evidence"):
    """Use a fresh seed copy and a real localhost HTTP server for each capture."""
    from app import create_app
    from werkzeug.serving import make_server

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="library-manual-api-") as directory:
        data_dir = Path(directory)
        for name in ("books", "users", "loans"):
            shutil.copy(ROOT / "data" / f"{name}.json", data_dir / f"{name}.json")
        server = make_server("127.0.0.1", 0, create_app(data_dir), threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/api"
        captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            results = scenarios(base, display=False)
        finally:
            server.shutdown()
            thread.join(timeout=5)
    if results[1]["response"]["loan"]["id"] != 1:
        raise AssertionError("Fresh delivered seeds must produce loan id 1")
    for index, record in enumerate(results, start=1):
        draw_console(record, base, destination / f"manual-api-{index:02}.png")
    archival = [
        {key: value for key, value in record.items() if key != "content_type"}
        for record in results
    ]
    (destination / "manual-api-results.json").write_text(
        json.dumps(archival, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    run_context = {
        "captured_at": captured_at,
        "transport": "live HTTP against a temporary localhost WSGI server",
        "server_base_url": base,
        "data_source": "fresh isolated copies of delivered data/books.json, users.json, loans.json",
        "python": sys.version.split()[0],
        "flask": importlib.metadata.version("Flask"),
        "pillow": importlib.metadata.version("Pillow"),
        "manual_cases": len(results),
    }
    (destination / "manual-api-run.json").write_text(
        json.dumps(run_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Saved five live-HTTP checks and images to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", action="store_true", help="Recreate evidence from fresh isolated seeds")
    parser.add_argument("--base-url", default=BASE, help="Live API base URL for the normal demonstration")
    args = parser.parse_args()
    if args.evidence:
        regenerate_evidence()
    else:
        scenarios(args.base_url)
