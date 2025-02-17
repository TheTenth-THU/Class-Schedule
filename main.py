from web_to_html import request_web_page, parse_html, build_schedule_html
from html_to_png import export_image
import json
import os
import http

build_schedule_html(
    parse_html(
        request_web_page(
            type='3',
            term='2024-2025-2',
            config_path='config.json',
            save_path='demo/response.html'
        ),
        save_path='demo/courses.json'
    ),
    save_path='demo/schedule.html'
)

export_image(
    'demo/schedule.html',
    'demo/schedule.png'
)
