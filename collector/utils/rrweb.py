import asyncio
import json
import os
from typing import Any, Dict, List

from playwright.async_api import Page

from . import logger
from collector.utils.file_utils import write_file


async def save_rrweb_events_to_file(
    stop_flag: List[bool], db_path: str, page: Any
) -> None:
    rrweb_events_path = os.path.join(
        db_path, "rrweb", f"{os.path.basename(db_path)}_rrweb_events.json"
    )
    os.makedirs(os.path.dirname(rrweb_events_path), exist_ok=True)
    open(rrweb_events_path, "a").close()  # Ensures file is created if it doesn't exist
    viewer_file_created = False

    while not stop_flag[0]:
        try:
            if page.is_closed():
                logger.error("Page is closed. Exiting save_rrweb_events_to_file.")
                break

            new_events = await page.evaluate("() => window.rrwebEvents || []")

            if new_events:
                all_events: List[Dict[str, Any]] = []

                if os.path.exists(rrweb_events_path):
                    with open(rrweb_events_path, "r") as f:
                        try:
                            all_events = json.load(f)
                        except json.JSONDecodeError:
                            pass

                all_events.extend(new_events)

                write_file(rrweb_events_path, json.dumps(all_events), mode="w")

                await page.evaluate("() => window.rrwebEvents = []")

                if not viewer_file_created:
                    create_rrweb_viewer_serving_script(rrweb_events_path)
                    viewer_file_created = True

        except Exception as e:
            logger.error(f"Exception during rrweb event saving: {e}")
        await asyncio.sleep(0.1)


async def inject_rrweb_script(page: Page) -> None:
    await page.evaluate(
        """
        (function() {
            if (!window.rrwebObserverInjected) {
                function injectRRweb() {
                    if (!window.rrwebInjected) {
                        var script = document.createElement('script');
                        script.src = "https://cdn.jsdelivr.net/npm/rrweb@latest/dist/rrweb.min.js";
                        script.async = false;  // Ensure script is executed in order
                        script.onload = function() {
                            window.rrwebEvents = window.rrwebEvents || [];
                            rrweb.record({
                                emit(event) {
                                    window.rrwebEvents.push(event);
                                },
                                recordCanvas: true,
                                sampling: {
                                    mousemove: true,
                                    scroll: true,
                                    input: true
                                }
                            });
                            console.log('rrweb recording started');
                            window.rrwebRecordingStarted = true;
                        };
                        script.onerror = function() {
                            console.error('Failed to load rrweb script');
                        };
                        document.head.appendChild(script);
                        console.log('rrweb script tag added to document');
                        window.rrwebInjected = true;
                    }
                }

                const observer = new MutationObserver((mutations) => {
                    for (let mutation of mutations) {
                        if (mutation.type === 'childList' && mutation.addedNodes.length) {
                            injectRRweb();  // Reinject rrweb if the DOM changes
                        }
                    }
                });

                observer.observe(document, { childList: true, subtree: true });
                window.rrwebObserverInjected = true;
                injectRRweb();  // Initial injection
            }
        })();
        """
    )


def create_rrweb_viewer_serving_script(rrweb_events_filename: str) -> None:
    rrweb_events_relative_path = os.path.basename(rrweb_events_filename)
    rrweb_viewer_file = rrweb_events_relative_path.replace(
        "_rrweb_events.json", "_rrweb_viewer.html"
    )

    server_script_content = f"""import os
from http.server import SimpleHTTPRequestHandler, HTTPServer
import webbrowser

def serve_files(directory, port=8001):
    os.chdir(directory)
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(('localhost', port), handler)
    print(f"Serving files from {{directory}} on http://localhost:{{port}}")
    httpd.serve_forever()

if __name__ == "__main__":
    directory_to_serve = os.path.dirname(__file__)
    rrweb_viewer_file = "{rrweb_viewer_file}"
    print(f"Serving rrweb viewer: {{rrweb_viewer_file}}")
    webbrowser.open(f"http://localhost:8001/{{rrweb_viewer_file}}")
    serve_files(directory_to_serve)
    """

    script_filename = rrweb_events_filename.replace(
        "_rrweb_events.json", "_serve_rrweb_viewer.py"
    )
    write_file(script_filename, server_script_content, mode="w")

    viewer_html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>rrweb Player Event Viewer</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/style.css"/>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: #f0f0f0;
            min-height: 100vh;
        }}
        #player-container {{
            width: 100%;
            max-width: 1024px;
            height: 576px;
            border: 1px solid #ccc;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            background-color: #fff;
        }}
    </style>
</head>
<body>
    <div id="player-container"></div>

    <script src="https://cdn.jsdelivr.net/npm/rrweb@latest/dist/rrweb.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/rrweb-player@latest/dist/index.js"></script>
    <script>
        function loadAndPlayEvents() {{
            fetch("{rrweb_events_relative_path}")
                .then(response => response.json())
                .then(events => {{
                    new rrwebPlayer({{
                        target: document.getElementById('player-container'),
                        props: {{
                            events: events,
                            width: 1024,
                            height: 576,
                            autoPlay: true,
                            speedOption: [1, 2, 4, 8]
                        }}
                    }});
                }})
                .catch(error => {{
                    console.error("Failed to load rrweb events:", error);
                }});
        }}

        loadAndPlayEvents();
    </script>
</body>
</html>
    """

    viewer_filename = rrweb_events_filename.replace(
        "_rrweb_events.json", "_rrweb_viewer.html"
    )
    write_file(viewer_filename, viewer_html_content, mode="w")
    logger.debug(f"rrweb viewer HTML file created: {viewer_filename}")
