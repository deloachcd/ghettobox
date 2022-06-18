#!/usr/bin/python3

import yaml
import jinja2


with open("dashboard.yml", "r") as infile_yaml:
    dashboard_obj = yaml.safe_load(infile_yaml.read())


with open("index.html.j2", "r") as infile_html_j2:
    html_template_obj = jinja2.Template(infile_html_j2.read())

print(
    html_template_obj.render(
        logo=dashboard_obj["dashboard"]["logo"],
        columns=dashboard_obj["dashboard"]["columns"].values(),
    )
)
